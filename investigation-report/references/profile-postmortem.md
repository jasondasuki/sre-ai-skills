# Profile: postmortem

The report format for a resolved incident: what happened, in what order, why, and what
changes. Read this when the brief names this profile (Step 3 of the core). The
shared page rules, hard rules, and verification are in the core; this file holds
what is specific to this format.

## Contents

- Title and file name
- Visual language
- Sections, in order
- Investigation graph
- Timeline drawing
- What the page must not do

## Title and file name

**Report title (required):**

```
YYYY-MM-DD HH:MM UTC - <SEV> <system>: <impact>
```

- **Date and time** are when the impact started, in UTC; when only detection is
  known, the detection time. Always say `UTC`. The time the report was generated goes
  in the header and footer, not the title.
- **SEV** is the severity as the brief gives it (for example `SEV2`). **System** is
  the affected service or feature, and **impact** is a few plain words ("checkout
  errors for all users", "login latency over 10 s"). Keep the title under about 110
  characters, trimming the middle rather than the ends.
- Use this exact string in the `<title>` element and the page `<h1>`. It is a
  deliberate exception to any short-title guidance in `{{PAGE_DESIGN_SKILL}}`.

**Filename:** `YYYY-MM-DD-HHMM-<sev>-<system>-<impact-slug>.html`, using the same date
and time as the title (UTC) and short kebab-case slugs, for example
`2026-10-05-1432-sev2-checkout-errors-all-users.html`. Never overwrite an existing
report; if the name exists, append `-2`.

## Visual language

This profile lays the page out like an observability investigation workspace (the
kind where an AI investigator shows a conclusion first, then the hypotheses it
validated and ruled out), because that is how on-call engineers already read an
incident. It replaces the core's warm "Page style" palette for this profile only;
every hard rule, the dark-mode requirement, and the escaping rules still apply.
Do not use any vendor's name, logo, or brand mark on the page.

Start from `references/postmortem-layout-example.html`: copy its tokens, CSS,
icon sprite, and small script, and replace its synthetic content with the brief's
findings. It is a layout reference, never a source of facts, so delete its sample
banner and leave no sample value behind.

- **Frame:** a sticky top bar (incident id, SEV chip, `Draft - awaiting review`
  chip, an expand-all button), a sticky outline rail of section links on wide
  screens (hidden on phones), and one main column of cards. Cards are white or
  dark-surface panels with a 1px border and a header row (icon, title, hint).
- **Palette:** cool neutral ground, one violet brand accent for the conclusion and
  analysis, and fixed status colours: green validated, grey ruled out, amber still
  open, blue contributing, red impact. Define them as tokens on `:root` with
  dark-mode variants.
- **Status is never colour alone:** each status chip and node carries an icon and a
  text label (check, cross, question mark, layers, alert).
- **Interaction:** native `details`/`summary` for nodes. The only script is the
  expand-all toggle and the rail highlight; it never writes brief text into the
  page.

## Sections, in order

1. **Header:** the sticky top bar plus the `<h1>`, which is the report title.
   Beneath it: the incident id, the impact window, and the time the report was
   generated. The status chip reads `Draft - awaiting review` on every postmortem
   this skill writes, because the team reviews it before it is final.
2. **Conclusion card:** the answer card, with a violet left edge. A status chip
   (`Root cause identified` for high or medium confidence, `Root cause not
   established` otherwise), a three-segment confidence meter with its word, then
   the summary: two or three sentences on what broke, who felt it, for how long,
   how it ended. Beneath it, three fact tiles: trigger, mechanism, recovery, each
   one line from the brief's root cause (write `not established` for a link the
   brief lacks).
3. **Impact at a glance:** stat tiles, each with an icon, for time to detect, time
   to mitigate, and time to resolve, plus the impact figures the brief carries. A
   value with no logged source shows `not recorded` in muted text, never an
   estimate.
4. **Investigation graph:** the final root cause drawn as a tree, as the brief gives
   it. See "Investigation graph" below. It carries the root cause, so there is no
   separate prose copy of it.
5. **Timeline:** a swim-lane drawing and an event stream, both from the logged
   entries. See "Timeline drawing" below. It follows the graph in the page, because
   a reader should see the cause before the sequence.
6. **Detection and response:** two panels. Detection: how it was noticed and how long
   after impact began. Response: what was tried, in order; what worked; options
   proposed and not taken.
7. **What went well, what went badly, where we were lucky:** three short lists, as
   three side-by-side panels, each headed by an icon and its label.
8. **Action items:** a table with the columns type (`detect`, `mitigate`, `prevent`
   as labelled badges), action, why, proposed priority, owner, due. Owner and due are
   shown as "unassigned" and blank, exactly as the brief gives them.
9. **Open questions:** what the evidence could not reach or nobody confirmed.
10. **Linked reports:** the file names of the investigation and triage reports and the
    incident log, as plain text (they are local files). Name the report the root
    cause came from here and in the graph's validated node. Show file names only,
    never directories, under the core's portable-reference rule.
11. **Footer:** generated by the producing skill (named in the brief); the mode; the
    log file name; and the model that actually ran.

## Investigation graph

A left-to-right tree of the brief's final root cause, built from nested lists with
elbow connectors (see the layout example for the CSS). Every node is a `details`
element whose summary shows an icon, a status label, and a one-line title, and whose
body holds the investigator's wording as the brief gives it. Draw only what the
brief carries: a node with no source text is not drawn.

| Node | Status label and icon | Source in the brief |
|---|---|---|
| Root, always first | `Impact` (alert) | Impact line and window |
| Validated cause, open by default, green connector to its children | `Validated - root cause` (check) | The final root cause and its confidence; name the source report |
| Four numbered steps under it | `Trigger`, `Mechanism`, `Why it crossed the alert threshold`, `Recovery` (numbers 1 to 4) | The same four links, in that order |
| One node per ruled-out cause, collapsed, title struck through | `Ruled out` (cross) | The ruled-out list |
| One node per open item | `Still open` (question mark) | The still-open list |
| One node per contributing factor | `Contributing factor` (layers) | The contributing factors |
| A link the source did not give | `Not established` (question mark, dashed border) | Shown as written; never filled in |

When no root cause was established, draw no validated node: show one `Still open`
node holding the leading hypothesis, labelled "Hypothesis", and a `Not established`
node for the cause. A cause that came from a triage has no alert-threshold link and
often no ruled-out list: omit the nodes the list would have held, and mark the
missing step `Not established`. The tree never states the cause more strongly than
the brief's confidence.

## Timeline drawing

Two parts, both from the same log entries; add no event the brief lacks.

1. **Swim lanes.** A horizontal axis from a round time before the first entry to a
   round time after the last, with four lanes: Detection (`impact-start`,
   `detected`), Analysis (`hypothesis`, `evidence`), Response (`decision`, `action`,
   `comms`), Outcome (`mitigated`, `resolved`). Each event is a numbered marker in
   its lane, coloured by tag and numbered in time order. Compute each marker's
   horizontal position as `(event time - axis start) / (axis end - axis start)`; do
   not place by eye. Shade the span from `impact-start` to `mitigated` across all
   lanes as customer impact, and the span from `mitigated` to `resolved` as
   mitigated, watching, only when both endpoints are logged. Put the lanes in an
   `overflow-x: auto` container with a minimum width so a phone scrolls the chart,
   not the page. Give it a `role="img"` and an `aria-label` that names the event count
   and the axis window.
2. **Event stream.** The same events as a list in time order. Each row has the
   marker number, the UTC time in a `time` element, the one-line text, the tag as a
   labelled chip, and its source as a chip (`observed`, `reported`, or a skill name).
   The numbers tie the list to the markers, so no label has to sit on the chart.

When fewer than three entries have times, show the event stream alone. Never smooth,
interpolate, or extend the lines: the drawing shows events, not a measured series.

## What the page must not do

- Name a person. The brief carries roles; show roles. A name in the findings is a
  mistake to flag to the producer, not to copy.
- State a duration, a count, or a time that the brief does not carry, or draw a
  chart of anything but the logged timeline. The graph and the swim lanes are
  diagrams of the brief, not measurements.
- State the root cause more strongly than the brief's confidence.
- Reproduce a Secret, a token, an environment value, a connection string, or
  customer data. Say that it exists and where.
- Show a finished-looking status. The chip stays `Draft - awaiting review`.
- Carry any vendor's name, logo, or brand mark, or keep a value from the layout
  example.
