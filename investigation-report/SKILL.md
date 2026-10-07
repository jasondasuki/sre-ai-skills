---
name: investigation-report
description: Write the finished HTML report document for an investigation, triage, Kubernetes cost review, or incident postmortem - one self-contained, escaped, dark-mode-aware page saved to disk with a dated title and file name, in the report format (profile) the calling skill names. Use whenever a skill or the user needs the report for a completed root-cause investigation (hypothesis tree, evidence, final root cause), a completed workload triage (what is broken, evidence, narrowest fix), or a completed cost review (prioritized changes, marginal savings, reliability constraints, evidence), or a completed incident postmortem (timeline, impact, root cause, action items), or says "write the report", "make an HTML report", "save this investigation as a document", "report for the triage", "cost review report", "postmortem report", or "document what we found" - even if they do not say HTML. Owns the page rules, the title and file name rules, the output folder, and the checks after writing; the producing skill owns the findings.
---

# Investigation report

Turn findings that already exist into one HTML report file. The investigating
skill (the **producer**) decides what is true; this skill decides how it is laid
out, escaped, named, and saved. Keeping the two apart means every report looks
and behaves the same no matter which skill produced it, and a producer never has
to re-derive page rules.

## Variables this skill expects

Supplied by the machine-local handler. Use these placeholders; never write a
literal path, model, or skill name in this file.

| Variable | Meaning |
|---|---|
| `{{WORKDIR}}` | Working directory for shell commands |
| `{{OUTPUT_DIR}}` | Root folder for reports when the caller names no folder of its own |
| `{{INVESTIGATION_OUTPUT_DIR}}` | Fallback folder for investigations when a caller incorrectly supplies a cost-review destination |
| `{{PAGE_DESIGN_SKILL}}` | Skill that governs the page contract for HTML output |
| `{{CHART_SKILL}}` | Skill that governs charts, loaded before drawing any chart |
| `{{OPEN_COMMAND}}` | Command that opens a file for viewing on this machine |

## The brief

The caller gives you a brief. Without it, ask for the missing field rather than
guess; each one changes the file you write.

| Field | Meaning |
|---|---|
| profile | Which report format to use (see "Profiles") |
| output folder | Where to write; the caller's own folder. Use `{{OUTPUT_DIR}}` only when the caller names none |
| time and title facts | The date and time (UTC) and the title text the profile's title rule needs |
| producer facts | The producing skill's name, the mode, the model that actually ran, and anything else the profile's footer lists. The time the report was generated is your own clock when you write it, in UTC, not a value the findings carry |
| findings | Everything the report says. These are already in the conversation from the producer's own report; do not re-investigate |
| page-design skill (optional) | Caller-selected design skill; when provided, load it instead of the default `{{PAGE_DESIGN_SKILL}}`. The report profile still governs the title, sections, and filename |

## Profiles

A profile is one report format: its title and file name rules, its sections, and
its visuals. Read the profile file the brief names before you write.

| Profile | For | File |
|---|---|---|
| `hypothesis-investigation` | A root-cause investigation that tests hypotheses against telemetry | `references/profile-hypothesis-investigation.md` |
| `triage` | A workload triage that ends in a cause, evidence, and a narrowest fix | `references/profile-triage.md` |
| `cost-review` | A Kubernetes cost review with prioritized changes, marginal savings, reliability constraints, and evidence | `references/profile-cost-review.md` |
| `postmortem` | A resolved incident with timeline, impact, final root cause, and action items | `references/profile-postmortem.md` |

If the brief names a profile not in this table, stop and say so. Do not improvise
a format: the point of a profile is that the same kind of report always looks the
same.

## Steps

1. **Check the brief** has every field above, and that the findings are complete
   (a report written from half a result misleads the reader who trusts it).
2. **Pick the folder by the report's purpose.** Use the caller's output folder
   and create it with `mkdir -p` if it does not exist. Cost-review destinations
   are reserved for reviews whose primary goal is cost optimization. A report
   investigating failures, root cause, reliability, or operational capacity belongs
   in an investigation destination, even if it discusses prices or reuses cost-review
   evidence. If the caller supplied its cost-review default for an investigation,
   use `{{INVESTIGATION_OUTPUT_DIR}}` and return the corrected path. Preserve a
   suitable producer-specific investigation folder and explicit user destination
   overrides. Check that the brief's profile also matches the purpose; have the
   producer correct a cost-review brief used for an investigation before writing.
3. **Read the profile** the brief names, in full.
4. **Load the design skills.** Load the brief's page-design skill when provided,
   otherwise `{{PAGE_DESIGN_SKILL}}`, and follow its page
   contract (colour tokens on `:root`, dark-mode variants, explicit `body`
   background, phone-width layout). Load `{{CHART_SKILL}}` before drawing any chart.
5. **Write the page** to the file name the profile's rule gives. Never overwrite an
   existing report; if the name exists, append `-2`. Keep the producer's evidence
   IDs, their order, and the tree nesting exactly as the findings give them: do not
   renumber, and do not invent structure the findings lack (a flat list stays flat).
   Link to an object only when the brief carries its URL; otherwise show its ID as
   plain text, because a guessed link is a wrong link.
6. **Check it.** The file exists and is not empty; the `<title>` and the `<h1>` are
    the same string and match the profile's title rule; every section the profile
    lists is present, in order; nothing from telemetry sits unescaped. Apply the
    portable-reference rules below to prose, links, code blocks, and embedded
    evidence; verify that no machine-local directory path remains.
7. **Hand back** the full path and the command to view it, which is
   `{{OPEN_COMMAND}}` followed by the path. The producer puts these at the end of
   its chat reply.

## Page style

Use a warm, restrained visual style: warm neutral surface, generous whitespace, a
serif or humanist heading face with a system sans body, soft rounded cards, and
one restrained accent colour. Everything is inline: one file, inline CSS, no
external fonts or scripts unless `{{PAGE_DESIGN_SKILL}}` allows them. Small inline
JS is fine (for example expand/collapse). The file is a local document and no
publisher wraps it, so write a complete one (doctype, charset, viewport meta) and
follow the design skill's theming and layout rules, not its advice to omit the
document skeleton. Convey every status through an icon and
a text label as well as colour, so the page reads without colour vision. A profile
may set its own visual language (the `postmortem` profile does, with a layout
example); where it does, the profile's palette and layout replace the warm style
above, and every rule in this file still applies.

## Hard rules

Each rule has a reason; the reason is what lets you apply it to a case not listed.

- **Escape everything** you interpolate: queries, log messages, tag values, and
  titles contain `<`, `>`, `&`, and quotes. Use proper HTML escaping so nothing
  from telemetry can render as markup or script. Do not use `innerHTML` on
  telemetry strings. The report is opened in a browser by someone who trusts it.
- **No secrets or customer data.** Name the type and location, never the value. No
  emails, tokens, message bodies, passwords, or full request payloads. A saved file
  outlives the conversation and gets shared.
- **No invented data.** Charts and numbers come only from results actually
  retrieved. If a chart needs points that were not fetched, show a table or a stat
  tile instead. Never draw a plausible-looking curve: a reader cannot tell it from
  a measured one.
- **Same content as the chat report.** The HTML is the same findings in a better
  container, not new claims. Anything in it traces to evidence the producer
  recorded.
- **Portable references.** Replace paths inside the producer's scoped source
  repositories with verified GitHub links. Resolve the repository from its actual
  remote, normalize SSH remotes to HTTPS, and prefer the reviewed commit. Use
  `blob` for files and `tree` for directories; link a wildcard to its verified
  parent directory and keep the pattern as text. Preserve known line anchors.
  Never infer the organization from a checkout folder or invent a missing target.
  Remove all other machine-local directory paths, including home shorthand,
  file URLs, temporary/preview directories, output folders, and commands that
  expose them. Keep a standalone artifact filename when it is useful for a
  citation; omit directory-only references. Apply this to Markdown/JSON excerpts
  as well as visible HTML, and render source links as clickable links outside
  literal evidence blocks. Absolute paths needed to read/write or open files
  belong in runtime inputs and the handoff chat, not the saved document.
- **Do not publish it.** Do not call a page-publishing tool, and do not upload the
  file anywhere. It stays a local file unless the user asks to share it; then offer
  to publish it as a private hosted page when a publishing tool is available.

## Reference files

- `references/profile-hypothesis-investigation.md`: the hypothesis-tree report
  format, with its diagram section.
- `references/profile-triage.md`: the workload triage report format.
- `references/profile-cost-review.md`: the Kubernetes cost-review report format.
- `references/profile-postmortem.md`: the incident postmortem report format.
- `references/postmortem-layout-example.html`: the postmortem page's layout
  reference, with synthetic content. Copy the structure and CSS, never the values.
