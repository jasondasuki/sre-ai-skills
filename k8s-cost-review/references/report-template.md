# Report and evidence outputs

Write in a dated run folder under `{{OUTPUT_DIR}}`, using a filesystem-safe scope
slug and timestamp to avoid overwrites:

- `k8s-cost-review-YYYY-MM-DD-<scope>.md`
- `evidence.json`
- Optional sanitized role-specific evidence files.

Use this report structure, omitting empty inventory tables but keeping explicit
source status and an action for missing decisive evidence.

```markdown
# Kubernetes cost review — <scope> — <date>

## Executive summary
<Top actions, marginal monthly estimate/range or unpriced, readiness, blockers.>

## Scope and evidence coverage
<Contexts/namespaces, provider/region/billing model, historical window,
resolution/coverage, live versus supplied evidence, source availability, currency,
pricing basis/date, repository revision/drift.>
<For GKE: billing per pool/ComputeClass, allocation status and coverage start,
export table/source status, gross versus net credits, unallocated/overhead and
unattributed costs, and any provider recommendation's window/limitations.>

## Baseline
<Pools/nodes/shape/min-max, allocatable, effective scheduled requests, observed
usage and peaks, major workloads/scalers and independently billed resources.>

## Prioritized actions
| ID | Readiness | Target/change | Marginal monthly saving | Confidence | Effort | Dependencies/overlap |
|---|---|---|---|---|---|---|

### <ID>: <action>
- Target and ownership: <context/resource + actual repo path/key or unknown>.
- Evidence: <evidence IDs; observed values with window and units>.
- Before -> after: <specific supported config or exact measurement task>.
- Mechanism: <change -> feasibility -> billable reduction>.
- Estimate: <equation, rates/hours, currency, basis; capacity separately>.
- Prerequisites and reliability constraints: <HPA/PDB/peaks/retention/etc.>.
- Rollout and rollback: <sequence/canary and triggers/config to restore>.
- Verification: <demand-normalized runtime, node/resource, and billing checks>.

## Combined savings scenarios
<Baseline-versus-proposed effective costs. List mutually exclusive alternatives,
overlap groups and fixed commitment charges. Sum only distinct marginal savings.>

## Rejected hypotheses and evidence gaps
<What looked wasteful but is constrained, missing source/rate/window, and the
smallest evidence collection needed to move forward.>

## Implementation order
<First changes, dependent changes, owners if evidenced, effort, and success checks.>

## Evidence index
<IDs mapping to sources/commands/queries/file sections, timestamps, scopes,
units, aggregations, limitations, and sanitized local evidence files.>
```

Use JSON with these keys; add details as useful, keeping numbers typed and
unknowns null rather than zero. Evidence and findings must cross-reference.

```json
{
  "scope": {"contexts": [], "namespaces": [], "mode": "live-or-supplied"},
  "collected_at": "ISO-8601",
  "window": {"start": null, "end": null, "coverage_notes": []},
  "sources": [{"name": "source", "status": "available-or-unavailable", "reason": null}],
  "observations": [{
    "id": "E1", "resource": "scoped-resource", "source": "source",
    "query_or_reference": "command/query or supplied file section",
    "timestamp": null, "aggregation": null, "value": null, "unit": null,
    "limitations": []
  }],
  "findings": [{
    "id": "F1", "readiness": "ready-or-conditional-or-measure-first-or-rejected",
    "target": "resource", "action": "proposed change",
    "evidence_ids": ["E1"], "dependencies": [], "overlap_group": null,
    "saving": {"low": null, "high": null, "currency": null, "period": "monthly", "basis": "marginal", "formula": null, "assumptions": []},
    "capacity_benefit": null, "confidence": "high-or-medium-or-low"
  }],
  "scenarios": [],
  "gaps": []
}
```
