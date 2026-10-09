# Hygiene checks

`alarmctl.py inspect` runs the definition checks first; they need no history and
show no monitor text. The history checks go to executors. Every number in the report comes from a query, and the
report says which window it covers.

## Definition checks (from the monitor itself)

| Check | Finding when | Typical fix |
|---|---|---|
| Owner | no team or owner tag | add the tag, or route the notification to the owning team |
| Runbook | message has no runbook or next step | add one line saying what to check first |
| Priority | none set | set one, so paging policy can use it |
| Recovery | no recovery threshold on a flapping metric | add a recovery threshold with hysteresis |
| Evaluation | no evaluation delay on a metric that arrives late; no full-window requirement on a spiky one | set the delay; require the full window |
| No-data | notifies on no data for a sparse or batch source | stop notifying on no data, or add a longer window |
| Template tags | message holds tags that never resolve | fix or remove them |
| Muting | muted or silenced with no end date, or a downtime that never ends | end it or delete the monitor |
| Duplicates | two monitors share the same query and scope, or one is a strict subset of another | keep one, merge the notification lists |
| Routing | notifies a handle or channel that no longer exists or nobody reads | repoint it |
| Leaks | message holds a credential, address, or customer name | redact it (Mode 1) and rotate if a credential |

## History checks (from executors, over `{{LOOKBACK_DAYS}}` days)

| Check | Observation | Finding when |
|---|---|---|
| Transitions | count of entries into alert state | more than `{{NOISY_TRANSITIONS}}` |
| Flaps | alerts that recovered within `{{FLAP_MINUTES}}` minutes | more than half of transitions |
| Time in alert | median and longest duration in alert | median under the flap time, or longest over the window (stuck) |
| No-data share | fraction of the window in no data | over a fifth |
| Action link | any incident, case, acknowledgement, or comment tied to the alert | none in the whole window while transitions are many |
| Stale | the metric, log, or tag set the monitor queries has no data in the window | no data at all |
| Threshold fit | share of the window the query value sits above the threshold | the threshold sits inside normal variation (fires more than a few percent of the time) |

A monitor with many transitions and no action link is the strongest sign of noise.
A monitor with few transitions is not "good" by that alone: check that it can
still fire (stale and no-data rows).

## From finding to proposal

The report is built by the report skill from the plan (see `change-plan.md`), so
a hygiene result is a list of proposals, one per field change, each carrying:

- the monitor and the exact field (for example `options.renotify_interval`);
- the proposed value;
- the evidence: the measurement or definition flag behind it, with the window;
- `alerts_removed`: the alerts the change should remove over the window, from the
  measurements (leave it out when you cannot compute it; never estimate);
- `detection_cost` and `risk`: what detection could be lost and how it is kept;
- who must approve.

Rank by alerts removed per unit of detection risk. Mark a finding `inconclusive`,
and propose nothing for it, when an executor could not get the history. Never
present a guess as a number. A monitor that guards a customer-facing symptom is
never proposed for removal without saying what replaces it, and removal is not a
change this tool makes at all.
