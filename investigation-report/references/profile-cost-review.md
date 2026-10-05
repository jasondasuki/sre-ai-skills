# Profile: cost-review

Format a completed Kubernetes cost review as one self-contained HTML page. The
producer owns the observations, calculations, proposed changes, and evidence
limits. Read this profile when the brief names `cost-review`; follow the shared
core for escaping, page style, destination selection, and verification.

## Title and file name

**Report title:**

```
YYYY-MM-DD HH:MM UTC - Kubernetes cost review: <scope>
```

Use the review start date/time in UTC and the producer's resolved cluster/scope
label. Use exactly the same string for `<title>` and `<h1>`. The report generation
time belongs in the header and footer. Keep the scope readable; wrap a long title
rather than hiding identifiers that distinguish the reviewed cluster.

**Filename:** `YYYY-MM-DD-HHMM-k8s-cost-review-<scope-slug>.html`, with the same
review start date/time as the title and a filesystem-safe kebab-case scope slug.
Write directly in the caller's HTML output folder. Never overwrite a report;
append `-2`, then `-3`, and so on if the name exists. A follow-up gets a new file.

## Sections, in order

1. **Header:** report title, contexts/namespaces, live or supplied-evidence mode,
   review start and report generation times in UTC, and a text status such as
   ready actions / conditional savings / measure first. Derive status from the
   producer's findings; do not upgrade confidence.
2. **Executive summary:** the highest-priority changes, their dependencies, and
   the savings that can be defended. Put conditional estimates beside their
   blockers. Show unpriced benefits as unpriced and unknown values as unknown.
3. **Scope and evidence coverage:** provider, region, resource-level billing
   model, history window/resolution/coverage, source availability, currency,
   pricing basis/date, and repository revision/drift. For GKE, retain allocation
   status/coverage start, export-source status, credits, unattributed/overhead
   costs, and provider-recommendation limitations when supplied.
4. **Baseline:** node/pool inventory, allocatable capacity, effective requests,
   observed demand/peaks, scalers, and independently billed resources. Clearly
   distinguish requests, limits, usage, capacity, and cash cost.
5. **Prioritized actions:** an index table with stable finding ID, readiness,
   target/change, marginal monthly saving, confidence, effort, and
   dependencies/overlap. Follow it with each action's full target and ownership,
   evidence IDs, before/after configuration, savings mechanism/formula/rates,
   capacity benefit, prerequisites, reliability constraints, rollout, rollback,
   and workload/resource/billing verification. Use native `details` for depth.
6. **Combined savings scenarios:** baseline and proposed effective costs, distinct
   marginal savings, fixed commitment charges, overlap groups, and mutually
   exclusive alternatives. A single total may include only compatible actions
   the producer combined; do not add request savings to the same node savings.
7. **Rejected hypotheses and evidence gaps:** constraints that disprove a
   proposal, missing decisive sources, and the smallest next measurement tasks.
8. **Implementation order:** ordered changes, their dependencies, evidenced
   owners or unknown ownership, effort, rollback triggers, and success checks.
9. **Evidence index:** original IDs, commands/queries or supplied file sections,
   timestamps, scope, units, aggregation/window, and limitations. Show only
   sanitized snippets. Use links only for URLs actually supplied by the brief.
10. **Report files and provenance:** Markdown, evidence, and final HTML filenames,
     static and visual check status (or exact blocker), and a footer naming
    the producer, actual planner and collector models, parallel/serial mode,
    review scope, estimation period hours, and generation time in UTC.

Keep every section, even when its content is a short statement of unavailable
evidence. All material findings and assumptions from the validated source report
must remain accessible; summary cards do not replace action/evidence details.

## Visuals

- Lead with three to five points the reader should act on. Pair readiness and
  confidence colours with text labels; money tiles state currency and period.
- Use paired baseline/proposed tiles or a table for exact scenario arithmetic.
  Keep ready and conditional savings separate. A capacity tile is not a cash tile.
- Show implementation dependencies as numbered steps or a small flow diagram
  only when the producer supplied those dependencies. If using SVG, follow the
  selected page-design skill's accessibility and responsive layout rules.
- A cost-composition bar requires complete compatible component values from the
  same scenario/basis. Preserve negative savings as increases and retain credits.
  Do not draw a utilization trend without retrieved time-series points; use a
  labelled snapshot/window table instead. Follow the writer's chart guide before
  drawing a chart.

## Content checks

- Verify all finding/evidence IDs against the Markdown and JSON; keep their
  order and cross-references. Check numerical agreement, units, totals, and the
  readiness/overlap classification in the summary as well as the detail.
- State estimates as estimates and proposals as proposed. No rollout, allocation
  enablement, resource removal, or realized savings may be claimed without the
  producer's recorded evidence of it.
- Retain HPA interactions, placement/headroom limits, commitment consequences,
  retention dependencies, and GKE allocation gaps beside the affected estimates.
- Follow the selected page-design skill's markup checker and desktop/phone,
  light/dark render checks. Report unavailable checks honestly in provenance.
- Apply the shared core's portable-reference rules throughout the page, including
  expanded evidence blocks: verified GitHub links for scoped repository sources,
  filenames for companion artifacts, and no machine-local directory paths.
