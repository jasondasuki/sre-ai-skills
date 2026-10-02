# Report template

Write the report in Markdown to `{{OUTPUT_DIR}}/matlev-<date>.md`. Save the raw
assessor returns beside it in `{{OUTPUT_DIR}}/matlev-<date>-raw/`. Keep prose
short; tables carry the substance.

```
# MatLev assessment - <date>

Planner: {{MODEL}}. Assessors: {{SUBAGENT_MODEL}} at effort {{SUBAGENT_EFFORT}}.
Rounds: <n>. Scale document: {{SCALE_DOC}} (version read: <date in its header>).

## 1. Summary
<three to five sentences: the overall picture, what moved, what is blocking the
 next level most often.>

## 2. Sources assessed
| Source | Assessed | Notes |
| Each repository, the clusters, Datadog, Cloudflare. "Down" or "partial" with why.

## 3. Scorecard
| Capability | Previous | Assessed | Basis | Why | Next | North |
Basis is `configured` or `confirmed live <date>`. "Why" names the ladder question
where the capability stopped, with one citation.

## 4. What changed against the current scorecard
For each capability whose level moved, or whose basis moved from configured to
confirmed live: before, after, and the evidence.

## 5. Contradictions
Each place two sources disagreed (documentation versus repository, repository
versus cluster, cluster versus monitoring). Say which you believe and why, and
what to fix.

## 6. Gaps and risks
Unmonitored capabilities, hand-applied packages, live-but-undeclared resources,
unpinned references, untested recovery. Ordered by how much each caps the rating.
Do not inflate severity.

## 7. Not assessed
Capabilities and questions with no evidence, and what would be needed.

## 8. Proposed scorecard patch
The exact rows to change in the scale document, ready to apply. Nothing has been
applied.

## 9. Evidence appendix
Per source: the questions, the observations, the citations, grouped by capability.
Exclude anything that is, or could be, a secret or customer data.
```
