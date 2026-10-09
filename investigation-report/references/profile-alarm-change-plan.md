# Profile: alarm-change-plan

Format a proposed set of monitor changes as one self-contained HTML page that a
person reads before approving anything. The producer owns the plan, the
evidence, and the apply step; this profile owns how the plan looks. Read it when
the brief names `alarm-change-plan`; follow the shared core for escaping, page
style, destination selection, and verification.

The page is a decision aid, not a record of work done. Every line on it is
**proposed**, and the page says so at the top and again at the approval section.

## Title and file name

**Report title:**

```
YYYY-MM-DD HH:MM UTC - Alarm change plan: <scope>
```

Use the plan's creation time in UTC and a readable scope label (the tag or query
the runner gave). Use exactly the same string for `<title>` and `<h1>`.

**Filename:** `YYYY-MM-DD-HHMM-alarm-change-plan-<scope-slug>.html`, same time as
the title, scope slug in kebab case. Write in the caller's folder. Never
overwrite; append `-2`, `-3` if the name exists. A re-planned set gets a new
file and a new plan ID, because an approval belongs to one plan ID only.

## What the brief must carry

The producer's plan file and summary (plan ID, scope, modes, items with ID,
monitor ID and name, mode, field, proposed value, reason, risk, approver, alerts
removed, redaction counts, review flags), the review notes, any history
measurements behind hygiene items, the monitors left out and why, and the
producer, models, and time facts for the footer. The plan file holds **proposed
text and redaction counts only**; the original values are not in it and must not
be anywhere on the page.

## Sections, in order

1. **Header:** title, scope, modes chosen, plan ID in a copyable code element,
   creation and generation times in UTC, and a status badge reading
   `Awaiting approval - nothing has been changed` (icon plus text).
2. **What you need to decide:** three to five lines: how many monitors would
   change, how many changes, how many need a person's eye, the single riskiest
   change, and the exact reply that approves (see section 8).
3. **How this runs:** a flow diagram of the stages (scope, plan, this report,
   approval, apply with drift check, verify), with the current stage marked.
4. **At a glance:** the charts below, each with a one-line takeaway above it.
5. **Change list:** the full list, grouped by monitor, every item visible. One
   row per item: item ID, monitor ID and name, mode, field, the proposed change,
   reason, risk label, who must approve, and alerts removed when known. For a
   text field show the proposed text in a `details` block with placeholders
   highlighted; for a number or setting show `now -> proposed` using only the
   values the plan carries. Never show the text that a redaction removed.
6. **Needs a person:** items flagged for review and the review notes (long
   tokens left in place, text a script could not judge), each with the monitor
   and field.
7. **Left out and not changing:** monitors in scope with nothing to change,
   monitors skipped and why, and the fields this tool never touches (no
   deletions, mutes, resolves, or notification-list changes).
8. **Approval and safety:** the plan ID again; how to approve all, a subset, or
   all but some (give a copyable example of each using real item IDs); the
   guarantees (only approved items; a monitor edited by someone since the plan
   is skipped, not overwritten; each write is read back and verified; prior
   values for non-credential fields are kept for rollback; a changed plan needs a
   fresh approval); and the sentence that nothing happens until the runner replies.
9. **Evidence and provenance:** when and how the monitors were read (scope
   query, count), the history window for hygiene items, tool test status, and a
   footer naming the producer, the planner model that ran, executors if any,
   and generation time in UTC.

Keep every section, even when its content is "none". A short statement that
nothing was found is evidence too.

## Visuals

Load the chart skill before drawing any chart and the page-design skill before
the page. Each chart has a text label and a table or number beside it, so the
page reads without colour vision.

- **Flow diagram (section 3):** inline SVG, six boxes joined by arrows, the
  approval box drawn as a gate and marked as the stop point. Follow the
  diagramming guidance of the selected page-design skill.
- **Changes by mode and field:** horizontal bars, one per field name, grouped or
  coloured by mode, count labelled on each bar.
- **Redaction categories** (when the redact mode ran): horizontal bars of the
  summary's category counts. Categories are labels only, never values.
- **Noise before and after** (when the hygiene mode ran): one bar per monitor of
  alert transitions in the window, with a marked line at the noisy threshold,
  and beside each the alerts the change would remove. Draw only measured values;
  a monitor with no measurement is listed as "not measured", never as zero.
- **Risk mix:** a single stacked bar or three tiles for low, medium, high, with
  the counts.

Do not draw a trend or curve the plan does not carry points for.

## Checks after writing

In addition to the shared checks: the plan ID on the page equals the brief's; the
item count on the page equals the plan's; every item ID in the plan appears once
in section 5; the approval examples use item IDs that exist; and the page holds
no credential-shaped string and no email address anywhere (scan for them, and
fail the report if one is found), because the page is a file that outlives the
conversation.
