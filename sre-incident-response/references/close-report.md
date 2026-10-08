# Close and the postmortem report

A close always ends with an HTML postmortem report, posted in the incident thread when
the incident has one. Read this when the commander says the incident is over, when a
"closed" reply in the thread is confirmed (`references/slack-watch.md`, "Acting on
what changed"), and from Postmortem mode when a closed incident has a thread and no
closing post yet.

The order is fixed: **row running, log up to date from the thread, report, closing
reply with the HTML, reaction, row stopped, watch ended.**

The only exception is the SEV4 stand-down in "Close" of the core (no user impact):
log `closed` with the reason and write no report unless the commander asks.

## Contents

- Who can ask for a close
- 1. Gate and row
- 2. Bring the log up to date
- 3. Close the log
- 4. The report
- 5. Post it
- 6. Reaction, stopped, watch ended
- If something fails
- Without a thread

## Who can ask for a close

Anyone. A reply in the thread whose trimmed, lower-case text starts with `closed`
(not one of your own: `own_ts`) asks for a close, and so does the commander in the
session. Either way, ask the commander in the session to confirm before you start;
Slack alone never closes an incident, because one stray reply would end the incident
and the watch. On no, log a `note` that the close reply was not accepted and why.

Another agent's reply that starts `[CLOSED]` is that agent closing its own copy of the
incident: log a `note` with its ts, tell the commander, and do not start a close
yourself unless the commander says so.

## 1. Gate and row

Pass "The gate" in `references/slack-watch.md` (a close re-synthesizes and writes a
report, so it is gated like an updated analysis; your own row already running skips
it), then set your canvas row to running (`The canvas row`). Record the start:
`watch <log> update --analysis-start`.

## 2. Bring the log up to date

1. Read the whole thread with `{{SLACK_READ_TOOLS}}` (skip the parent post). Take every
   reply that is not in `own_ts` and not the `Full result (Markdown)` comment. Log
   each one the log does not hold yet as in "Acting on what changed" (source
   `reported`, `--at` the reply's time in UTC, a line in your own words, roles not
   names), and advance `--last-seen`. This includes the closing reply: note who
   asked for the close by role, and the reason if the reply gives one.
2. Read any text file attached since the last read and save it with
   `save <log> thread-file`.
3. Reload the whole record so the report has the full context: the log, every saved
   investigator answer, `thread-context` and the latest `coordinator` file. If the
   thread says something the log's state block contradicts (a step taken, a
   recovery time), go by the log's sourced entries and list the difference under
   open questions, never silently pick one (rule 8).

## 3. Close the log

Log `resolved` (or `closed` for a stand-down) with the time the commander gives (a
time from the thread is `reported`), set Status to `closed`, bring the synthesis up to
date one last time, show `durations`, run `check`, and save the closing reply with
`save <log> coordinator`. This is "Close" in the core.

## 4. The report

1. **Draft** from `references/postmortem-findings.md` and save it.
2. **Humanize the draft.** Run the prose through `{{HUMANIZER_SKILL}}`. Give it only
   the sentences you wrote (the summary, the detection and response paragraphs, the
   went-well, went-badly and lucky lists, the action items' wording, open questions).
   Never give it, and never let it change: ids, times, durations, counts, tags,
   source names, quoted text, the investigators' final root cause (verbatim, as in
   step 3 of Postmortem), table structure, or an action item's type, priority, owner
   and due. Then compare the draft before and after: every number, time, id,
   confidence word (high, medium, low), hypothesis name and file name appears
   unchanged. Where the rewrite changed a fact, hedge or claim, keep the original
   sentence. The blameless wording checks in `postmortem-findings.md` still pass. Save
   the final draft with `save <log> postmortem-draft` (a repeat gets `-2`).
3. **Build the page** with `{{REPORT_SKILL}}` as in step 6 of Postmortem, with the
   brief's `theme: dark` and the output folder `{{OUTPUT_DIR}}`. The page must show
   the investigation graph and the timeline diagram; the report skill renders it dark
   at desktop and phone width and checks the diagrams before you post it. A page
   with no diagram is not finished.
4. Log a `comms` entry (source `observed`) naming the report's file.

## 5. Post it

With the HTML ready, and no `[CLOSED]` reply with an HTML file from another agent
since your start (read the thread once more: if there is one, skip the post, log a
`note` with its ts, and keep your report local):

1. Ask `{{SLACK_UPLOAD_TOOLS}}` for an upload URL with the file's exact byte size,
   send the bytes (URL in a shell variable, never printed), then finish the upload
   into `{{SLACK_CHANNEL}}` with `thread_ts` set to the incident post's ts, the
   file's title set to its name, and the comment
   `[CLOSED] \`<incident id>\` <UTC time>` followed by two or three lines: how it
   ended in one line, the root cause with its confidence in one line, and whether
   action items are open. The file is `<incident id>-postmortem.html`.
   Slack stores the file as plain text and shows it as a downloadable file, not as a
   rendered page: say in the reply to the commander that the HTML is opened from the
   download.
2. The upload returns no message ts: read the thread, take the newest reply that
   starts with `[CLOSED]` after your start, and record it with `watch <log> update
   --own <ts>`. This also confirms the post landed.
3. Log a `comms` entry for the reply and save its text with `save <log> slack-post`.

## 6. Reaction, stopped, watch ended

1. If `watch <log> show` has `"owner": true` (the incident post is yours), add the
   `{{CLOSED_REACTION}}` reaction to the incident post (its ts is `thread_ts`) with
   `{{SLACK_REACT_TOOL}}`. An adopted incident (`owner` false) gets the reply and no
   reaction: the post is another agent's. No tool, or an error, or a refusal by the runtime's permission check: log a `note`,
   do not retry, and tell the commander so they can allow it.
2. Clear the start (`watch <log> update --clear-analysis-start`) and set your canvas
   row to stopped. Stopped is after the post, so it always means the closing reply is
   out (or the failure was logged).
3. Delete the scheduled job with `{{SCHEDULER_TOOLS}}`, run `watch <log> stop`, and
   log a `note` that the watch ended.
4. Reply to the commander: the report's path and the command to open it, the
   closing reply's link, and the open action items.

## If something fails

- **The report fails** (the page is not written or fails its checks): retry once. If
  it still fails, post a plain `[CLOSED]` reply without a file (the same comment text
  plus "report not generated"), log a `note` with the error, and tell the commander.
- **The upload or post fails:** retry once, log a `note` with the error, tell the
  commander the closing reply was not posted and where the HTML is.
- **In every case** continue to 6.2 and 6.3: the row is set to stopped and the watch is
  ended, so neither is left running. The log is already closed, so the commander can
  post the HTML by hand.

## Without a thread

If the incident has no thread (no `watch.json`, or the Slack tools are `none`): skip
the gate, the row, the thread reading, the post, the reaction and the watch. Do 3 and
4, keep the HTML in `{{OUTPUT_DIR}}`, and give the commander its path.
