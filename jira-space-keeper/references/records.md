# Records: input, templates, fingerprints, dedupe

## Input from an agent

An agent that wants findings recorded passes one batch in this shape (YAML or
JSON). A person can just describe the record in words; normalize what they say
to the same shape.

```yaml
site: example.atlassian.net    # optional; defaults to the handler's site
space: OPS                     # optional for people (the skill asks); agents should always set it
source: sre-investigation      # required, kebab-case: what produced these records
source_ref: "<link or path to the investigation, report, or incident>"
caller: datadog-investigate    # the agent or skill handing over the batch
dry_run: false                 # true = preview only, no writes
records:
  - kind: finding              # required: a kind the profile defines
    title: "p99 latency doubled on checkout-api after 14:02 UTC"   # required, <= 120 chars, no trailing period
    stable_id: INV-2026-10-06-03   # optional: the caller's own ID for this exact finding
    resource: checkout-api     # optional: the affected service, host, queue, account...
    severity: high             # optional: a value from the profile's severity scale
    what: >-                   # what was observed, 1-3 sentences, facts only
      ...
    evidence:                  # links and short facts, each one checkable
      - "<dashboard or query link>"
      - "error rate 0.4% -> 6.1% between 14:02 and 14:20 UTC"
    impact: >-                 # who or what is affected, how much, and how sure we are
      ...
    next_step: >-              # suggested next action; the triager decides
      ...
    confidence: medium         # optional: high | medium | low
    labels: [checkout]         # optional extras; must pass the profile's allow-list
    links: []                  # optional related issue keys or URLs
  - kind: task
    title: "Add a burn-rate alert for checkout-api availability SLO"
    why: "..."                 # task template field: why this work matters
    done_when: "..."           # task template field: acceptance in one line
```

Rules for callers:

- One record per distinct problem or piece of work. Do not bundle five findings
  into one ticket, and do not split one finding into five.
- `title` states the problem, not the investigation step ("disk 95% on db-2",
  not "checked disk usage").
- Never put secrets, customer data, or raw log dumps in any field. Link to the
  source instead.
- Give a `stable_id` whenever you have one. It makes dedupe exact across reruns
  of the same investigation.
- Keep `confidence` honest: a `low` finding is still worth recording, as long as
  it is labelled that way.

## Description templates

Use the template the kind's profile entry names. Leave out an empty section
rather than writing "N/A". Jira renders the Markdown when the MCP converts it;
read one created issue back to confirm it rendered.

**finding**

```markdown
**What we saw**
<what>

**Evidence**
- <evidence item>

**Impact**
<impact>  (confidence: <confidence>)

**Suggested next step**
<next_step>

----
Recorded via jira-space-keeper by <caller or "a person"> on <YYYY-MM-DD>.
Source: <source> <source_ref>
Fingerprint: <rec-label>
Stable ID: <stable_id>
```

**task**

```markdown
**Why**
<why>

**Done when**
<done_when>

**Context**
- <evidence or links>

----
Recorded via jira-space-keeper by <caller or "a person"> on <YYYY-MM-DD>.
Source: <source> <source_ref>
Fingerprint: <rec-label>
```

The footer is what lets a person, or a later run, trace an issue back to where
it came from. Never remove it when editing an issue this skill created.

## Fingerprint

`scripts/space_keeper.py fingerprint` computes it, so every person and every
machine gets the same label for the same record:

- With a `stable_id`: `sha256("v1|" + source + "|id:" + stable_id)`.
- Without one: `sha256("v1|" + source + "|t:" + title + "|r:" + resource)`.
- Before hashing, `source`, `stable_id`, `title`, and `resource` are lowercased,
  Unicode-normalized, stripped of punctuation, and whitespace-collapsed.
- The label is the profile's `fingerprint_prefix` plus the first 12 hex digits.

A reworded title changes the fingerprint. That is why the similar-issue search
below always runs too.

## Dedupe searches

Run both for every record. Add the profile exclusion to each query.

1. **Exact:** `project = <KEY> AND labels = <rec-label>`, across all statuses.
2. **Similar:** `project = <KEY> AND text ~ "<3-6 distinctive words>" AND
   created >= -<similar_window_days>d`. Pick words a person would also use: the
   resource name, the symptom, and the component. Leave out dates, numbers, and
   words like "issue" or "error". When a `resource` exists, run a second query
   with `text ~ "<resource>"` alone.

Judge the similar matches yourself. Two issues are duplicates only when fixing
one would close the other. Same resource with a different symptom is not a
duplicate; mention it as related in the preview.

When the default action is a comment on an existing issue, the comment holds
only what is new: new evidence, a new time window, changed impact, and the same
footer. Never restate the whole finding.
