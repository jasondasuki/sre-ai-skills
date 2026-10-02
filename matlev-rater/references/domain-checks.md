# Domain checks

Read this when planning (Step 2). It is the starting checklist per evidence
source. Turn each item into a numbered, answerable question for the capabilities
in the current scale document; drop what does not apply and add what the scale
document's capabilities need.

## Contents

- Repository assessors
- Kubernetes assessor
- Datadog assessor
- Cloudflare assessor

## Repository assessors

One assessor per repository. Read-only: reading files, listing, grepping, and
running read-only git commands (log, show, blame). No builds that write, no
installs, no apply, no plan against live systems.

- What does this repository declare, and which capabilities does that cover?
- How is a change applied: which pipeline, which approvals, which policy checks?
  Cite the workflow, CODEOWNERS entry, or policy file.
- Is anything applied by hand that the repository only describes?
- Are module and chart references pinned to a release or to a moving branch?
- Is there a scheduled drift check, a reconcile loop, or a plan-on-schedule job?
- Are there monitors, dashboards, or alerts defined as code here? Which?
- Are there runbooks, and does the runbook name a date it was last exercised?
- Where do the repository's claims and its documentation disagree?
- Anything declared as planned, not built, TODO, or empty scaffolding?

## Kubernetes assessor

Only the verbs in `{{KUBE_ALLOWED_VERBS}}`, on the contexts in `{{KUBE_CONTEXTS}}`,
one context at a time. Never read Secret objects or pod logs. Never exec.

- Delivery controller: every Application's sync and health status, the sync
  policy (automated, self-heal, prune), the last sync time, and any that are out
  of sync or degraded.
- Platform packages: are the packages the repositories declare actually present,
  and at what version? Which are managed by the delivery controller and which are
  not? Anything running that no repository declares?
- Secret and certificate synchronisation: the status of each store and each
  synchronised secret object, and of each certificate resource (ready, expiry
  window). Counts and conditions only.
- Operators and custom resources for stateful services: their status conditions,
  replica counts, and whether the declared version matches the running one.
- Guardrails: namespace quotas, limit ranges, default-deny network policies,
  disruption budgets, and which namespaces lack them.
- Nodes: versions, pools, taints, and count; how far the version is behind the
  declared release channel.
- Monitoring agents: are the telemetry collector and the monitoring agent
  running on every node and healthy?

## Datadog assessor

Read-only queries through the MCP tools. Load the MCP's own skill guides for
query syntax first. Metadata and aggregates only: no log message bodies.

- Monitors: which exist for the delivery controller, the secret synchroniser, the
  telemetry pipeline, cluster and node health, and certificates? For each: query,
  thresholds, notification target, mute or downtime state, and current status.
- Have those monitors fired in the last 90 days, and is there evidence the alert
  was acted on (an incident, a resolved event, a downtime that followed)?
- Dashboards: do the dashboards the handbook names exist and receive data?
- SLOs: do any SLO objects exist, and for which services? Compare against the
  scale document's claim.
- Signal flow: is each environment and cluster reporting metrics now? Any gap in
  the last 30 days?
- Is monitoring defined as code (managed-by tags, naming, generator markers) or
  hand-made?

## Cloudflare assessor

GET requests only, only for the zones in `{{IN_SCOPE_DOMAINS}}`. Never range-scan
addresses. Never read customer data or logs.

- Zones and DNS: record counts by type, proxied versus not, records pointing
  straight at origins, wildcards, and anything that looks unmanaged.
- Is the edge configuration consistent with the declared design (origin
  protection, mutual TLS to the origin, TLS mode and minimum version)?
- Rulesets and WAF: which managed rulesets and custom rules are enabled, in which
  action mode, and whether they are defined as code (names, descriptions).
- Zero Trust and tunnels, if used: applications, policies, and who may reach them.
- Audit log: how recent changes were made (by a user, token, or automation) as a
  signal of manual versus pipeline-driven change. Counts and actors by type, not
  detailed payloads.
- Notifications and health checks: do alerts exist for the edge, and where do
  they go?
