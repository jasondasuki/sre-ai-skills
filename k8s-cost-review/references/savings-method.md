# Defensible savings estimates

## Choose the billing basis first

Establish whether the bill is driven by nodes, Pod resource requests, serverless
execution, disks, traffic, or a combination. Identify exact SKU, region, currency,
rate source/date, billing period, discounts/commitments, and credit treatment.
Use actual period hours when available; otherwise `{{MONTH_HOURS}}` hours is a
labeled monthly run-rate convention, not the duration of every calendar month.

Show separately:

1. **Capacity benefit:** resources freed or demand removed, with no assumed cash
   conversion. For node-hour billing, changing requests with unchanged nodes may
   yield no immediate bill saving.
2. **Gross/list-price reduction:** optional scenario at explicit published rates.
3. **Marginal realizable bill reduction:** change in actual cost after commitments,
   floors, fallback capacity, and offsetting resources. This is the ranked value.
4. **Conditional or unpriced benefit:** arithmetic with unknown rate variables or
   an evidence collection task, not an invented currency amount.

For same-shaped removable nodes with verified marginal rate:

`monthly saving = removed nodes × marginal hourly rate × billable hours removed`

For shape/purchase-mode migration:

`saving = baseline total effective cost − proposed total effective cost`

Include differences in node count, usable capacity, disks, fallback/on-demand
capacity, management/network costs, and unchanged commitment charges. Do not
multiply every idle CPU core by a vCPU list rate on a node-hour cluster.

## Commitments and Spot

A commitment is a fixed obligation or discount pool with provider-specific
coverage rules, not automatically a removable hourly charge. Reducing covered
usage can strand committed spend instead of reducing the cash bill. Model whether
another eligible workload absorbs coverage, when the commitment expires, and
which incremental charges actually disappear.

Evaluate Spot against the workload's interruption tolerance, availability of
capacity in its zones, retry/checkpoint cost, architecture/image support, startup
latency, SLO/quorum/PDB requirements, and fallback plan. A marketing discount is
not an achieved fleet discount. If migration adds Spot charges while fixed
commitments remain unused, show the possible cost increase explicitly.

Stabilize demand before recommending a new commitment; do not prescribe a
purchase amount without coverage, utilization, term, and demand-confidence data.

## Sizing and packing

Show workload before/after resource targets only when historical demand supports
them. Explain headroom, metric resolution, CPU burst/throttling, memory peaks and
OOMs, init/startup demand, and replica/autoscaler interaction. Changing CPU request
changes HPA utilization targets: for CPU usage U and request R, utilization is
U/R; halving R doubles the percentage. Model resulting replica counts before
claiming a net capacity reduction.

Calculate aggregate capacity lower bounds as bounds, then check actual placement
constraints and pool/zone minimums. Verify allowed evictions and remaining
capacity under required failover or rollout conditions. Node removal is
conditional if this cannot be established from existing evidence; an analysis
must not test removability by draining production.

## Avoid double counting

Treat workload rightsizing and the node removal it enables as one causal savings
chain. Do not add Pod savings to the same node-hour reduction. Combine rightsizing,
HPA/replica changes, and consolidation into one scenario and count its final bill
delta once. Mark Spot/shape alternatives mutually exclusive when they affect the
same nodes. Storage/traffic reductions can be additive only when independently
billed and not already included in the scenario.

For multiple actions, list dependencies and overlap groups, and show a final
baseline-versus-proposed cost table. If inputs are ranges, propagate conservative
bounds with clear assumptions. Do not add an optimistic end of every mutually
exclusive option to claim a maximum total.

## Recommendation readiness

- **Ready:** consistent historical/configuration evidence, established mechanism
  to reduce billable resources, and no unresolved feasibility constraint. Use a
  clearly labeled estimate rather than promising realized savings.
- **Conditional:** named blockers such as an autoscaler minimum, HPA adjustment,
  missing placement check, interruption support, or retained commitment cost.
- **Measure first:** missing historical coverage, workload lifecycle signals,
  ownership/retention intent, billing/rates, or critical scheduler accounting.
- **Rejected:** evidence rules out the purported benefit or reveals a net increase.

Give a concrete next task even for conditional/unpriced findings. Define post-
rollout verification: requested/used resources, replicas, pending Pods, OOMs,
throttling, latency/errors, evictions, actual node count, and scoped billing cost
over comparable demand/time windows. Include rollback configuration and triggers.
