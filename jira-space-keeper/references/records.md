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
    what:                      # facts only, one per item
      - "..."
    evidence:                  # links and short facts, each one checkable
      - "<dashboard or query link>"
      - "error rate 0.4% -> 6.1% between 14:02 and 14:20 UTC"
    impact: "..."              # who or what is affected, and how much
    confidence: medium         # optional: high | medium | low, as the source stated it
    next_step: "..."           # one suggested action; the triager decides
    still_open: []             # optional: what the source could not verify
    labels: [alert-checkout-api]   # optional hints; mapped to the profile's known labels
    links: []                  # optional related issue keys or URLs
  - kind: task
    title: "Add a burn-rate alert for checkout-api availability SLO"
    why: "..."                 # why this work matters
    done_when: "..."           # one checkable condition: "alert on X above Y exists", not "improve monitoring"
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
- Pass a cause and `confidence` exactly as your analysis stated them. The skill
  never strengthens them.
- `labels` are hints. The space's board profile decides the final labels: a
  hint is mapped to the known label it means, or proposed as a new one in the
  preview.

## Description templates

- Use the template the kind's profile entry names.
- Bullets only, no prose paragraphs.
- Drop an optional bullet that has nothing in it. A required one (finding: What,
  Impact; task: Why, Done when) the source did not establish reads
  `not established`.
- Write every time in UTC and say so (`14:02 UTC`).
- `Possible regression of` appears only when dedupe found a done issue with the
  same fingerprint.

**finding**

```markdown
- **Possible regression of:** <KEY>
- **What:**
  - <fact>
- **Evidence:**
  - <link or fact>
- **Impact:** <impact> (confidence: <confidence>)
- **Next step:** <next_step>
- **Still open:**
  - <what is not verified>

----
Recorded on <YYYY-MM-DD>.
Fingerprint: <rec-label>
```

**task**

```markdown
- **Why:** <why>
- **Done when:** <done_when>
- **Context:**
  - <link or fact>

----
Recorded on <YYYY-MM-DD>.
Fingerprint: <rec-label>
```

**comment** (new evidence on an existing issue)

```markdown
- **New:**
  - <evidence, or a new time window>
- **Impact change:** <only if it changed>

----
Recorded on <YYYY-MM-DD>.
Fingerprint: <rec-label>
```

Footer:

- Only these two lines. The date comes from `date -u`.
- No source, caller, or stable ID: the source is already in the `src-` label,
  and the fingerprint is how a later run finds the issue.
- Never remove it when editing an issue this skill created.

## Fingerprint

`scripts/space_keeper.py fingerprint` computes it, so every person and machine
gets the same label for the same record. A reworded title changes it, which is
why the similar-issue search below always runs too.

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

A comment on an existing issue uses the comment template: only what is new.
Never restate the whole finding.
