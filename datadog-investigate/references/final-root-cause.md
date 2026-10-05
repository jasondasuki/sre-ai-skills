# Final root cause

Read this when you write the report (Step 6). It holds the closing root cause, the
part of the report that needs the most care. The diagram and the page layout are
owned by the report skill's `hypothesis-investigation` profile.

## Contents

- Final root cause: the closing chain
- Accuracy rules

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

## Accuracy rules

- Do not state a mechanism word (sequential, parallel, retried, queued) unless a
  span, log, or metric shows it.
- Check dose and response: say when a smaller occurrence of the cause did not move
  the symptom, and when the timing of the two series differs by bucketing.
- A diagram is the same findings in a better container. Nothing appears in it
  that is not in the Evidence section; the report skill's profile holds the
  diagram's own spec.
