# Link parsing

Read this at the start of every run that begins with a Datadog link. It maps each
URL shape to the MCP call that resolves it and lists the parameters to carry
forward.

## Link parsing

| URL pattern | What it is | Resolve with |
|---|---|---|
| `/monitors/<id>` or `/monitors/<id>/status`, `/monitors#<id>` | Monitor | `search_datadog_monitors` by id (read query, threshold, message, state, group) |
| `/monitors/<id>?group=<k:v>` or `?q=<group>` | Monitor, one alerting group | same, then scope every query to that group's tags |
| `/event/event?id=<n>`, `/event/explorer?...`, `/event/...` | Alert/event notification | `search_datadog_events` for the event; it names the monitor and group |
| `/incidents/<id>` | Incident | `get_datadog_incident` with timeline |
| `/apm/trace/<trace_id>`, `/apm/traces?query=...` | Trace / trace search | `get_datadog_trace` / `search_datadog_spans` |
| `/logs?query=...`, `/logs/...` | Log search | `search_datadog_logs` with that query |
| `/dashboard/<id>?...`, `/notebook/<id>` | Dashboard / notebook | `get_datadog_dashboard` / `get_datadog_notebook` for the queries; use its `tpl_var_*` values as filters |
| `/synthetics/details/<id>` | Synthetic test | monitor/events for that test; failing location and step |
| `/rum/...`, `/error-tracking/...`, `/services/<svc>` | RUM / error / service view | RUM tools, error-tracking skill, entity search |
| Anything else on Datadog | Unknown | extract any `query=`, `from_ts`, `to_ts`, `tpl_var_*`, ids, and use them as filters |

Extract and carry forward every parameter that narrows the problem:

- **Time:** `from_ts`, `to_ts`, `eval_ts`/`event_ts`/`evaluation_ts` are epoch
  **milliseconds** (convert to UTC and state it). The window in the link is the
  incident window; use it as `T0` context before falling back to "now". A
  missing time means the alert is current: use the monitor's last transition.
- **Scope:** `group=`, `q=`, `query=`, `tpl_var_<tag>=<value>` become tag
  filters (`env`, `service`, `host`, `kube_namespace`, `region`).
- **IDs:** monitor, event, incident, trace.
- If the link is a notification link carrying an `event` plus a group, the
  alerting group (for example `host:abc`) is the scope; do not widen to the
  whole monitor until that group is understood.
- A notification event can be a **recovery** or a warning rather than the alert
  itself. Read the event's title and state, and use the monitor's own transition
  times, not only the event's timestamp, to find `T0`.
