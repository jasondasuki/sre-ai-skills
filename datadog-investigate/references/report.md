# Report

Read this at Step 6, when the investigation is over. The mode, the rules of
engagement and the placeholder table stay in `SKILL.md`; the placeholders below
are the ones defined there.

The report is your reply in chat, and nothing is written to disk, so it has to
stand on its own for a reader who was not there and for a caller (such as an
incident coordinator) that records it. Open with the answer: the root cause, or "no
root cause established". Then:

```
## Alarms investigated
<the intake table: each link, monitor, scope, UTC time, and whether it is the
 root-cause alarm, a symptom of it, or independent>

## Root cause
<one or two sentences, plain. Confidence: high | medium | low, and why.>

## Impact
<what, who/where, from when to when, magnitude vs baseline>

## Timeline (UTC)
<the absolute UTC time of each event (change, first symptom, alert, any
 recovery), with its offset from T0>

## Hypothesis tree
- [VALIDATED]   <hypothesis> - <evidence in one line>
  - [VALIDATED]   <sub-hypothesis> - <evidence>
- [INVALIDATED] <hypothesis> - <what was absent or contradicted>
- [INCONCLUSIVE] <hypothesis> - <what is missing; what would resolve it>

## Evidence
<each query: tool, query/filter, time range, and what it showed, with exact
 values and units, the baseline it was compared with, and any gap, truncation, or
 known delay. A missing series is not zero, and notification values are not a
 continuous monitor series.>
<link or ID for the monitor, trace, incident, or change story where available>

## Recommended next steps
<mitigation now (rollback, scale, flag off), fix, and follow-up monitoring.
 Each step names who runs it (a role), whether it is reversible (yes | no |
 partly, and what cannot be undone), and whether it is safe to do immediately or
 needs an owner's call. A step that is not reversible is never safe to do
 immediately. End with one line of offers (do not do them): a Datadog notebook or
 case capturing the investigation, a follow-up on any inconclusive branch, and a
 deep run when a normal run ended low-confidence or inconclusive.>

## Gaps
<telemetry that was missing or too coarse; monitor improvements worth making>

## Method
<the mode (normal or deep); the planner model that actually ran (`{{MODEL}}`, or
 the real one if it differs) and the executor model (`{{SUBAGENT_MODEL}}` in a
 normal run, `{{DEEP_SUBAGENT_MODEL}}` in a deep run); N probes across R rounds run
 by executors; any probe you re-ran yourself, and any that failed>

## Final root cause
<the last section: the constructed causal chain (trigger, mechanism, why it
 crossed the alert threshold, recovery; then ruled out, still open, contributing,
 confidence). Shape and rules are in references/final-root-cause.md;
 read it now.>
```

Rules for the report:

- Every claim in the tree cites a query that was actually run. No evidence, no
  `[VALIDATED]`.
- Distinguish **trigger** (what started it), **root cause** (why it was able to
  happen), and **contributing factors** (why it was worse or slower to detect).
- Report the confidence honestly: **high** when the evidence shows the cause, its
  timing (cause before symptom), and the mechanism; **medium** when one of the
  three is not shown; **low** when the cause fits the evidence but nothing tested
  confirms it. A single correlated deploy with no mechanism is medium at best.
- The reply ends with the Final root cause section: nothing follows it. The
  opening "Root cause" is the quick answer; the closing one is the argument that
  earns it, so the two must agree.
