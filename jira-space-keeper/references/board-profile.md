# Board profile

The board profile is one issue in the space that holds the space's recording
conventions. Keeping it in Jira means everyone who can file into the space can
also read its rules through the same MCP connection, with no extra repo to
clone or keep in sync.

## The profile issue

- **Type:** a plain task-like type the space has (`Task` when it exists).
- **Summary:** `Board profile: recording conventions (do not close)`.
- **Label:** `space-keeper-profile`. This label is how the profile is found, so
  it is fixed and not configurable.
- **Description:** these three bullets, then exactly one fenced `yaml` block
  holding the schema below:

  ```markdown
  - Recording conventions for this space. jira-space-keeper reads them before every write.
  - Labels are `<prefix>-<subject>`. Each one is explained under `labels.known`.
  - Edit through jira-space-keeper, or keep the YAML valid. Do not close.
  ```
- **History:** every change adds a dated comment (see "Editing the profile").
- **Status:** leave it in the workflow's initial status. Ask a board admin to
  exclude the label from the board's filter, so the profile does not sit in a
  triage column.

Find it with:

```
project = <KEY> AND labels = space-keeper-profile ORDER BY created ASC
```

Exclude it from every other query this skill runs with:

```
AND (labels IS EMPTY OR labels NOT IN (space-keeper-profile))
```

Use that form, not `labels != space-keeper-profile`: in JQL, `!=` also drops
every issue that has no labels at all.

## Schema

Keys are snake_case. Anything not listed is ignored. A missing optional key takes
the default shown. The `epics` section is required for profiles that create
cards; a legacy profile without it must be upgraded before a card is created.

```yaml
schema: 2                      # profile format version; this file describes 2
version: 1                     # bumped on every edit
space: OPS                     # project key; must match the space it lives in
purpose: >-                    # one line shown at the top of every preview
  Findings from SRE investigations and follow-up tasks, triaged weekly.

kinds:                         # record kinds this space accepts
  finding:
    issue_type: Bug            # must exist in the space
    summary_format: "[{source}] {title}"
    labels: [finding]
    template: finding          # description template in records.md
  task:
    issue_type: Task
    summary_format: "{title}"
    labels: [task]
    template: task

severity:
  scale: [critical, high, medium, low, info]   # values callers may send
  target: priority             # priority | label | <custom field id> | none
  map:                         # severity -> value in the target
    critical: Highest
    high: High
    medium: Medium
    low: Low
    info: Lowest

fields:                        # static values set on every created issue
  components: []               # names that exist in the space
  # customfield_10042: "Platform"   # only fields the create screen accepts

epics:                         # every created card must have one
  issue_type: Epic             # the space's Epic type
  field: parent                # create field that assigns a card to its Epic
  inbox:
    key: OPS-400               # existing Epic; use when no named Epic clearly fits
    summary: "Pending - Missing Epic"

labels:                        # this space's label convention; anyone may add to it
  prefixes:                    # label families, named <prefix>-<subject>
    alert: "From a monitoring alert; the subject is the system that alerted"
    src: "Generated: what produced the record"
    rec: "Generated: the record's fingerprint; never set by hand"
  known:                       # every label used here, and when to use it
    finding: "Something observed that people should triage (finding kind)"
    task: "Work someone should do (task kind)"
    agent-recorded: "Generated: an agent, not a person, supplied the record"
    alert-mongodb: "A MongoDB alert fired, or the record is about one. Older issues use mongodb-alert"
  source_prefix: "src-"        # adds src-<source> to each record
  fingerprint_prefix: "rec-"
  agent_label: agent-recorded  # added when an agent, not a person, supplied the records

dedupe:
  similar_window_days: 180     # how far back the similar-issue search looks

triage:                        # named read-only views, shown in this order
  untriaged: "statusCategory = 'To Do' AND assignee IS EMPTY"
  open_findings: "statusCategory != Done AND labels = finding"
  stale: "statusCategory != Done AND updated <= -30d"

manage:                        # operations the space allows through this skill
  assign: true
  transition: true
  link: true
  sprint: false
```

Validation, each run:

- `space` equals the space's key, and every `issue_type` exists there.
- Every field the create screen marks required for each kind's type is supplied
  by `fields`, by the severity mapping, or by the record itself. A newly required
  field shows up here first.
- `epics.issue_type` exists, `epics.field` is accepted on every created kind's
  create screen, and its value selects an Epic rather than a non-Epic parent.
  The inbox resolves to an open Epic with the stated summary. Before selecting
  an Epic for a card, list all open Epics through the Jira MCP with
  `project = <KEY> AND issuetype = "<epics.issue_type>" AND statusCategory != Done`
  and page until the result is complete; do not treat the profile as an Epic
  inventory. The profile stores the actual create-field name: use `parent` only
  when the space accepts it; otherwise use its verified Epic-link field.
- Every `severity.map` value is valid for its target, and every component exists.
- Every label in a kind's `labels`, and every severity label when `target` is
  `label`, is in `labels.known`.
- Triage queries get the space clause and the profile exclusion added
  automatically, so they are written without them.

A failure is a profile problem. Show it under "Problems" in the preview, and
do not write rows that depend on the failing part.

A `schema: 1` profile has `labels.allowed` instead of `prefixes` and `known`.
Load it, and add an `update profile` row that upgrades it to `schema: 2`: drop
`allowed`, and draft `prefixes` and `known` the way the bootstrap does.

## Labels

The profile is the only source of a space's label convention. Each space grows
its own set, so never carry labels over from another space or from memory: read
`labels` in this space's profile every run.

- **Naming.** Lowercase kebab-case, prefix first: `<prefix>-<subject>`, so
  related labels sort and filter together (`alert-mongodb` and `alert-redis`,
  not `mongodb-alert`). Reuse a prefix from `prefixes` when one fits. A label
  that belongs to no family is one word, like `finding`.
- **Picking.** A created issue gets its kind's `labels`, the generated ones
  (`src-`, `rec-`, and `agent_label` when an agent supplied the records), and
  each `known` label whose meaning fits the record. Choose by meaning, not by a
  similar-looking name, and list the labels chosen this way under "Inferred" in
  the preview.
- **Caller labels.** Map each label a user or caller sends to the known label
  it means (`mongodb-alert` becomes `alert-mongodb`). Never add a near-duplicate
  of a known label.
- **Adding a label.** Anyone may add one. When a record needs a label the
  profile lacks, name it by the convention, write a one-line meaning that says
  when to use it, and put it in the preview's `update profile` row. Add a new
  prefix to `prefixes` the same way. Add labels sparingly: only when the user or
  caller asked for one, or for a category that will clearly recur.
- **Labels that break the convention.** A label already on issues, such as
  `mongodb-alert`, is not used for new records. Its convention name goes in
  `known`, with the old name in its meaning so searches can cover both.
  Relabel old issues only when the user asks.

## Epics

The profile requires an Epic before every card is created. No card is created
without an Epic assignment.

- **List first.** Before assigning any card, list every open Epic in the space
  through the Jira MCP and page until complete. Do this on every record-creation
  run, even when the profile has an inbox key. Existing Epics are not required
  to appear in the profile.
- **Resolving.** Match the record to a listed Epic only when its work clearly
  belongs there. If it does not, assign `epics.inbox`. Do not infer a more
  specific Epic just because words look similar.
- **Inbox.** Every profile has exactly one inbox Epic named `Pending - Missing
  Epic`. It is for work that needs recording now but has no clear Epic yet, or
  when there is no time to decide whether a new Epic is warranted. It is a
  deliberate holding place, not permission to leave the card Epic-less.
- **New Epics.** Propose a new Epic only when the work has a durable, distinct
  outcome that does not fit an existing one. Unless the profile explicitly
  defines another format, name it `<Impact> - <Item> <Subject>`, for example
  `Cost - Legacy footprint and cost reduction`, `Stability - Traefik
  observability and hardening`, or `Security - SSO and access governance`.
  The `Pending - Missing Epic` inbox is the sole naming exception.
- **Creating or changing an Epic.** Read the Epic type's create metadata first.
  Add the Epic creation as a preview row before any cards that use it. Update
  the profile only when creating or replacing the inbox Epic. After approval,
  create the Epic, then create the cards with its key. Never use a card's
  summary as a substitute for the relationship field.

## Bootstrap (no profile yet)

1. Read the space's issue types and the create fields for each one.
2. Draft a profile from the schema defaults, adjusted to what really exists:
   - a `finding` kind on `Bug` (or the closest type for defects or findings) and
     a `task` kind on `Task`;
   - severity on `priority` only if the space uses priority, otherwise `label`
     with `severity-<level>` labels;
   - `labels.known` from the labels already on the space's recent issues, each
     with a guessed meaning, plus the kind labels and `agent_label`; a label
     that breaks the naming convention goes in under its convention name (see
     "Labels");
   - no static `fields` except ones that are required and have one obvious
     value.
   - an `epics` section from the space's real Epic type and card create fields.
     Find an existing `Pending - Missing Epic` first; when it does not exist,
     add its creation as a preview row before any record. Do not create cards
     until it can be assigned.
   Do not invent components or custom-field values.
3. Show the draft YAML along with every guess you made, and add "create
   profile" as row 0 of the preview. Do not ask who owns or coordinates the
   space; the preview approval is all the profile needs.
4. After approval, write row 0 first, and the records in the same preview use
   it. Nothing is created in a dry run.
5. If the user drops row 0, use the draft for this run only, mark the preview
   `PROVISIONAL PROFILE`, and give the user the draft YAML so a later run can
   create it. Issues filed now still carry fingerprints and labels, so a later
   real profile can find them.

## Editing the profile

1. Read the current profile issue fresh. Someone else may have changed it since
   this run started.
2. Show the change as a YAML diff and say what it changes for future records
   (for example, "new findings go to type Incident instead of Bug").
3. Validate the new YAML against the space as above.
4. After approval, increment `version`, replace only the YAML block, keep the
   human-written text, and add a comment:
   `YYYY-MM-DD v<old> -> v<new> by <user>: <one-line summary of the change>`.
5. Read the profile back and confirm it parses.

Change the profile only through a profile row: `create profile`, or `update
profile` for any edit, such as adding labels or an Epic mapping a record needs.
Profile and Epic prerequisite rows come before records and are written in their
listed order. Show every profile row's YAML diff under the preview table.
