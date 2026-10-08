# Deep investigation

Read this when the run is in deep mode. Deep mode keeps the same loop as normal
mode (hypotheses, probes, executors, consolidation, report) and changes how far
it goes, how hard it checks itself, and what the report adds. Use the `DEEP_`
counterparts of the executor, round, query-limit, and executor-model variables.

## Contents

- When deep mode applies
- What changes, step by step
- Verification the planner must do itself
- What the report adds
- Stopping

## When deep mode applies

Use deep mode when the user asks for it in any form ("deep", "deep dive", "deep
investigation", "thorough", "in depth", "full RCA", "dig deeper", "go deeper"),
or when they follow a normal run that ended low-confidence or inconclusive with a
request to continue. Otherwise the run is normal. Never switch to deep on your
own: say in one line at the end of a normal run that a deep run is available.

State the mode in one line before the first query, so the user knows the cost:
"Deep investigation: up to N rounds, M executors per round."

## What changes, step by step

**Step 1, context.** Add three things to the normal checks.
- *History.* Pull the monitor's and group's transitions for the last 14 days.
  Note how often it fires, whether it flaps, and at what times of day. A pattern
  that repeats at the same minute each day is a different problem from a one-off.
- *Baselines.* Compare the incident window with the same window the previous day
  and the previous week, not only with the hour before. A "normal" that moves by
  time of day is invisible against a baseline taken right before the incident.
- *Documentation.* Read `{{DOCS_DIR}}` for every system in the suspected path
  before round one, not only when data is missing: architecture, owners, the
  documented metric names and labels, dashboards, and runbooks.

**Step 2, hypotheses.** Generate 6 to 10 instead of 3 to 6. Add the layers normal
mode skips: a dependency of a dependency, the control plane against the data
plane, configuration drift, a slow trend over days, a change in who is calling or
in the mix of requests, and an external provider (check provider status). Keep
the ranked list and update it each round.

**Step 3, plan.** Use the deep query limit per probe and these wider windows:
`T0 - 3h` to `T0 + 1h`, plus a 7-day trend for any hypothesis that could build
slowly. Every probe splits by the dimensions that could concentrate it (version,
pod, zone, endpoint, tenant, caller) and is not allowed to return a bare total.

**Step 4, dispatch.** Use the deep executor count and the deep executor model.
Everything else about the brief is unchanged.

**Step 5, consolidate.** Add two moves for every validated hypothesis.
- *Walk the dependency.* Follow the chain at least two levels down, and test
  whether the cause is shared: look at other callers or consumers of the same
  dependency in the same minutes. If they were affected too, the cause is on the
  shared path; if only this one was, it is specific to this path.
- *Try to disprove it.* Write down what would be true if the hypothesis were
  wrong and probe for exactly that, once. A hypothesis that survives its own
  disconfirmation probe is validated; one that was only never contradicted is not.

## Verification the planner must do itself

Normal mode has the planner re-run the decisive queries. Deep mode re-runs the
query behind every validated node, and also:

- **Dose and response.** Take every occurrence of the suspected cause in the
  window, not only the ones near the alert. For each, did the symptom follow? List
  the occurrences that did not move the symptom, with their size. A cause that
  only works above a size is still a cause, and the size is a finding.
- **Quantify.** Say how much of the symptom the cause explains (for example the
  share of slow requests that show it, or the change in the metric if the cause
  were absent), not only that it is present.
- **Two exemplars.** For a mechanism seen in a trace or a log, confirm it in at
  least two independent examples, one from each episode when there is more than
  one.
- **Word check.** Do not state a mechanism word (sequential, parallel, retried,
  queued) unless a span, log, or metric shows it.

## What the report adds

On top of the normal report:

- A **Recurrence** line: how often this monitor and group fired in the last 14
  days, and whether earlier episodes share the cause.
- A **Quantified contribution** line in the final root cause: how much of the
  symptom the chain explains.
- An **Alternatives not fully excluded** list: hypotheses the data made unlikely
  but did not rule out, each with what would settle it.
- A **Monitor tuning** note when the monitor flaps: the share of the last 7 days
  the series spent above the warn line, and a threshold or window that would have
  fired only on real events, with the numbers behind it.
- The Method section names the mode as deep and lists the extra checks.

## Stopping

Deep mode uses up to the deep round limit, but stops sooner when all of these
hold: the chain is validated down to a human change, an external failure, or a
capacity limit; every validated node passed its disconfirmation probe; and the
dose-and-response check is written down. If the limit is reached with a link
still open, say which link and what data would close it, rather than extending
the run.
