# Profile: hypothesis-investigation

The report format for an investigation that builds a hypothesis tree, tests each
branch against telemetry, and ends with a validated root cause or an honest
"inconclusive". Read this when the brief names this profile (Step 3 of the core).
The shared page rules, hard rules, and verification are in the core; this file
holds what is specific to this format: the title, the file name, the sections, and
the visual investigation.

## Contents

- Title and file name
- Sections, in order
- Visual investigation: path, comparison, timeline, and trace
- Hypothesis map
- Accuracy and visual checks

## Title and file name

**Report title (required):** every report's title contains the date, the time,
and the incident title:

```
YYYY-MM-DD HH:MM UTC - <incident title>
```

- **Date and time** are `T0`, when the alarm fired or the incident began, in
  UTC (for several alarms in one cluster, the earliest `T0`). Always say `UTC`.
  The time the report was generated goes in the header and footer, not the title.
- **Incident title** is the name Datadog uses: the incident's title, else the
  monitor's name (with template variables like `{{host.name}}` filled in from
  the alerting group, or dropped), else a short plain description you write
  from the problem statement ("checkout 5xx spike after deploy"). Keep it
  under about 90 characters, trimming the middle rather than the ends. For
  several unrelated alarms, name the root-cause alarm, then " (+N more)".
- Example: `2026-10-02 14:02 UTC - [prod] checkout p99 latency above 2s`.

Use this exact string in all three places: the `<title>` element, the page
`<h1>`, and the `title` you would pass if the report is later published. This
is a deliberate exception to the two-to-four-word title guidance in
`{{PAGE_DESIGN_SKILL}}`; the user's rule wins, so do not shorten it.

**Filename:** `YYYY-MM-DD-HHMM-<slug>.html`, using the same `T0` date and time
as the title (UTC) and a short kebab-case slug of the service and symptom (for
example `2026-10-02-1402-checkout-latency.html`). A deep run adds `-deep` to the
slug (`2026-10-02-1402-checkout-latency-deep.html`). Never overwrite an existing
report; if the name exists, append `-2`. For a follow-up on the same alarm,
write a new file and link back to the earlier one.

## Sections, in order
1. **Header:** the `<h1>` is the report title exactly as the Title section above defines it
   (date, time, incident title). Beneath it: the UTC incident window, the time the
   report was generated, a confidence pill (high / medium / low), an overall
   status pill derived from it (root cause found for high or medium; inconclusive
   for low, or no root cause), and a mode pill ("Normal investigation" or "Deep
   investigation").
2. **Root cause card:** the one or two sentence answer, the trigger vs root
   cause vs contributing factors, and why the confidence is what it is.
3. **Visual investigation:** a connected request-path or dependency diagram,
   baseline-versus-incident comparison charts when numeric evidence exists, and
   an alert timeline chart when time points exist. Add a trace-duration bar only
   when an exemplar was retrieved. Adapt headings to the symptom: errors, latency,
   saturation, availability, or a telemetry gap. Every number comes from recorded
   evidence. Read the full visual specification below before building this section.
4. **Impact tiles:** what, where, start and end, and magnitude vs baseline,
   as a short row of stat tiles.
5. **Alarms investigated:** the intake table. Each row links back to the
   original Datadog URL and is tagged root-cause alarm, symptom, or independent.
6. **Timeline:** a vertical UTC timeline of the change, first symptom, alert,
   and recovery.
7. **Hypothesis tree:** begin with a connected visual hypothesis map, followed by
   nested, collapsible (`<details>`) evidence summaries. Each node shows a
   status pill and a one-line evidence summary. Status is conveyed by an icon
   and a text label as well as colour: validated, invalidated, inconclusive.
   Invalidated branches are collapsed by default; validated and inconclusive
   ones are open so the reader sees both the supported chain and unresolved gaps.
8. **Evidence:** one entry per query actually run, by you or an executor: tool,
   query or filter, time range, result in one line, and whether you verified it
   yourself. Put raw queries in a monospace block and link to the Datadog object
   (monitor, trace, incident, change story) when you have its URL. When a
   documentation lookup (Step 5, "No data is a finding about the data") changed
   which names you queried, record the document and what it corrected.
9. **Next steps:** split into "do now" and "follow up", each marked with who runs
   it, whether it is reversible, and whether it needs an owner's decision.
10. **Gaps:** missing telemetry and monitor improvements.
11. **Method:** how the work was split and what you re-ran yourself. In a deep run,
    also the extra checks (dependency walk, disconfirmation probes, dose and
    response).
12. **Final root cause:** the same chain as the chat reply's close, given the
    strongest visual weight after the header card. In a deep run it also carries
    the quantified contribution, the recurrence line, and the alternatives not
    fully excluded (the brief carries them).
13. **Footer:** generated by the producing skill (named in the brief); the mode;
    planner model; executor model with the number of rounds and probes; and the
    original alarm links. The brief supplies these values. Name the model that
    actually ran, even when it differs from the one the producer's handler is
    configured for.

Load `{{CHART_SKILL}}` before drawing any chart in the visual investigation.

## Visual investigation

Place this immediately after the root cause card, with a header link labelled
"Visual diagrams". Start with a short reading cue explaining what each visual
helps the reader decide. Use actual connected diagrams and quantitative charts;
a row of unconnected text cards is not enough.

Build from the producer's findings and visual evidence. An inconclusive result
still has a visual investigation: draw the supported relationships and mark
where attribution stops. When a trace or numeric series is unavailable, omit
only that unsupported chart and state the gap. Retain the path/dependency diagram
and hypothesis map. If no path relationships were established, show the observed
alert entity and the missing attribution boundary without inventing hops.

### 1. Request path

Draw the verified service/dependency relationships, with branches when multiple
traffic paths exist. Use inline SVG or a responsive connected HTML diagram.

- Each node carries its name, an icon and status text, a concise observed fact,
  and its supporting evidence ID. Use narrow descriptions such as "Ready
  snapshot" when that is what was checked; readiness does not prove full request
  success or historical health.
- Solid connectors mean verified relationships. Dashed connectors mean candidate
  paths reported in the findings, with a legend. A verified relationship alone
  does not establish that failing requests used it; label attribution separately.
- Highlight the error, delay, or saturation location only when established.
  Otherwise mark the missing link explicitly, such as "Hostname unknown" or
  "Origin status unavailable". Keep unmeasured branches visibly unknown.
- Number hops only when the order is established. Avoid arrows that imply an
  unproven causal chain, and note when candidate paths overlap rather than forming
  an exclusive partition.

### 2. Baseline versus incident

When the findings carry numeric comparisons, draw paired bars with exact values
and a neighbouring table. This works even when no continuous time series exists.

- Label units, dimensions, UTC windows, and source evidence IDs. Label the two
  series clearly; outline versus filled bars can distinguish them without colour.
- Start count bars at zero. Use a common scale for the same unit; separate panels
  for different units. Keep chart text and value labels clear of the bars.
- Distinguish scope and population. Edge-wide and single-ingress counts can be
  shown in separate rows, but cannot be subtracted or treated as matched requests.
  Falling origin errors alone do not prove the edge caused an increase.
- State when comparison windows differ from the monitor evaluation window. A
  separately computed ratio is not the monitor's evaluated ratio unless the
  inputs, aggregation, and window actually match.

### 3. Alert timeline and metric samples

Draw retrieved alert values and relevant metric samples on a shared UTC time
axis, with separate stacked panels for different units. The lower panel is a
candidate or correlated signal until causality is established; name it accordingly.

- Plot only returned points. Sparse samples are discrete markers, not a connected
  curve; missing minutes are unplotted, not zero. Notification-transition values
  are not a continuous monitor series.
- Draw retrieved warn/critical thresholds only on the matching alert-metric panel.
  Shade alarm episodes only when transition history establishes their bounds.
  Label observed peaks as such rather than claiming a peak over missing data.
- Mark T0 from the producer's timeline. Receipt time, re-warning, recovery
  notification, request onset, and sustained recovery are distinct facts.
- Explain bucket size, timestamp meaning (start, completion, export, or other),
  freshness/delay, and gaps in the caption. Say when timestamp semantics are
  unknown; exporter timestamps and delayed Analytics cannot establish exact user
  impact onset. Show lag on the chart only if it was actually measured.
- Give the exact plotted values in a labelled table with UTC timestamps and
  evidence citations. When there are events but no numeric time points, use a
  connected event timeline with the recorded timestamps instead of inventing a
  metric curve.

### 4. Where the time goes (latency with an exemplar)

When you have an exemplar trace, draw a bar of its child spans sized by their
real durations.

- Label the bar with the summed time and the wall-clock time of the parent.
- Call spans "back-to-back" or "overlapping" only as their start and end times
  show. Compare the sum of the child durations with the parent's duration before
  using a word like "sequential": a sum larger than the parent means some overlap.
- If you can, add a second, shorter bar for the same work at the baseline
  latency and label it an estimate (count of calls multiplied by the baseline
  median).
- Say it is one trace if it is one trace.

## Hypothesis map

Draw an inline connected map of the observed symptom and the hypotheses tested.
Keep every original hypothesis ID, order, status, and parent-child relationship.
A flat set of hypotheses fans out from the symptom; do not add deeper causes that
the producer never established. Map edges represent investigated branches unless
explicitly labelled as a validated causal relationship.

Each node shows its hypothesis label, an icon and text status (validated,
invalidated, inconclusive), a one-line finding, and evidence IDs. Inconclusive
nodes state the missing observation. Follow the map with the expandable evidence
summaries; the map supplements the evidence rather than hiding it.

## Accuracy and visual checks

- Do not state a mechanism word (sequential, parallel, retried, queued) unless a
  span, log, or metric shows it.
- Check dose and response: say when a smaller occurrence of the cause did not move
  the symptom, and when the timing of the two series differs by bucketing.
- A diagram is the same findings in a better container. Nothing appears in it
  that is not in the Evidence section.
- Use theme tokens for SVG text, lines, fills, grid, and status colours. Each SVG
  has a `viewBox`, `role="img"`, and unique `<title>`/`<desc>` IDs referenced by
  `aria-labelledby`. Describe uncertainty and scope in its caption.
- Use a readable minimum width inside an independently horizontally scrollable
  container when a diagram cannot reflow. Make overflow keyboard-accessible with
  a labelled focusable region; the page itself must not scroll sideways on a phone.
- Check light and dark themes at desktop and phone widths. Inspect every diagram
  for clipped labels, text overlaps, connector collisions, readable contrast, and
  legends that agree with the connections. Verify the plotted values, thresholds,
  time windows, hypothesis statuses, and citations against the brief.
- Minimum completion check: a connected path/dependency or attribution-boundary
  diagram, a connected hypothesis map, and comparison/time charts for the numeric
  data actually supplied. A missing trace or full series is not a reason to ship
  a text-only report.
