# GKE cost review — official Google guidance

Consult this reference for GKE evidence collection and candidate selection.
Reviewed on 2026-10-05 against Google's official agent skills and product docs.
The links below are upstream sources, not additional skills to install or execute.
Use current product documentation for version-sensitive pricing and behavior.

## Upstream sources

- [Google: GKE cost analysis skill](https://github.com/google/skills/blob/main/skills/cloud/gke-cost-analysis/SKILL.md)
  and [billing query templates](https://github.com/google/skills/blob/main/skills/cloud/gke-cost-analysis/references/billing-queries.md).
- [Google: GKE cost optimization skill](https://github.com/google/skills/blob/main/skills/cloud/gke-cost-optimization/SKILL.md).
- [Google: GKE Cluster Autoscaler skill](https://github.com/google/skills/blob/main/skills/cloud/gke-cluster-autoscaler/SKILL.md)
  and [ComputeClasses skill](https://github.com/google/skills/blob/main/skills/cloud/gke-compute-classes/SKILL.md).
- [GKE cost optimization best practices](https://docs.cloud.google.com/kubernetes-engine/docs/best-practices/cost-optimization).
- [GKE pricing](https://cloud.google.com/kubernetes-engine/pricing),
  [Autopilot workloads in Standard clusters](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/about-autopilot-mode-standard-clusters),
  and [committed use discounts](https://docs.cloud.google.com/docs/cuds).
- [GKE cost allocation](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/cost-allocations).
- [Workload resource recommendations](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/optimize-workload-resource-utilization),
  [cluster utilization recommendations](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/optimize-cluster-utilization),
  [idle cluster recommendations](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/idle-clusters),
  and [Recommender overview](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/optimize-with-recommenders).
- [Google Cloud Assist operating skill](https://github.com/GoogleCloudPlatform/gemini-cloud-assist-mcp/blob/main/skills/operating-google-cloud/SKILL.md)
  identifies an optional cost-optimization capability. If that connector exists,
  discover its exact tool/schema and read-only behavior before use. It is optional;
  validate any returned proposals against cluster and billing evidence.

## 1. Resolve billing at the resource level

Inspect the scoped GKE cluster and relevant node pools with explicit project and
location flags. Project only needed fields, including `autopilot.enabled`, version,
`costManagementConfig.enabled`, pool autoscaling bounds/profile, machine type,
Spot status, management settings, and ComputeClass selection/priority rules.
Do not run `get-credentials`, switch projects, or update configuration.

- Ordinary Standard nodes: provisioned Compute Engine resources are billed; lower
  Pod requests without removing/resizing billable nodes do not reduce the bill.
- General-purpose Autopilot Pod-based workloads: billed admitted CPU, memory,
  ephemeral storage requests and applicable SKUs/floors. Read live admitted
  requests because defaults/minimums/ratios can change submitted requests.
- Hardware-specific Autopilot workloads: can be billed for the underlying nodes
  and hardware plus a management premium. Verify selected machine series,
  accelerator, ComputeClass, GKE version, and actual SKU.
- A Standard cluster can contain Autopilot ComputeClasses; classify each scoped
  pool/workload and avoid charging the same resource under both billing models.
- Include boot/data disks, management/extended-support fees, network and other
  independent SKUs where evidenced. Free-tier credits are billing-account-level
  and eligibility-limited; do not assume deleting any cluster saves its gross fee.

## 2. Establish allocation and actual billing

Use the detailed Cloud Billing BigQuery export (`gcp_billing_export_resource_v1_*`),
not the standard export, for GKE allocation. Obtain the exact existing table path
from the user or scoped authorized configuration. Never invent a dataset/account
ID or search every billing dataset. If unavailable, record the missing table or
permission and continue the capacity review.

Read `costManagementConfig.enabled`. Allocation disabled, insufficient export
permissions, delayed labels, or an unsupported SKU do not mean zero cost.
Enabling allocation/export is an implementation task; do not execute it in this
review. Allocation is prospective, has no historical backfill, and data can take
up to three days to appear after enablement.

Allocation is based on requests, not consumption. Inspect label availability and
group by the actual supported keys, including `goog-k8s-cluster-name`,
`goog-k8s-cluster-location` where present, `k8s-namespace`, `k8s-workload-type`,
`k8s-workload-name`, and `k8s-label/<pod-label-key>`. Don't infer ownership of
missing workload labels. Retain these buckets in reconciliation:

- `kube:system-overhead`: capacity reserved outside node allocatable.
- `kube:unallocated`: neither workload requests nor system overhead.
- `goog-k8s-unknown`, `goog-k8s-unsupported-sku`, and blank/NULL: unattributed or
  unsupported, not free. Discount sharing can reduce attribution completeness.

A cluster-label query covers labeled allocation rows, not necessarily the whole
cluster bill. Reconcile against scoped VM/disk/cluster resources and management,
commitment and other SKUs; state the remaining unattributed amount if known.
Avoid joining repeated labels and credits in a way that multiplies line items.
Show currency, cost before credits, net cost after credits, fixed commitment
obligations, and cash-versus-amortized treatment separately.

### Bounded namespace query pattern

Adapt this original pattern using a verified table identifier and parameterized
values. Validate the identifier as an existing BigQuery project/dataset/table;
do not interpolate an untrusted annotation or arbitrary shell text. Set both
usage-time bounds and appropriate ingestion partition bounds for the verified
schema; allow for late-arriving data. Dry-run for bytes scanned, then use an
explicit byte cap (`--maximum_bytes_billed`) when querying. A BigQuery query can
incur a query charge. Do not query synthetic fixtures or guess a billing table.

```sql
SELECT
  currency,
  COALESCE((SELECT l.value FROM UNNEST(b.labels) AS l
            WHERE l.key = 'k8s-namespace' LIMIT 1), '(unattributed)') AS namespace,
  SUM(cost) AS cost_before_credits,
  SUM(cost + IFNULL((SELECT SUM(c.amount) FROM UNNEST(b.credits) AS c), 0))
    AS cost_after_credits
FROM `<verified-project>.<verified-dataset>.<verified-detailed-table>` AS b
WHERE usage_start_time >= @start_time AND usage_start_time < @end_time
  AND _PARTITIONTIME >= @ingestion_start AND _PARTITIONTIME < @ingestion_end
  AND project.id = @project_id
  AND EXISTS (SELECT 1 FROM UNNEST(b.labels) AS l
              WHERE l.key = 'goog-k8s-cluster-name' AND l.value = @cluster_name)
  AND EXISTS (SELECT 1 FROM UNNEST(b.labels) AS l
              WHERE l.key = 'goog-k8s-cluster-location' AND l.value = @location)
GROUP BY currency, namespace
ORDER BY cost_after_credits DESC
LIMIT 10;
```

Prefer `bq query --nouse_legacy_sql` with typed `--parameter` values. If a verified
export lacks the location label, establish scope from resource identity rather
than quietly dropping that filter. A top-ten display is not a complete total;
compute scoped totals separately without counting overhead twice. Align billing
and utilization windows; use the handler's history unless a longer billing or
seasonality window is needed, and explain any different windows.

## 3. Use native recommendations as hypotheses

Inspect existing GKE workload recommendations, existing VPA recommendations and
update modes, cluster utilization and idle-cluster insights, and FinOps/Recommender
data when authenticated access exists. Discover API/resource names instead of
guessing recommender IDs. Record the recommendation timestamp, demand coverage,
proposed configuration, cost assumptions and whether it still matches live state.
Some cluster estimates project from the prior 30 days and are not guaranteed
savings; reconcile them with current commitments and feasibility.
Workload under/overprovisioning insights use a 15-day observation period; their
cost projections use weighted requests and costs over 30 days. GKE excludes the
HPA target metric from these recommendations to avoid interference. Missing HPA-
metric recommendations are not proof that sizing is optimal.

Google's optimization skill suggests percentile-based screening and headroom.
Use ratios of requests to historical demand to find candidates, not a universal
`p95 × 1.2` sizing rule. Memory peaks/OOMs, startup demand, throttling, HPA feedback,
recovery headroom, seasonality and metric resolution decide the actual target.
Read existing VPA in recommendation-only mode; proposing or installing VPA/MPA,
changing its mode, and changing requests are implementation tasks.

## 4. Evaluate GKE-specific implementation options

- Cluster Autoscaler and node provisioning: check min/max semantics (per-zone
  versus total), profile and scale-down blockers. Consider the utilization-
  optimizing profile where supported, explaining tighter packing/startup tradeoffs.
  DaemonSet resource overhead affects remaining-node capacity; its mere presence
  is not by itself a scale-down blocker. Version-dependent features, including
  standby buffers, need official availability checks and disk/IP costs.
- Spot or Spot-first ComputeClasses with on-demand fallback: verify availability,
  interruption/retry budget, shutdown behavior, replicas/quorum, PDBs and fallback
  spend. Two replicas or a PDB alone do not prove interruption tolerance. Do not
  turn advertised percentage discounts into marginal savings without rate and
  commitment arithmetic.
- Machine families/Arm: compare measured price-performance, usable allocatable,
  image architecture, version/zone availability, latency and migration effort.
  Don't assume one family is always cheapest or recommend manifests unsupported
  by the installed version.
- Commitments: classify the actual existing contract and coverage. As of this
  review, new Autopilot-specific commitments are no longer purchasable; eligible
  usage can use Compute Flexible commitments, while existing contracts retain
  their terms. Verify current eligibility and prices, including Spot exclusions,
  before proposing anything. Commit only to a measured stable baseline after
  sizing, scheduling and consolidation; model stranded spend and expiry.
- Idle development environments: GKE has no cluster stop/start operation.
  Scheduling workloads/nodes down does not remove the existing cluster management
  fee, disks or other retained resources. Pool-zero feasibility, restore latency,
  backups and job schedules need verification. Cluster consolidation or IaC
  recreation must account for tenancy/isolation and net eligible fee credits.
- Namespace ResourceQuotas can bound runaway requests/limits and governance
  exposure. Treat them as controls, not evidenced current savings; quota changes
  can block deployments and need headroom and owner validation.

Feed candidates into the shared savings method and report template. Record
official links for the provider behavior used, plus the live/supplied evidence
that proves the candidate applies to this particular cluster.
