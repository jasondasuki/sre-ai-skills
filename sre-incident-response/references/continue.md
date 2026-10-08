# Continue mode

The procedure for picking up an incident that already has a log. Read it at step 1
"Continue" of "Live incident". Steps 2 to 6 of that section then apply unchanged.

Pick up an incident that already has a log, in this session or a new one. The log
and the incident folder are the whole memory; do not rely on what you remember
from an earlier conversation.

1. **Find the log.** Use the path the user gave (the log or its incident folder).
   Otherwise run `python3 {{CORE_DIR}}/scripts/incident_log.py list {{LOG_DIR}} --active`.
   One incident: use it and say which. Several: list them and ask. None: say so in
   one line and offer New; if the user means one that is already closed, go to
   the reopen rule in step 3.
2. **Reload it.** Run `check` (fix an ordering error with `sort`) and `durations`.
   Read the whole log: state, synthesis, timeline. Read the saved answers the
   timeline links (in the incident folder) and the latest `coordinator` file. If the
   state block and the timeline disagree (a `resolved` entry with Status still
   `open`), say so and go by the timeline.
3. **Reopen only on a reason.** If the log's Status is `closed` and the user says
   impact is back or the alert re-fired, log a `note`
   (source `reported`, with the time they give) saying why it is reopened, set
   Status to `open`, and re-propose the severity (rule 3). It stays one incident
   with one log unless the commander says it is a different one. If the user only
   wants the write-up of a closed incident, that is Postmortem, not Continue.
4. **Mark the gap.** Log one `note` (source `observed`) saying the incident was
   continued, with the Status and the time of the last entry; it makes a break in
   the timeline visible instead of looking like inactivity. Get the gap from
   `incident_log.py now`. If the next update was due while no one was working it,
   say so at the top of your reply.
5. **Log what happened meanwhile.** If the incident has a thread
   (`watch.json`) and `{{SLACK_READ_TOOLS}}` is not `none`, read the thread first and
   log each reply from anyone else that the log does not hold yet (source
   `reported`, `--at` the reply's time in UTC; "Acting on what changed" in
   `references/slack-watch.md` has the rules), then say in the reply how many you
   found. Then ask once, in one line, what changed since the last entry that the
   thread does not show (a step taken, a recovery, new impact, a message sent). Log
   each thing with source `reported` and the time the user gives, using `--at`; if
   they give no time, log it now and say that the event time is unknown. Never
   backfill a time you guessed (rule 2). Those thread replies are folded into the
   next result file as well (step 6).
6. **Do not repeat finished analysis.** An investigator's saved answer stands until
   the evidence it used has changed. Re-run an investigator only when the user asks
   or when the world has moved (the alert is still firing, a mitigation was
   applied, new impact), and say why in one line; the new answer is saved as a
   repeat (`-2`). Otherwise start from the synthesis's "Next evidence needed" line.
   Before any investigator re-runs, pass "The gate" in `references/slack-watch.md`.
   With no active watch there is no later check to retry it, so if the gate is
   blocked, tell the commander which members' agents are running and offer "go
   ahead" (run now) or "ask me again".
7. **Re-arm the watch.** If the incident folder has a `watch.json` that is still
   active but no scheduled job exists in this session (a new session), schedule the
   check again as in `references/slack-watch.md` and record the new job id with
   `watch <log> update --cron-id <id>`. If there is no `watch.json`, do not start
   one unless the commander asks.
8. **Bring the state up to date,** then reply in the live shape (see "Output")
   with the state block, the options as they stand, and a status update if one is
   due. Then continue with steps 2 to 6: route any new analysis, keep the
   synthesis, options, state and comms current, and close when the human says so.
