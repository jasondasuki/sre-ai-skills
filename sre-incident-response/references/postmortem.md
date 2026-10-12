# Postmortem (closed incident)

Read this in Postmortem mode: the incident's Status is closed and the user wants the
write-up or review.
The rules, "The incident log" and "Output" stay in `SKILL.md`; the placeholders are the
same ones. Do not restate them here.

## Postmortem

This mode is for an incident that is over: Status `closed`. It
reads the log and writes; it opens no new log and changes nothing in the timeline.

1. **Find the log.** Use the path the user gave (the log, or its incident folder);
   otherwise run `python3 {{CORE_DIR}}/scripts/incident_log.py list {{LOG_DIR}}` and
   take the most recent `closed` incident (folder names start with the
   UTC date and time, so the newest sorts last), and the `<id>.md` log inside it.
   Then check its Status:
   - `closed`, and the timeline has a `resolved` entry: go on.
   - `open`: the incident is not over. Say so in one line and offer Continue, so it
     is closed first. Write a postmortem now only if the commander says to, label
     the draft and the report "written while the incident was open", and treat the
     missing resolution as "not recorded".
   - `closed` with a `closed` entry and no `resolved` entry (closed without a recorded
     recovery or a confirmed cause, per "Close"): go on and write it, unasked. Say in
     the first line how it ended (for example no user impact, the alert did not clear,
     the cause was not established), and write it from the log as it stands, with the
     unknowns shown as unknown (rule 8).
   - An old log with the status `resolved`, `mitigated` or `monitoring` reads as
     `closed`, `open` and `open`.

   A log from before incident folders existed sits directly in `{{LOG_DIR}}` as
   `<id>.md`, with its saved answers in a folder named `<id>`; use it the same way.
   If it is ambiguous, list the candidates and ask. With no log at all, ask for the
   facts (start, detection, mitigation, resolution, impact, what was done) and say
   in the report that the timeline is reconstructed from the user's account. Run
   `check` on the log. If it reports the timeline out of order, run `sort`. A log
   written before `alerted` and `engaged` existed uses `detected` for both; see
   step 4.
2. **Read everything the log points to.** Every saved investigator answer it links
   (in the incident folder, beside the log), in full. The root cause comes from there. Also read the log's synthesis:
   its table shows what each source could and could not see, and its "Open" and
   "Next evidence needed" lines are open questions for the postmortem. Its combined
   reading never replaces the investigator's final root cause (step 3).
3. **Reuse the root cause.** Take the investigator's final root cause as written:
   trigger, mechanism, why it crossed the alert threshold, recovery, then ruled
   out, still open, contributing factors, and confidence. Do not regenerate or
   strengthen it. A final root cause from a different kind of investigator can have fewer
   links than a telemetry investigation's (a cluster triage has no alert threshold,
   and often no ruled-out list): use the links it gives and write "not established"
   for each one it lacks, never a filled-in guess. If no investigator ran, write "Root cause not established" and give the
   leading hypothesis labelled as such.
4. **Compute only what was logged.** Run `durations` and use its output as it
   stands: time to detect (impact start to alert), to engage (alert to first
   response), to mitigate, and to resolve come from logged UTC entries. A duration
   with a missing endpoint is "not recorded", not an estimate. In an old log that
   has `detected` entries and no `alerted`, take the entry that came from the
   monitor's own transition as the alert, say which one under "Needs review", and
   work that one duration out from the logged times.
5. **Draft from `references/postmortem-findings.md`.** It lists the content, the
   action-item rules, and the blameless wording checks. Save the draft in the
   incident folder with `save <log> postmortem-draft`, so the findings stay readable
   as Markdown beside the evidence. Before saving, run the prose through
   `{{HUMANIZER_SKILL}}` (see `references/close-report.md`, "Humanize the draft").
6. **Write the report** with `{{REPORT_SKILL}}`: load it with the skill tool, or
   read its handler file if skill loading is unavailable. It owns the page, the
   title and file name rules, the escaping and secrets rules, and the checks after
   writing, so none of that is repeated here. Give it this brief:
   - **profile:** `postmortem`.
   - **theme:** `dark`. The page must show the investigation graph and the timeline
     diagram.
   - **output folder:** `{{OUTPUT_DIR}}`. This skill's reports go there and nowhere
     else.
   - **time and title facts:** the incident start in UTC (the `impact-start` entry,
     else the `alerted` entry, else the `engaged` entry), the severity, the
     affected system, and the impact in a few words.
   - **producer facts:** this skill's name, the mode, the model that actually ran
     (`{{MODEL}}`, or the real one if it differs), the log path, and the file names of
     the saved answers it drew on.
   - **findings:** the full draft from step 5. The page is the same findings in a
     better container, so add nothing the draft does not say.
7. **Post it when the incident has a thread.** If the folder has a `watch.json` and
   no closing post yet, do the Slack steps of `references/close-report.md` (row
   running first, the closing reply with the HTML, the reaction, row stopped, the
   watch ended). Otherwise the report stays local.
8. **Save your reply.** Put the postmortem reply you are about to give (see
   "Output") in the incident folder with `save <log> coordinator` (the closing
   reply from the live run is already there, so this one gets `-2`).
