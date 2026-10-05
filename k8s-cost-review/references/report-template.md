# Report and evidence outputs

Write in a dated run folder under `{{OUTPUT_DIR}}`, using a filesystem-safe scope
slug and UTC timestamp to avoid overwrites:

- `k8s-cost-review-YYYY-MM-DD-<scope>.md`
- `evidence.json`
- Optional sanitized role-specific evidence files.

Write the finished HTML under `{{HTML_OUTPUT_DIR}}` using `{{REPORT_SKILL}}` and
its `cost-review` profile. Its title and filename rules govern the HTML name.
The Markdown/evidence run folder and HTML filename share the review start time
and scope so the outputs can be matched. Do not overwrite an existing run.

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

## Report files and provenance
<Review start and generation times in UTC, actual planner model, collector models
and parallel/serial mode, absolute Markdown/HTML/evidence paths, HTML markup and
visual check results or the specific unavailable check.>
```

## HTML writer brief

After validating the Markdown and evidence, load `{{REPORT_SKILL}}` and provide:

- **Profile:** `cost-review`.
- **Output folder:** `{{HTML_OUTPUT_DIR}}` or the user's explicit HTML override.
- **Page-design skill:** `{{PAGE_DESIGN_SKILL}}` (overrides the writer's default).
- **Time and title facts:** review start date/time in UTC and the resolved scope
  label; the HTML writer records its own generation time in UTC.
- **Producer facts:** producing skill name, live or supplied-evidence mode,
  actual planner model, actual collector models and parallel/serial execution,
  contexts/namespaces, history window, currency, pricing basis/date, and
  `{{MONTH_HOURS}}` or the actual period hours. Use unknown when a fact is absent.
- **Findings:** validated summary, baseline, complete prioritized action details,
  combined scenarios, rejected hypotheses, evidence gaps, implementation order,
  and evidence index. Preserve stable IDs and all limitations.
- **Source files:** absolute Markdown and evidence paths. Add the returned HTML
  path and check results to both after generation. Pass only existing source URLs;
  do not invent links from resource identifiers.

The HTML must retain the full actionable plan and evidence detail, using native
`details` where useful. Keep capacity benefits separate from currency savings and
conditional scenarios separate from ready savings in the summary and any visual.
Use tables/stat tiles when no real time series exists. Follow the page-design
skill's static checker and desktop/phone, light/dark visual review. Keep rebuild
helpers beside the Markdown/evidence, with only the finished page in the HTML
folder. If an output or check is blocked, return the completed paths and the
specific blocker rather than claiming all formats passed.

## Sanitized evidence JSON

Use JSON with these keys; add details as useful, keeping numbers typed and
unknowns null rather than zero. Evidence and findings must cross-reference.

```json
{
  "scope": {"contexts": [], "namespaces": [], "mode": "live-or-supplied"},
  "collected_at": "ISO-8601",
  "review_started_at": "ISO-8601 UTC",
  "outputs": {"markdown": null, "html": null, "evidence": null},
  "report_checks": {"markup": null, "visual": null, "limitations": []},
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
