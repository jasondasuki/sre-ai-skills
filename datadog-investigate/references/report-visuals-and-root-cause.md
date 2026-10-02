# Report visuals and the final root cause

Read this when you write the report (Step 6) and the HTML page (Step 7). It holds
the two parts of the report that need the most care: the diagram section and the
closing root cause.

## Contents

- Diagram section: how the delay builds up
- Final root cause: the closing chain
- Accuracy rules that apply to both

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

## Final root cause: the closing chain

The last content section of the report, and the end of the chat reply. The
opening "Root cause" is the quick answer; this is the argument that earns it, and
the two must agree.

Write it after all the evidence is in, in this shape:

1. **Trigger.** What started it, with the numbers and the UTC minutes.
2. **Mechanism.** How the trigger became the symptom (the amplifier).
3. **Why it crossed the alert threshold.** The link between the mechanism and
   the exact metric the monitor measures.
4. **Recovery.** What ended it, and when.

Then, as short labelled lines:

- **Ruled out:** the branches the data rejected.
- **Still open:** links in the chain the data could not reach.
- **Contributing factors:** why it was worse or slower to detect.
- **Confidence:** high, medium, or low, with the reason.

Every link cites the evidence IDs behind it and uses only validated nodes of the
hypothesis tree. An unproven link is named as open and is never filled in with a
plausible guess.

## Accuracy rules that apply to both

- Do not state a mechanism word (sequential, parallel, retried, queued) unless a
  span, log, or metric shows it.
- Check dose and response: say when a smaller occurrence of the cause did not move
  the symptom, and when the timing of the two series differs by bucketing.
- A diagram is the same findings in a better container. Nothing appears in it
  that is not in the Evidence section.
