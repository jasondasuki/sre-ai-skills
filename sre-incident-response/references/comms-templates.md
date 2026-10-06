# Status update drafts

Read this when a status update is due. These are drafts for the human to review and
send; this skill never posts them. Write for a reader who is not an engineer and
has not been following: plain words, what users see, what is being done, when the
next update comes.

## Contents

- Rules for every draft
- Investigating
- Identified
- Mitigated, monitoring
- Resolved
- Overdue reminder

## Rules for every draft

- **State only what is established.** Do not name a cause until an investigator
  (the telemetry investigation or the cluster triage) has reported one with medium
  or high confidence, and then say "we believe" unless it is high.
- **Describe user impact, not internals.** No hostnames, cluster names, ticket
  numbers, secrets, or customer data.
- **Always give the next update time** in UTC (and the local time if the user gave
  a time zone). A missing next-update time makes readers ask for one.
- **No promises of a fix time** unless the commander states one.
- Keep each draft under about 80 words.

## Investigating

```
[SEV<n>] <service or feature>: investigating
We are seeing <user-visible symptom> affecting <who>. Since <time> UTC.
The team is investigating. Next update by <time> UTC.
```

## Identified

```
[SEV<n>] <service or feature>: cause identified
We believe <plain-language cause>. <What users may still see.>
The team is <the mitigation under way, or the next step>.
Next update by <time> UTC.
```

## Mitigated, monitoring

```
[SEV<n>] <service or feature>: mitigated, monitoring
A fix is in place as of <time> UTC and <the metric users feel> has returned to
normal. We are watching it before closing the incident.
Next update by <time> UTC.
```

## Resolved

```
[SEV<n>] <service or feature>: resolved
The issue is resolved as of <time> UTC. It affected <who> from <start> to <end> UTC.
<One sentence on cause if established.> A full review will follow.
```

## Overdue reminder

When a scheduled update has passed without one, open your reply with:

```
Status update was due at <time> UTC (<n> minutes ago). Draft below.
```
