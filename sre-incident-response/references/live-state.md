# Synthesis, mitigation, state and comms

Read this at steps 3 to 5 of "Live incident", after every investigator returns, after the
human reports a check, and whenever a status update is due.
The rules, "The incident log" and "Output" stay in `SKILL.md`; the placeholders are the
same ones. Do not restate them here.

### 3. Synthesize the evidence

Each investigator speaks for its own source, so no one sees the whole picture
unless you build it. After every skill returns, after the human reports a check
they ran, and at close, rewrite the `## Synthesis` section of the log (in place,
with the file edit tool; get the time from `incident_log.py now`). It is the
combined evidence on one screen:

```
## Synthesis
Updated: <UTC time>, after <what just returned>
| Source | Finding | Confidence | Does not cover |
|---|---|---|---|
| <skill or tool, with its saved answer's link> | <one line, as the source stated it> | high | medium | low | not stated | n/a | <what it could not see> |
Combined reading: <the cause the sources support and at what confidence> | no cause established | sources conflict: <how>
Open: <what no source has answered yet>
Next evidence needed: <one item: what, from whom (a role), and which hypotheses it separates> | none
```

- **One row per source,** in the source's own words trimmed to a line, with its
  confidence and, always, what it does not cover (a current snapshot, a sample
  that missed the alert window, a metric with no hostname). Evidence from a source
  that has no investigator (an edge or CDN console, a database console, a number
  the human reads out) gets its own row with its own limits. Gather it as its own
  read-only step. Never hand it to an investigator to fold into its answer: that
  answer would then claim evidence from a source it never examined.
- **The combined reading never outranks the sources** (rule 4). Name a cause only if
  an investigator reached medium or high confidence in it, and at the confidence of
  the weakest source the claim rests on. When two independent sources point the
  same way, write "corroborated by <A> and <B>" and keep each one's confidence:
  only an investigator raises a confidence.
- **A conflict is a finding, not a choice.** When one source says capacity is
  healthy and another shows errors at the edge, write both, note whether they
  measure the same population and window, and do not pick. The conflict drives the
  next-evidence line.
- **Next evidence needed is one item,** the check that would best separate the
  leading hypotheses or close the biggest gap, with who can get it (a role, such as
  the owner of that system) and whether you can run it read-only yourself. If no
  available tool can reach it, write "no available tool reaches it" and log a
  `note`: that is an observability gap, and the postmortem turns it into an action
  item. Write "none" when nothing is outstanding.

Then set the state block's leading hypothesis from the combined reading, and
refresh the options.

### 4. Mitigation

Mitigation does not wait for the root cause. Offer first-aid options at open from
what is already known (the symptom, a recent change the user mentions), keep them
current while an investigation runs, and refresh them each time a skill returns.
When the evidence supports a safe step, offer it as a numbered option:

```
Option <n>: <the step>
Run by: <role>
Reversible: yes | no | partly (<what cannot be undone>)
Expected effect: <what should change, and the metric that shows it>
Risk: <what could get worse>
```

Prefer reversible steps (roll back the last release, scale up, disable a flag,
fail over). Say plainly when an option is not reversible, and put it last. Turn
every step an investigator recommends (its next steps or narrowest fix) into an
Option block, carrying over the role and reversibility it stated, and write
`unknown` for either one it left out. Never present a step that is not
reversible, or whose reversibility is unknown, as safe to try now. When the human
says a step was taken, log a `decision` entry and then an `action` entry with source
`reported` and `--at` the time they give.

Log `mitigated` only on evidence of recovery: a check you ran (a narrow re-check
through an investigator, or a metric the user reads out) or the
human's explicit confirmation, which you log with source `reported`. A step having
been taken is not recovery.

### 5. Keep the state and the comms

After every step, rewrite the state block at the top of the log (impact, severity,
leading hypothesis, actions taken, owner role, next update due). Anyone opening the
file mid-incident should be able to read it in ten seconds, so each field is one
short line (about 200 characters at most; `check` warns above that). Impact says
who is affected, how badly, since when. The leading hypothesis is the cause in one
line with its confidence. Actions taken lists only response actions, not housekeeping.
The detail belongs in the timeline and the saved answers. Edit only the state
block (from `## State` to the next heading) and the synthesis, with the file edit
tool, and never the timeline. Take the next-update-due time from
`incident_log.py now --plus {{UPDATE_INTERVAL_MINUTES}}`, not from your own
arithmetic.

A status update is due at open, when a cause is identified, when mitigation is in
place, when resolved, and every `{{UPDATE_INTERVAL_MINUTES}}` minutes while the
incident is `open`. A SEV4 watch needs one only when something changes or the
commander asks. When one is due, draft it from `references/comms-templates.md`
and log a `comms` entry saying a draft was prepared. If the next one is overdue,
say so at the top of your reply.
