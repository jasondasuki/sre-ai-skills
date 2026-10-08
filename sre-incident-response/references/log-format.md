# Incident log format

The template `open` writes, the statuses, and the tags. Read this when writing the
state block or choosing a tag (Step 5 of "Live incident").

What `open` writes into the log, and what the entries look like (the synthesis
block is described in "Synthesize the evidence"):

```
# <id>: <impact in a few words>

## State
Status: open | closed
Severity: <SEV level> (proposed | confirmed)
Impact: <who or what is affected, how badly, since when>
Leading hypothesis: <cause as the investigator stated it, with confidence> | none yet
Actions taken: <short list>
Owner: <role>
Next update due: <UTC time>

## Synthesis
<Updated line, source table, Combined reading, Open, Next evidence needed>

## Timeline
- <YYYY-MM-DD HH:MM[:SS]>Z [<tag>] <one line>  (source: <observed | reported | skill name>[; logged <time>])
```

Statuses are only two. `open`: the incident is being worked or watched, at any
severity (a SEV4 watch is open). `closed`: it is over. How it ended is in the
timeline, not the status: a `resolved` entry means it was an incident (the
postmortem is due), a `closed` entry alone means it was stood down with no
incident. `mitigated` is a timeline entry too, not a status. Old logs may carry
`monitoring`, `mitigated` (read as open) or `resolved` (read as closed).

Tags:

| Tag | Use |
|---|---|
| `impact-start` | When users began to be affected; only with evidence or the human's word |
| `alerted` | When the monitor or alert first fired |
| `engaged` | When a person or this skill started working it |
| `hypothesis`, `evidence` | An investigator's stated cause, and the line it names as proof |
| `decision`, `action` | What the commander chose, and what was then done |
| `mitigated`, `resolved` | Recovery on evidence, and the human's close |
| `closed` | Stood down with no incident, with the reason |
| `comms` | A status update draft was prepared |
| `note` | Severity changes and anything else that bears on the story |

`alerted` and `engaged` are separate because they measure different things: time to
detect (impact start to alert) is about the monitoring, time to engage (alert to
first response) is about the response. One event per line. Link to a saved answer by
the link `save` printed (`<source>.md`, a name inside the incident folder, so the
postmortem finds it beside the log), and to a system by its id as plain text.
