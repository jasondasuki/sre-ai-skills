# Reproducible inventory, calculations and evidence checks

Use Python 3.9+ and the standard library; no installation or authenticated service
is needed for offline processing. Run from `{{WORKDIR}}`. Create the run folder
first. Output files are exclusive-create: use new filenames for revised artifacts.
Do not run these helpers against synthetic names as live contexts.

## Inventory

```bash
python3 {{CORE_DIR}}/scripts/collect-inventory.py --context <resolved-context> --output <run-folder>/inventory.json
python3 {{CORE_DIR}}/scripts/collect-inventory.py --context <fixture-context> --input <provided-file> --output <run-folder>/inventory.json
```

For namespace scope add `--namespace <name>`. A supplied file must have its exact
`context` and optional `collected_at`, `version` (string or kubectl version object),
`nodes` and `pods` (arrays or Kubernetes List objects). The input is Kubernetes-
shaped admitted state, not desired-state templates. Missing APIs remain unavailable.
Keep supplied timestamps; do not replace them with the processing time.

Live collection uses explicit context and timeouts, with a kubectl Go-template
allowlist. Workload raw specs are not emitted or saved: environment values,
commands, arbitrary annotations/labels and host paths are omitted. A fixture is
projected through the same allowlist. Live projection failure is an unavailable
source, not permission to fall back to saving raw Pods. Errors are summarized
without persisting client stderr. Record useful sanitized permission/projection
diagnostics separately in the source status.

The output separates scheduled, pending and completed demand; CPU is millicores,
memory/storage/hugepages are bytes, other resources are integer units. Quantities
are added exactly before scheduler unit rounding. Each Pod has effective requests
or null plus accounting gaps. Totals exclude unknown Pods and must be described
as partial whenever `accounting_complete` is false. Namespace inventory totals
describe that namespace only, not whole-cluster schedulability or savings.

The helper implements admitted spec accounting for Kubernetes 1.28–1.35:
regular containers, ordered restartable init phases, pod-level supported overrides
and overhead. It follows the upstream [resource helper](https://github.com/kubernetes/kubernetes/blob/v1.35.0/staging/src/k8s.io/component-helpers/resource/helpers.go)
and [scheduler request conversion](https://github.com/kubernetes/kubernetes/blob/v1.35.0/pkg/scheduler/framework/types.go).
It pauses accounting on unsupported versions, pre-default feature-gate cases,
or unresolved spec/status in-place resize accounting. Obtain a version-matched
scheduler metric/source verification rather than treating null as zero. The
collector does not infer LimitRange defaults for unadmitted manifests.

This is a minimal shared inventory, not a full scheduling simulator. Collect
affinity/topology spread, pool/zone minima, PDBs, attachment/IP limits, rollout
surge and failover evidence with targeted sanitized projections. Reuse inventory
in all collector briefs rather than repeating a broad API scan.

## Savings

```bash
python3 {{CORE_DIR}}/scripts/calculate-savings.py --input <run-folder>/calculation-input.json --output <run-folder>/calculations.json
```

Use independent baseline-versus-proposed scenarios, not an additive list of
workload request dollars and node dollars. Example input (synthetic rates):

```json
{
  "currency": "USD", "period": "monthly", "basis": "marginal",
  "rate_source": "supplied scoped rates", "rate_date": "2026-10-01",
  "scenarios": [{
    "id": "S1", "action_ids": ["F1", "F2"],
    "baseline": [{"id": "pool", "kind": "hourly", "quantity": 6, "rate": "0.20", "hours": 730}],
    "proposed": [{"id": "pool", "kind": "hourly", "quantity": 4, "rate": "0.20", "hours": 730}]
  }]
}
```

Hourly components calculate quantity × rate × hours. Fixed components use
`{"id":"commitment", "kind":"fixed", "amount":"900"}`. Preserve unchanged fixed
obligations in both states. For Pod-based CPU/memory use one component per SKU
with total admitted resources and matching rate units. Rates can be decimal
strings in calculation input; result numbers are typed and exact Decimal strings
are retained. The script rejects missing/non-finite/negative input values and
duplicate components/actions/scenarios. Unknown rates mean an unpriced finding,
not zero. A negative saving is a cost increase.

The helper establishes arithmetic, not pricing or feasibility. Assign a billable
resource/SKU once per state and explain overlaps and alternative scenarios. It
cannot detect two different IDs referring to the same physical charge; the
planner must verify that mapping. Do not sum its alternative scenarios.

## Evidence and report contract

Use `references/evidence.schema.json` (Draft 2020-12) for new `evidence.json` files.
The bundled validator implements exactly its used keywords with no dependencies.
Keep `schema_version: 1`, source statuses, explicit units/aggregation, zoned
timestamps or explained nulls, pricing provenance, and cross-referenced findings.
For priced scenarios copy the calculator's components, numeric baseline/proposed/
saving and action IDs; add assumptions. For unpriced scenarios all three cost
values are null and components can be empty. Every priced finding needs a
reconciled scenario, including zero immediate cash impact if stated numerically.

```bash
python3 {{CORE_DIR}}/scripts/validate-evidence.py --evidence <run-folder>/evidence.json --facts-output <run-folder>/report-facts.json --checks-output <run-folder>/evidence-checks.json
```

After evidence passes, embed the exact generated facts once in Markdown:

````markdown
<!-- cost-review-facts -->
```json
<contents of report-facts.json>
```
````

Pass the same JSON to the HTML writer to embed as
`<script type="application/json" id="cost-review-facts">…</script>`.
Escape `<`, `>` and `&` as JSON Unicode escapes in HTML to prevent premature
script termination; never insert unescaped source text. This is a data block,
not executable code. It supplements the full visible plan; it is not a substitute.

If the HTML writer's checker rejects every `script` element, use its documented
script-allowance option only for this inert inline data block, then run the final
contract validator. That validator rejects other script elements and external
sources on the facts block. Record the actual static-check option to avoid
repeated failed attempts or a misleading strict-check claim.

```bash
python3 {{CORE_DIR}}/scripts/validate-evidence.py --evidence <run-folder>/evidence.json --markdown <markdown-file> --html <html-file> --checks-output <run-folder>/report-contract-checks.json
```

The validator checks schema, unique IDs, source availability, dangling evidence/
dependency references, dependency cycles, units, timestamps, pricing provenance,
component arithmetic, savings bounds, filenames, common machine-local path
remnants and identical report fact blocks. It does not prove provider pricing,
placement, workload headroom or visible prose correctness. Inspect visible tables,
totals, estimates/readiness and evidence against JSON, then run the HTML writer's
static and visual checks. Fix errors rather than relabeling a failed check as pass.

## Regression checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s {{CORE_DIR}}/evals -p 'test_*.py'
```

Use supplied fixture cases for end-to-end handler evaluations. Resolve `files`
entries in `evals/evals.json` relative to `{{CORE_DIR}}`, and give the evaluator
absolute runtime paths. Keep saved fixture provenance as standalone filenames.
