# Profile: hypothesis-investigation

The report format for an investigation that builds a hypothesis tree, tests each
branch against telemetry, and ends with a validated root cause or an honest
"inconclusive". Read this when the brief names this profile (Step 3 of the core).
The shared page rules, hard rules, and verification are in the core; this file
holds what is specific to this format: the title, the file name, the sections, and
the diagram.

## Contents

- Title and file name
- Sections, in order
- Diagram section: how the delay builds up
- Accuracy rules for the diagram

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
3. **Diagram - how the delay builds up:** a clear visual of the mechanism, in up
   to three parts: the request path as cards for each hop, a bar of where the
   time goes inside one exemplar trace, and a stacked time chart of the alert's
   metric over the suspected cause. Every number comes from a query you ran. The
   full spec is in the Diagram section below; read it before building this section.
4. **Impact tiles:** what, where, start and end, and magnitude vs baseline,
   as a short row of stat tiles.
5. **Alarms investigated:** the intake table. Each row links back to the
   original Datadog URL and is tagged root-cause alarm, symptom, or independent.
6. **Timeline:** a vertical UTC timeline of the change, first symptom, alert,
   and recovery.
7. **Hypothesis tree:** nested, collapsible (`<details>`). Each node shows a
   status pill and a one-line evidence summary. Status is conveyed by an icon
   and a text label as well as colour: validated, invalidated, inconclusive.
   Invalidated branches are collapsed by default; validated ones are open.
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

Load `{{CHART_SKILL}}` before drawing the time chart in the diagram section.

## Diagram section: how the delay builds up

A clear visual of the mechanism, made of up to three parts. Build each one only
from data you retrieved; if a part has no data (no trace, no time series), leave
it out and say so in one line instead of drawing a stand-in.

### 1. Request path

The hops a request travels, in order, from the service and dependency map you
found in Step 1.

- One card per hop: the hop's name, a status chip, and one line of evidence.
- The chip states healthy, slow, or unknown in words and with an icon, never by
  colour alone.
- Mark the hop where the extra time appears.
- Use CSS grid or flex with a minimum card width so the cards wrap on a phone.
- Number the hops ("Hop 1") only because the order is real.

### 2. Where the time goes

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

### 3. Time chart

The key series on one shared time axis, stacked: the alert's own metric on top
and the suspected cause below.

- Draw the alert's warn and critical lines, shaded bands for the alarm episodes,
  and labels on the peaks.
- Use inline SVG with a `viewBox`. Every point comes from a query you ran. Colour
  lines, grid, and text from the theme tokens so both themes read.
- Put the chart in its own `overflow-x: auto` container with a minimum width, so
  the page never scrolls sideways on a phone.
- Give the SVG a `<title>` and `<desc>` that state what it shows.
- In the caption, say how each series is bucketed (completion time or start time)
  when that can shift the peaks by a minute.
- If the chart shows a smaller occurrence of the suspected cause that did not move
  the symptom, say so in the caption. A cause that only shows up at one size is
  still a cause, but the reader needs to know the size.

## Accuracy rules for the diagram

- Do not state a mechanism word (sequential, parallel, retried, queued) unless a
  span, log, or metric shows it.
- Check dose and response: say when a smaller occurrence of the cause did not move
  the symptom, and when the timing of the two series differs by bucketing.
- A diagram is the same findings in a better container. Nothing appears in it
  that is not in the Evidence section.
