# Severity

Read this at "Open" and whenever the impact changes. Severity sets how often
updates go out and how much attention the incident gets, so it is worth a
moment, but it is a proposal: the incident commander decides.

## Contents

- The scale
- How to propose a level
- Re-proposing

## The scale

| Level | Meaning | Typical signs |
|---|---|---|
| SEV1 | Critical. The service is down or unusable for most users, or data is being lost or exposed. | Total outage of a core flow; data loss or corruption; a confirmed security exposure of user data |
| SEV2 | Major. A core flow is badly degraded or fully unavailable for a significant share of users, with no easy workaround. | Sustained high error rate or latency on a core flow; one region or one large customer fully down |
| SEV3 | Minor. A non-core flow is degraded, or a core flow is degraded for a small share of users, or there is a workaround. | Elevated errors on a secondary feature; slow batch jobs; partial degradation with retries succeeding |
| SEV4 | Low. No user impact now, but it needs attention before it becomes one. | A single replica failing behind healthy capacity; a nearly-full disk; an alert with no user effect |

A data-loss or data-exposure signal sets the level to SEV1 regardless of how many
users are affected, because it cannot be undone.

## How to propose a level

1. Ask what the evidence shows about **who is affected, how badly, and since
   when**, in that order. Use only what was observed or reported; say "unknown" for
   the rest.
2. Pick the highest level whose description fits. When two fit, take the higher and
   say what would lower it.
3. Say it in one line: `SEV2 (proposed): checkout errors at roughly 30% for all
   users; would drop to SEV3 if the retry path is confirmed healthy.`

An alert with nothing showing that users are affected is SEV4. Its status is still
`open`: it is a watch, not worked as a full incident, until user impact is reported
or seen, a critical threshold is crossed, or the alert does not clear. When that
happens, re-propose the level.

## Re-proposing

Re-propose whenever the impact grows, shrinks, or a new fact changes the reading
(for example, a data-integrity signal appears). Log each change as a `note` entry
with the reason, and keep the earlier level in the log so the postmortem can show
how the picture changed.
