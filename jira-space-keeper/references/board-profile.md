# Board profile

The board profile is one issue in the space that holds the space's recording
conventions. Keeping it in Jira means everyone who can file into the space can
also read its rules through the same MCP connection, with no extra repo to
clone or keep in sync.

## The profile issue

- **Type:** a plain task-like type the space has (`Task` when it exists).
- **Summary:** `Board profile: recording conventions (pinned, do not close)`.
- **Label:** `space-keeper-profile`. This label is how the profile is found, so
  it is fixed and not configurable.
- **Description:** two or three sentences for humans (what this is, who owns it,
  "edit through the jira-space-keeper skill or keep the YAML valid"), followed
  by exactly one fenced `yaml` block holding the schema below.
- **History:** every change adds a dated comment (see "Editing the profile").
- **Status:** leave it in the workflow's initial status. Ask the owner to
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
the default shown.

```yaml
schema: 1                      # profile format version; this file describes 1
version: 1                     # bumped on every edit
space: OPS                     # project key; must match the space it lives in
owners:                        # people who approve profile changes
  - "Jane Doe"                 # display name as shown in Jira
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

labels:
  allowed: []                  # empty = any label; non-empty = only these plus the generated ones
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
- Every `severity.map` value is valid for its target, and every component exists.
- Triage queries get the space clause and the profile exclusion added
  automatically, so they are written without them.

A failure is a profile problem. Show it under "Problems" in the preview, and
do not write rows that depend on the failing part.

## Bootstrap (no profile yet)

1. Read the space's issue types and the create fields for each one.
2. Draft a profile from the schema defaults, adjusted to what really exists:
   - a `finding` kind on `Bug` (or the closest type for defects or findings) and
     a `task` kind on `Task`;
   - severity on `priority` only if the space uses priority, otherwise `label`;
   - no static `fields` except ones that are required and have one obvious
     value.
   Do not invent components or custom-field values.
3. Show the draft YAML along with every guess you made, and ask: **"Do you own
   or coordinate this space, so the conventions here will apply to everyone who
   files into it?"**
4. **Owner (yes):** put `owners` as the user (plus anyone they name), add
   "create profile" as row 0 of the preview, and write it first after approval.
   Nothing is created in a dry run.
5. **Not the owner (no):** use the draft for this run only, mark the preview
   `PROVISIONAL PROFILE`, and give the user the draft YAML with a one-paragraph
   note they can send to the space owner. Issues filed now still carry
   fingerprints and labels, so a later real profile can find them.

## Editing the profile

1. Read the current profile issue fresh. Someone else may have changed it since
   this run started.
2. Show the change as a YAML diff and say what it changes for future records
   (for example, "new findings go to type Incident instead of Bug").
3. Confirm the user is in `owners`, or says an owner approved the change. If
   not, give them the diff to send to an owner and stop.
4. Validate the new YAML against the space as above.
5. After approval, increment `version`, replace only the YAML block, keep the
   human-written text, and add a comment:
   `YYYY-MM-DD v<old> -> v<new> by <user>: <one-line summary of the change>`.
6. Read the profile back and confirm it parses.

Never change a profile as a side effect of recording. If a record needs a label
outside `allowed`, show that as a problem in the preview and offer a separate
profile change.
