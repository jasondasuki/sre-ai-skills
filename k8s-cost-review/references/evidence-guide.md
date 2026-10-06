# Evidence collection guide

Use existing clients with explicit context and bounded request timeouts. These
are capability examples, not an instruction to run every command. Resource APIs
and metric names vary by Kubernetes version, provider, and installed agents;
discover them before use. Commands run from `{{WORKDIR}}`.

## Minimal common inventory

Prefer the bundled collector described in `references/deterministic-tools.md`
for the shared node/Pod baseline. Its live Go-template projection and offline
allowlist omit sensitive fields before output. Use the commands below only for
targeted additional evidence; retain source failures and accounting gaps. Do not
replace projection failures with saved raw Pod specs.

List context names with `kubectl config get-contexts -o name`; read the current
name with `kubectl config current-context`. Neither changes the selected context.
For a resolved context, obtain Kubernetes version, node pool/provider labels,
capacity/allocatable, node conditions, and relevant API resources. Node metadata
JSON can be used if sanitized; use projected fields for workloads instead of
dumping complete Pod specs that include environment variables.

Example safe projections (replace the angle-bracket context; these are not
variables in the handler):

```bash
kubectl --context=<context> --request-timeout=30s get nodes -o custom-columns='NAME:.metadata.name,PROVIDER:.spec.providerID,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory,PODS:.status.allocatable.pods'
kubectl --context=<context> --request-timeout=30s get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.nodeName}{"\t"}{.status.phase}{"\t"}{.metadata.ownerReferences}{"\t"}{.spec.containers[*].resources}{"\t"}{.spec.initContainers[*].resources}{"\t"}{.spec.initContainers[*].restartPolicy}{"\t"}{.spec.overhead}{"\t"}{.spec.resources}{"\n"}{end}'
kubectl --context=<context> --request-timeout=30s top nodes
kubectl --context=<context> --request-timeout=30s top pods -A --containers
kubectl --context=<context> --request-timeout=30s get hpa -A
kubectl --context=<context> --request-timeout=30s get pdb -A
```

`top` is a snapshot with limited provenance; label it as such. Further projections
may be needed for scheduling fields, replicas, container names, status restart
counts/termination reasons, PVC references, and controller templates. A namespaced
request should use its namespace instead of `-A`. Avoid broad `describe pod`
output when it could expose plaintext environment values; project relevant fields.

## Capacity and scheduling collector

- Group nodes by pool, shape, region/zone, architecture, purchase mode, and
  readiness. Compare allocatable, effective scheduled requests, and measured
  usage independently. Include system reservations already excluded from
  allocatable; do not subtract them twice.
- Use scheduler-equivalent effective requests for the detected version: admitted
  defaults/LimitRange, regular containers, sequential init containers, restartable
  init sidecars and their concurrent phases, Pod overhead, and pod-level resources
  where supported. A simple sum of application container requests can be wrong.
  Cite a verified effective-request metric or compute using documented version
  semantics. If unresolved, label capacity arithmetic incomplete.
- Separate pending demand from scheduled demand; exclude completed/failed Pods
  from steady scheduled demand but include future CronJob/rollout/concurrent-job
  requirements in capacity planning.
- Check pool minimums (including whether per-zone or total), autoscaling policies,
  consolidation settings and timeouts, scale-down-disabled/safe-to-evict metadata,
  PDB allowed disruptions and replica quorum, affinity/anti-affinity, taints,
  topology spread, GPU/extended resources, ephemeral storage, local PVs,
  attach limits, max-pod/IP limits, and DaemonSet overhead on remaining nodes.
- Do not treat every PDB as an absolute blocker; report the relevant budget and
  current allowed disruptions. Conversely, do not remove one just to improve
  consolidation without establishing the reliability requirement.
- Report specific pinned pools/resources and placement prerequisites rather
  than claiming that idle aggregate cores imply removable nodes.

## Workload demand and scaling collector

- Identify controller and container, configured requests/limits, replicas and
  scaling source. Use the default `{{LOOKBACK_DAYS}}` window, extending when
  monthly jobs or seasonality require it. Note scrape resolution, missing series,
  identity churn, and the fraction of workload lifetime represented.
- Discover available CPU usage (cores), memory working set/RSS/cache semantics,
  maxima and percentile series, restarts/OOM termination, CPU throttling,
  latency/error/queue saturation, and job durations/concurrency. Explain each
  metric's unit. Point-in-time p95 across Pods is not the p95 over time, and a
  sum of each container's p95 is not a simultaneous workload percentile.
- Preserve spikes: coarse rollups may hide startup, batch, or GC demand. CPU
  p95 can inform requests with justified headroom; memory sizing needs peaks,
  runtime/cache behavior, OOM and restart evidence, and recovery margin.
- Verify metric label mapping to the exact cluster and current workload; zero
  samples, short retention, or absent metrics mean unknown, not idle.
- Read HPA min/max, CPU percentage/absolute/custom metrics, stabilization and
  behavior; VPA update mode and recommendations; KEDA triggers and cooldown.
  HPA and VPA may conflict if both modify/control the same resource signal.
- Check idle replicas against redundancy, actual traffic, leader election,
  cold-start tolerance, background work, and environment operating hours.
  Scheduling non-production off-hours needs an explicit timezone, restart
  readiness, state retention, and coverage for jobs/users outside the schedule.

## Billable resources and ownership collector

- Distinguish standard node-hour billing from managed/autopilot Pod-resource or
  other billing classes. Establish what is billed, including floors, ephemeral
  storage, GPU, system/management fees, and provider-specific minimums.
- Map nodes to actual instance types and purchase modes. Check current provider
  config for pool size/minimum, version, autoscaling, boot disks, Spot, node
  provisioning, and supported alternative architectures. Use read/describe/list
  client operations only; do not authenticate anew or change global CLI config.
- Prefer actual scoped billing/effective rates and coverage over list prices.
  Record currency, region, period, discounts, commitments, credits, amortized
  versus cash basis, and source date. A billing export query may itself cost
  money: bound the time partitions/columns and use existing approved query tools.
- If live billing is unavailable, use provider public pricing only when requested
  or needed, with exact SKU/region/date and explicit list-price assumptions.
  Do not infer a project's effective rate from a generic pricing article.
- Inventory PVC/PV/storage classes, requested/capacity/usage if available, access
  modes, attachment and reclaim policies. Compare cloud disks and snapshots only
  within the scoped project/resource set. Released PV or zero attachment does
  not establish safe deletion.
- Correlate Service/Ingress/Gateway ownership to paid LBs/IPs and provider billing;
  internal/ClusterIP Services are not individually assumed to be billed LBs.
  Use actual transfer bytes and rates for cross-zone/NAT/egress hypotheses.
- Telemetry costs need ingestion/retention/indexing evidence; do not estimate
  log savings from Pod count or recommend dropping operationally required data.
- Read relevant desired-state resource files in `{{SOURCE_REPOS}}`, avoiding
  encrypted/private unrelated files and secret material. Return exact paths and
  config keys plus live/source mismatch, without modifying repositories.

## Missing tools and fixture mode

Do not install OpenCost, metrics-server, Prometheus, VPA, or cloud extensions as
part of this review. Offer the smallest data collection needed for an unresolved
recommendation. Supplied files can replace live APIs completely; preserve their
timestamps and limitations and do not cross-check synthetic targets live.
