# Open a new incident

Read this at step 1 "Open (New)" of "Live incident", when the incident has no log yet.
The rules, "The incident log" and "Output" stay in `SKILL.md`; the placeholders are the
same ones. Do not restate them here.

### 1. Open (New)

1. Create the log:
   `python3 {{CORE_DIR}}/scripts/incident_log.py open {{LOG_DIR}} <slug> --title "<impact in a few words>"`.
   The slug is short kebab-case for the impact (for example `checkout-errors`).
   The script reads the clock, makes the id `YYYY-MM-DD-HHMM-<slug>`, creates the
   incident folder `{{LOG_DIR}}/<id>/` first and then the log `<id>.md` inside it
   from the template in "The incident log", never overwrites (a taken id gets
   `-2`), and prints the id, the log path and the folder. The folder is the whole
   record of the incident: the log, every investigator's saved answer, and your own
   output all go in it, and nothing about the incident goes anywhere else.
2. Capture what you were given: the alert link, monitor, workload, or the user's own
   description. Log one `engaged` entry (source `observed`) saying the incident
   was opened from it: that is when work began, not when the alert fired. Log
   `alerted` only when a time for the alert firing is known (the user gave one, or
   the alert event carries it), with `--at`; the time a link reached you is never
   the alert time. Log `impact-start` only when the user or the evidence gives a
   start time.
3. **Incident or watch?** Work out from the evidence whether users are affected
   (rule 3, `references/severity.md`). If all you have is an alert and nothing
   says users are affected (a warning-level monitor, one failing replica behind
   healthy capacity), propose SEV4: say in one line that you are treating it as a
   watch, and what would turn it into a higher severity (user impact reported or
   seen, a critical threshold crossed, the alert not clearing). Still route the
   analysis. If impact is stated or evident, propose the severity that fits. The
   Status is `open` either way: a watch is an open incident at SEV4. The commander
   decides.
4. Set the severity in the state block and the next update due to now plus
   `{{UPDATE_INTERVAL_MINUTES}}` minutes.
5. Reply in chat in the live shape (see "Output") with the first state block, the
   first status draft, and any first-aid options the facts at open already
   support (see "Mitigation" in `references/live-state.md`, and `references/comms-templates.md` for the draft), so the commander has them before the analysis
   returns.
