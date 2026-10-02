---
name: <<NAME>>
description: <<DESCRIPTION>>
model: <<MODEL>>
effort: <<EFFORT>>
---

# <<NAME>> (local handler)

This is the machine-local half of the skill. It holds values that belong to this
computer and this agent setup. The general instructions live in the shared core.

## How to run

1. **Preflight, before anything else.** Run
   `bash <<PREFLIGHT_SCRIPT>> <<CORE_DIR>> <<CORE_BRANCH>> <<CORE_REMOTE>>` (the values of `PREFLIGHT_SCRIPT`,
   `CORE_DIR`, `CORE_BRANCH`, `CORE_REMOTE` below). If it prints `PREFLIGHT: ok`,
   continue. If it prints `PREFLIGHT: pause`, or the script is missing or fails to
   run, **stop**: do not read the core and do not run the skill. Say so in the
   first lines of your reply: which skill, what the script found, and the fix
   commands it printed. If a notification tool is available, also send one short
   notification so the user sees it when away. Run no git command that changes
   the checkout (no switch, pull, stash, or reset); fixing it is the user's call.
   Then wait. If the user answers "proceed anyway", continue for this run only
   and say in your final answer that the core was not verified current.
2. Read `<<CORE_DIR>>/SKILL.md` in full, plus any file in that directory it tells
   you to read (paths in the core are relative to the core directory). If the core
   is missing, stop and tell the user the skills repo is not at that path. Do not
   improvise the skill from memory.
3. Wherever the core uses a double-brace placeholder, substitute its value from
   the tables below. If the core uses a placeholder with no row here, this
   handler is out of date: stop and name the missing variable.
4. Run every shell command for this skill from `WORKDIR`, using absolute paths,
   and write outputs under `OUTPUT_DIR` unless the core says otherwise.
5. Resolve secrets only as described under "Secrets" below, and never print them.
6. When the core tells you to spawn subagents, give each one the model in
   `SUBAGENT_MODEL` (and the type in `SUBAGENT_TYPE` if the table defines one).
   Never let a subagent inherit this skill's model unless the core says to.
7. Follow the core's instructions from there.

## Local variables

| Variable | Value | Purpose |
|---|---|---|
| `SKILL_NAME` | `<<NAME>>` | This skill's name |
| `CORE_DIR` | `<<CORE_DIR>>` | Where the portable core lives |
| `CORE_BRANCH` | `<<CORE_BRANCH>>` | Branch the core's repo must be on |
| `CORE_REMOTE` | `<<CORE_REMOTE>>` | Remote the core's branch must be up to date with |
| `PREFLIGHT_SCRIPT` | `<<PREFLIGHT_SCRIPT>>` | Script that checks branch and freshness before every run |
| `MODEL` | `<<MODEL>>` | Model for this skill (same as frontmatter) |
| `EFFORT` | `<<EFFORT>>` | Effort for this skill (same as frontmatter) |
| `SUBAGENT_MODEL` | `<<SUBAGENT_MODEL>>` | Model passed to subagents this skill spawns, as the subagent tool accepts it |
| `WORKDIR` | `<<WORKDIR>>` | Working directory for this skill's commands |
| `OUTPUT_DIR` | `<<OUTPUT_DIR>>` | Where this skill writes its outputs |
<<EXTRA_ROWS>>

## Secrets

References only. Resolve a secret inside the same command that uses it, pass it
through the environment or stdin, and never echo, log, or save it. See the core
generator's secrets guide for the patterns.

| Name | Reference | Used for |
|---|---|---|
<<SECRET_ROWS>>
