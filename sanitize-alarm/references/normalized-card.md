# Normalized alarm card

One card per alarm. Fill each field from the input only; write `unknown` when
the input does not say. Never invent, round, or "correct" a value.

```
ALARM CARD
Source:        <monitor | event | incident | log alert | synthetic | other>
Name:          <monitor or alert name>
ID:            <monitor / event / incident id, or unknown>
State:         <alert | warn | recovered | no data | other>, since <timestamp with timezone>
Priority:      <as given, or unknown>
Type:          <metric | log | APM | synthetic | composite | anomaly | other>
Condition:     <the query or rule, and the threshold, exactly as given>
Observed:      <the value that triggered it, with its unit and window>
Scope:         <the tags or groups it fired for>
Impact hint:   <what the alarm itself says is affected, or unknown>
Message:       <the human text, cleaned (below)>
Runbook:       <link or unknown>
Owner:         <team or tag, or unknown>
Related:       <linked monitors, incidents, deploys, changes mentioned>
Links:         <one line per useful link>
```

## Cleanup rules

- **Unresolved template tags.** Tags like a hostname or value variable left raw
  in a message were never filled in. Drop them, and note `template tags
  unresolved` once if that is itself useful to the reader.
- **Conditional blocks.** A message often holds a block per state (alert,
  warning, recovery, no data). Keep only the block for the current state and say
  which one you kept.
- **Notification handles.** Remove who was paged or mailed from the message and
  put the routing, if it matters, in `Owner`.
- **Duplicated sections.** Merge repeated headers, repeated links, and the same
  snapshot image reference to one.
- **Markup.** Convert markup to plain text; keep a table or list when it carries
  values.
- **Keep what changes the response**: the threshold, the observed value, the
  scope, the time, what changed recently, and any instruction in the runbook.
- **Do not interpret.** The card records what the alarm says. Diagnosing it is a
  different job (the investigation skill's), so do not add a cause.
