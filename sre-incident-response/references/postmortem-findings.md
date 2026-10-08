# Postmortem findings

Read this at step 5 of the postmortem. It says what the draft contains, how to
write action items, and how to check the wording. The page layout, title, and file
name belong to the report skill's `postmortem` profile; this file is the content.

## Contents

- Content, in order
- Action items
- Blameless wording checks
- Before you hand the draft over

## Content, in order

1. **Summary.** Two or three sentences: what broke, who felt it, for how long, how
   it ended. A reader who stops here should have the story.
2. **Impact.** Who and what was affected, how badly, and since when, with the
   numbers the log or the investigators recorded. Duration figures from logged UTC
   times only; "not recorded" otherwise.
3. **Timeline.** The log's entries in UTC order, trimmed to the events that carry
   the story. Keep each entry's tag and its source (observed, reported, or the
   skill that produced it). Do not add an entry the log lacks.
4. **Root cause.** The investigator's final root cause as written: trigger,
   mechanism, why it crossed the alert threshold, recovery, then ruled out, still
   open, contributing factors, and confidence. Cite the saved answer it came
   from by file name. When it has fewer links (a triage has no alert threshold), keep the links it gave and mark each
   missing one "not established". If none was established, say "Root cause not
   established".
5. **Detection.** How the incident was noticed (which monitor or who), and how long
   after impact started (time to detect: `impact-start` to `alerted`). Then how
   long from the alert to the first response (time to engage: `alerted` to
   `engaged`), because a fast alert answered slowly is a different problem from a
   slow alert. When the answer is "a user reported it", say that plainly, because
   it is the most useful sentence in the document.
6. **Response.** What was tried, in order, and what worked. Include options that
   were proposed and not taken, with the reason if the log has one.
7. **What went well, what went badly, where we were lucky.** Short bullets about
   systems, process, and tooling. "Lucky" is anything that limited the damage by
   chance and cannot be relied on next time.
8. **Action items.** See below.
9. **Open questions.** Links in the chain the evidence could not reach, and facts
   nobody has confirmed. Include the log's synthesis "Open" and "Next evidence
   needed" lines when they were still unanswered at close, and any "Does not cover"
   limit that left a source blind to the incident window.
10. **Linked reports.** The file names of the saved investigator answers (one
    per investigator that ran) and of the incident log.

## Action items

Every item has these fields:

| Field | Rule |
|---|---|
| Type | `detect` (notice it sooner), `mitigate` (stop the damage sooner), or `prevent` (stop it happening) |
| Action | One concrete, checkable change. "Add an alert on X above Y" is an action; "improve monitoring" is not |
| Why | The specific finding from this incident it answers |
| Priority | Proposed: `now`, `soon`, or `later`, with a one-line reason |
| Owner | Always "unassigned": the team assigns owners in review. This skill does not pick a person |
| Due | Left blank for the team to set |

Derive items from the evidence, not from a generic checklist:

- An `alerted` entry much later than `impact-start`, or no alert at all because a
  user reported it, gives a `detect` item.
- An `engaged` entry much later than `alerted` gives a `mitigate` item (the response
  started slowly: routing, paging, or ownership).
- A slow or risky mitigation, or one that needed a person to know a hidden step,
  gives a `mitigate` item.
- Each contributing factor in the final root cause gives a `prevent` item or an
  explicit note on why none is proposed.
- A "still open" or "not established" link gives an investigation item.
- A synthesis "Next evidence needed" marked "no available tool reaches it" gives a
  `detect` item: the observability gap that kept the cause from being established
  (for example, a missing log source or a breakdown the monitor does not carry).

Do not propose more than about eight; rank them so the first three are the ones to
do.

## Blameless wording checks

Before you hand the draft over, scan it for these and rewrite:

- A person's name, or a pronoun for one. Use a role: the on-call engineer, the
  deploying team.
- "Failed to", "forgot", "should have", "mistake", "negligent". Describe what the
  person knew and what the system allowed instead ("the deploy proceeded because no
  check compared error rates before promotion").
- "Human error" as a root cause. It is never a root cause; ask what made the error
  easy to make and hard to catch.
- A cause stated more strongly than the investigator's confidence.
- A duration or number with no logged source.

## Before you hand the draft over

- Every time in the timeline is UTC and exists in the log.
- The root cause matches the investigator's wording and confidence.
- No secret, token, connection string, customer data, or personal data appears.
- Every action item has a type, a reason tied to a finding, and an unassigned owner.
- Anything unverified is listed under open questions, and the same list goes in the
  chat reply as "Needs review".
