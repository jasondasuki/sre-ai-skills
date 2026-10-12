# Close

Read this at step 6 of "Live incident", when the human says the incident is over. The
Slack and report steps are in `references/close-report.md`.
The rules, "The incident log" and "Output" stay in `SKILL.md`; the placeholders are the
same ones. Do not restate them here.

### 6. Close

When the human says the incident is over (or confirms a "closed" reply in the
thread), read `references/close-report.md` and follow it: it sets your canvas row to
running, brings the log up to date from the thread, logs `resolved` or `closed` and
sets Status to `closed`, writes the postmortem as a dark HTML report with diagrams
(prose through `{{HUMANIZER_SKILL}}`), posts it in the thread as the closing reply,
adds the `{{CLOSED_REACTION}}` reaction when the incident post is yours, sets the row
to stopped and ends the watch. The synthesis is brought up to date one last time (its
"Open" and "Next evidence needed" lines carry into the postmortem), and the final
durations are shown (`durations`, see "The incident log").

**Every close produces the postmortem and the HTML report**, except when another
agent's `[CLOSED]` reply in the thread already carries one: then you download that file
into the incident folder and write nothing (`references/close-report.md`, "When another
agent already closed"). The severity, the lack of
user impact, an alert that never cleared, a cause that was never established, and an
incident that was never resolved are not reasons to skip it: the report is where
what is unknown is written down, and a commander who closes an unclear incident needs
it most. Choose the closing tag by how it ended:

- `resolved`: the incident ended on evidence of recovery.
- `closed`: the commander closed it without a recorded recovery or a confirmed cause
  (a watch that never turned into user impact, an alert that did not clear, a false
  positive, a threshold that was tuned, or an investigation that found nothing more).
  Give the reason in the entry.

Either way the postmortem is written. When it ended with `closed`, the report says so
at the top and shows each unknown as unknown (rule 8): resolution "not recorded", root
cause "not established" or the leading hypothesis labelled as such, impact as far as
the log shows it. If impact turns up later, set Status to `open` and re-propose the
severity (rule 3).

Run `check` on the log before you hand it over; it should report no errors. Then
save your own output, the closing reply you are about to give the commander (the
live shape in "Output", with the final state, the synthesis and the durations), in
the incident folder with `save <log> coordinator <<'EOF' ... EOF`. It is your
original output, kept beside the evidence it was built from, so the folder can be
read, handed over, or continued by someone else without this conversation.
