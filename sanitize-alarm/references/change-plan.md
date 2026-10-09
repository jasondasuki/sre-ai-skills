# Change plan: files, proposals, and approval

A change plan is a file the scripts build and a report a person reads. Everything
in the plan is safe to show: it holds proposed text and a hash of each current
value, never the current value itself.

## Files in a run folder

| File | Holds | Safe to show |
|---|---|---|
| `fetched.json` | raw monitors as read from the API | **No.** Never open it. Deleted at the end |
| `changes.json` | the plan: items, plan ID, review notes | Yes |
| `proposals.json` | your proposals for modes 2 and 3, input to `build` | Yes (it holds only text you wrote) |
| `approved.json` | the runner's approval, bound to a plan ID | Yes |
| `rollback-<plan id>.json` | prior values of non-credential fields | Treat as private |
| the report | the HTML page for the runner | Yes |

## Plan items

`changes.json` has `plan_id`, `scope`, `modes`, `items`, and `review_notes`. Item
IDs (`c001`, `c002`, ...) are assigned in order whenever the plan is built, and
the plan ID is a hash of the items, so any change to the plan gives it a new ID.
An item holds: `monitor_id`, `monitor` (display name, itself filtered), `mode`,
`field`, `current_sha256`, `proposed`, `reason`, `risk`, `approver`, and where
known `redactions` (category counts), `alerts_removed`, `detection_cost`,
`evidence`, `needs_review`.

## Proposal format (modes 2 and 3)

A JSON list, one object per change:

```json
[{"monitor_id": 123, "mode": "hygiene", "field": "options.renotify_interval",
  "proposed": 60, "reason": "re-notified every 10 minutes while in alert; 38 of 41 alerts were repeats",
  "risk": "low", "approver": "owning team", "alerts_removed": 38,
  "evidence": "executor row for monitor 123, 30-day window",
  "detection_cost": "none; the first alert still fires at once"}]
```

Add it with `alarmctl.py build --fetched <run>/fetched.json --proposals
<run>/proposals.json --into <run>/changes.json`. `build` rejects a missing key, a
field outside the allow-list, and a change to `query` unless the proposal has
`"allow_query": true`. Text proposed for `message` or `name` is passed through the
same credential filter, so no mode can write a credential into a monitor.

## Allow-listed fields

`name`, `message`, `tags`, `priority`, `options.escalation_message`,
`options.renotify_interval`, `options.evaluation_delay`, `options.require_full_window`,
`options.notify_no_data`, `options.no_data_timeframe`, `options.notify_audit`,
`options.include_tags`, `options.new_group_delay`, and the thresholds
`critical`, `warning`, `critical_recovery`, `warning_recovery`. `query` is allowed
only with the explicit flag, because a query change alters what the monitor
measures.

Never proposed, and refused: deleting a monitor, muting or silencing, resolving,
changing who is notified (handles in the message are left alone by redaction), and
changing a monitor's type.

## What each mode may propose

- **Redact:** removals only, produced by `plan-redact`. At `team` level. Handles
  that start with an at-sign stay, since they route pages.
- **Normalize:** a monitor's message or name rewritten to be shorter and clearer.
  Keep every fact, threshold, link, handle, and template variable; drop only
  clutter. Never alter a number, and never remove a notification handle. If a
  rewrite would change meaning, do not propose it.
- **Hygiene:** settings that reduce noise or add missing guardrails, each tied to
  a measurement or a definition flag, with the alerts it should remove and what
  detection it could cost. A change that could hide a real outage is `high` risk
  and says what protects against that.

Risk labels: `low` when the change cannot hide a real failure, `medium` when it
could delay one, `high` when it could miss one or changes what is measured.

## The approval file

```json
{"plan_id": "<id printed on the report>", "approve_all": true, "exclude": ["c004"]}
{"plan_id": "<id printed on the report>", "approved_ids": ["c001", "c002"]}
```

`apply` refuses an approval whose plan ID differs from the plan, a plan that was
edited after it was built, and approved IDs the plan does not have.

## Apply results

Per item: `would_apply` (dry run), `applied`, `drifted` (the field changed since
the plan; skipped), `verify_failed` (written but the read-back differs; report it
and do not retry blindly), or `error` (with the HTTP status; the body is never
shown). Exit status 4 means at least one error or verify failure. A rate limit
stops the run and leaves later monitors untouched.
