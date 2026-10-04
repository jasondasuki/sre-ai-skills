# Datastore checks from inside the pod

Read this in Step 4 when the question is about a Redis-compatible store (Redis,
Valkey) or a RabbitMQ broker. Every command here is a read. Nothing here changes
data, configuration, or membership.

## Contents

- Before you choose a method
- Redis / Valkey
- RabbitMQ
- Reading the answers
- Mistakes that cost time

## Before you choose a method

1. **Try `kubectl exec` into the datastore's own container first.** These images
   have their CLI and, with operator-managed deployments, usually the password in
   the container's environment. No debug container is created.
2. **Use a debug container** only to test the network path from inside the pod
   (port open, DNS, a peer service), or when exec is not permitted. Apply the
   debug container recipe in the core. Datastore images do not all run as the same
   user: some official Redis-family images run as uid/gid 0, others as a dedicated
   uid such as 999. Read `/proc/1/status` and match both numbers, and do not copy a
   profile from a different workload.
3. **Pass `--target=<datastore container>`.** These pods usually carry a metrics
   exporter sidecar, and an untargeted debug container shows the wrong `/proc/1`.
4. **Find where the secret lives without reading it:** list the pod's `env`
   entries with their `secretKeyRef` name and key (names only), or the Secret
   names in the namespace. If the container's own environment already holds the
   password, use it in place (`REDISCLI_AUTH="$REDIS_PASSWORD"` inside the
   container's shell). Otherwise pipe the Secret over stdin into a sleeping debug
   container's `exec -i` and `read` it into a shell variable. Never `--env` it,
   never put it in an argument, and never echo it.

## Redis / Valkey

An unauthenticated connection to a protected instance answers `NOAUTH`.
That response proves the port is reachable and the server is up; it is not a
fault. Authenticate through `REDISCLI_AUTH`, or send `AUTH` as the first line over
the pipe.

From the datastore container (preferred):

```
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> PING
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> INFO server
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> INFO memory
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> INFO clients
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> INFO replication
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> DBSIZE
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> SLOWLOG GET 5
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> LATENCY LATEST
REDISCLI_AUTH="$REDIS_PASSWORD" <cli> ROLE
```

`<cli>` is `valkey-cli` or `redis-cli`, whichever the image has. For a clustered
deployment add `CLUSTER INFO` and `CLUSTER NODES`.

From a debug container with no client, speak the protocol over `nc` and filter the
reply to the lines you need:

```
{ printf 'AUTH %s\r\nPING\r\nINFO memory\r\n' "$PW"; sleep 1; } | nc 127.0.0.1 6379 | tr -d '\r' | grep -E '^(\+OK|\+PONG|-|used_memory_human|maxmemory_human|connected_clients)'
```

Do not run: `KEYS`, `SCAN` over a large keyspace, `MONITOR`, `DEBUG`, `FLUSHALL`,
`FLUSHDB`, `DEL`, `CONFIG SET`, `SHUTDOWN`, `REPLICAOF`, `FAILOVER`.

## RabbitMQ

Ports: 5672 (AMQP), 15672 (management HTTP API), 15692 (Prometheus metrics),
4369 (peer discovery), 25672 (inter-node). A port check proves reachability only.
The management API answers `401` without credentials; that confirms it is up.

From the broker container (preferred), no debug container needed:

```
rabbitmq-diagnostics -q check_running
rabbitmq-diagnostics -q check_local_alarms
rabbitmq-diagnostics -q status
rabbitmqctl -q list_queues name messages consumers
rabbitmqctl -q cluster_status
```

Against the management API from a debug container, with credentials piped over
stdin and an `Authorization: Basic` header built inside the shell:

```
GET /api/health/checks/alarms
GET /api/health/checks/local-alarms
GET /api/overview
GET /api/nodes
GET /api/queues?columns=name,messages,consumers,state&page=1&page_size=50
```

Always bound a listing with `columns` and `page_size`. A broker with many queues
returns a very large body otherwise.

Do not run: `purge_queue`, `delete_queue`, `delete_*`, `stop_app`, `reset`,
`force_reset`, `forget_cluster_node`, `cancel_sync_queue`, or a `PUT`, `POST`, or
`DELETE` on the API.

## Reading the answers

| Observation | Meaning |
|---|---|
| Redis `used_memory` near `maxmemory` | evictions or write errors are next; check the eviction policy |
| Redis `connected_clients` high or `blocked_clients` > 0 | connection leak, or consumers stuck on blocking pops |
| `SLOWLOG` entries from the app's usual commands | a hot command or a big value, not an outage |
| Redis `role:slave` when the app expects a primary | failover happened; the app is pointed at the wrong endpoint |
| RabbitMQ alarms not `ok` | a memory or disk alarm is blocking publishers; that is the incident |
| queue `messages` growing with `consumers` 0 | consumers are down or not connecting |
| queue `messages` growing with consumers > 0 | consumers are slow or erroring; check their logs |
| port open but app cannot connect | credentials, TLS, a NetworkPolicy from a different namespace, or the wrong service name |

## Mistakes that cost time

- A plain debug image that inherits the pod's `runAsNonRoot` can still run (the pod
  names a numeric user) yet fail to read `/proc/1/root` because its gid is 0.
  The fix is `runAsGroup`, not root.
- A script reading stdin that is passed at container creation hangs. Sleep first,
  then `exec -i`.
- An exec'd shell that inherits no terminal has no prompt and no echo. A command
  that prints nothing may have succeeded quietly; check the exit code before
  retrying.
- Ephemeral containers accumulate. Re-use the sleeper.
