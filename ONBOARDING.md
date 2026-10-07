# Onboarding guide for an AI agent

You are setting up this skill repo (**sre-ai-skills**: reliability, operations,
tooling, and the skill generator) on a computer, along with any other skill repos the
person uses with the same generator. When you are done, every core in those repos has
a working handler in this machine's skills directory, and the checker passes. The
person should have to answer one short batch of questions and nothing more.

## How the pieces fit

Every skill is two files:

- the **core**, in a skill repo: what the skill does, with double-brace placeholders
  for anything that belongs to a machine. It is committed and portable.
- the **handler**, in the agent's skills directory on each computer: the skill's
  frontmatter (`name`, `description`, `model`, `effort`), a table of this machine's
  values, a secrets table of references, and a "How to run" block that begins with a
  preflight check and then tells you to read the core.

Handlers are **not in git**, because they hold machine values. So a new computer has
the cores (after cloning) and no handlers. Onboarding means generating one handler
per core. This repo holds the generator, the preflight script, and the checker that
every handler uses, so set it up first. Any other skill repo built on this generator
may ship its own `ONBOARDING.md` with repo-specific steps: read it after this one.

## Ground rules

- **Ask once, in one batch.** Discover what you can (existing skills folder, installed
  tools, MCP tool names, skill names) before asking. Never ask a question you can
  answer by looking.
- **Never take a secret in the conversation.** Handlers record where a secret lives,
  never its value. If the person pastes one, do not repeat it or write it anywhere;
  follow `personal-skill-generator/references/secrets.md`.
- **Do not commit, push, or change repo settings** unless asked. Handlers live outside
  the repos, so onboarding should leave every repo exactly as cloned.
- **Never overwrite an existing handler** without showing what changes. Skills in the
  skills directory that have no core (older single-file skills, plugin folders) are
  not part of this layout: leave them alone.
- **Stop on a preflight pause.** If the preflight reports `pause` for any repo, report
  it and wait. Do not switch branches or pull on the person's behalf.
- **Assessment skills need explicit scope.** For any skill that assesses systems, the
  values that define what is in and out of scope are handler variables the person must
  confirm. Never assume a target is in scope, and never put scope in a core.

## Step 0 - ask the batch

Ask these together, offering a default where one exists:

1. The folder to hold the repos (and where they already are, if cloned), and any
   other skill repos to set up besides this one.
2. The clone URLs, for repos that are not on disk yet.
3. The skills directory this agent runtime reads personal skills from.
4. Default model and effort for new handlers, and the model subagents should run on
   (a stronger model for planning and judging, a faster one for subagents).
5. A default working directory for skills that do not name their own.
6. Whether to set up testing: the name of the skill-creator skill and where its scripts
   live, if the person wants to test and tune skills.
7. If there is more than one skill repo: which subject each one holds, so the generator
   can route new skills (recorded as the handler's routing variable).

## Step 1 - get the repos

Clone any repo that is not on disk, into the folder from step 0. Confirm each is on
`main` with `git -C <repo> branch --show-current` and `git -C <repo> status --short`.

## Step 2 - verify branch and freshness

For each repo, run the preflight against any core in it:

```bash
bash <sre-ai-skills>/personal-skill-generator/scripts/preflight.sh <repo>/<core> main origin
```

`PREFLIGHT: ok` means continue. `PREFLIGHT: pause` means stop and report what it
found and the fix commands it printed.

Optional speed-ups (see the generator's "Preflight" section): a `SessionStart` hook that
runs `scripts/preflight-warm.sh`, and the `PREFLIGHT_LAZY=1` / `PREFLIGHT_FF=1` environment
variables.

## Step 3 - bootstrap the generator's handler

The generator makes every other handler, so it must exist first, and it has to be
written by hand because nothing can generate it yet.

1. Copy `personal-skill-generator/templates/handler.SKILL.md` to
   `<skills dir>/personal-skill-generator/SKILL.md`.
2. Replace every `<<TOKEN>>`:
   - `NAME` is `personal-skill-generator`; `DESCRIPTION` is copied character for
     character from the core's frontmatter; `MODEL`, `EFFORT` are the step 0 defaults.
   - `CORE_DIR` is the generator's core folder; `CORE_BRANCH` is `main`;
     `CORE_REMOTE` is `origin`; `PREFLIGHT_SCRIPT` is that folder's
     `scripts/preflight.sh`.
   - `SUBAGENT_MODEL` is the subagent model from step 0, written the way the
     runtime's subagent tool accepts it (check the tool's schema).
   - `WORKDIR` and `OUTPUT_DIR`: this repo's folder is a sensible choice for both.
   - `EXTRA_ROWS`: one row per variable in the generator core's "Variables this skill
     expects" table (the default repo root, the repo routing, the skills directory,
     the defaults for model, effort, subagent model and working directory, the model
     alias mapping, the workspaces folder, and the skill-creator name and folder).
   - `SECRET_ROWS`: a single row saying the skill needs no credentials.
3. Run the checker:

   ```bash
   bash personal-skill-generator/scripts/check-skill.sh <sre-ai-skills>/personal-skill-generator <skills dir>/personal-skill-generator
   ```

   Fix every error. A new session is needed before the skill is listed; if you can
   invoke it in this session, do; otherwise follow its "Onboarding handlers" section
   by hand.

## Step 4 - handlers for every other core

List the cores: each folder directly inside a skill repo that holds a `SKILL.md`,
except the generator. For each one without a handler in the skills directory, follow
the generator core's **"Onboarding handlers for existing cores"** section. It tells
you how to derive each value, which to ask about, and how to treat secrets and scope.
Batch all the questions across all cores into one round.

## Step 5 - verify

1. Run the checker for every core and handler pair, in every repo. All must pass.
2. Run the preflight for every repo once more.
3. Tell the person to start a new session so the handlers are loaded, then confirm
   they appear in the skill list.
4. Optionally smoke-test one skill that is safe and read-only.

## Step 6 - report

Say, briefly: which handlers you created (and where), the values you chose by default
so they can override them, the secret references recorded (names only, plus the
command for storing each), any variable still unset, and that nothing in any repo
was changed.

## When something goes wrong

| Symptom | Cause and fix |
|---|---|
| Preflight says `pause` | Wrong branch, behind the remote, or unverifiable (no network, no remote). Report it; the person fixes it or says "proceed anyway" |
| Checker: "core uses a placeholder the handler has no row for" | Handler is out of date or a variable was missed. Add the row with its value |
| Checker: "core hardcodes the value of X" | A machine value leaked into a core. Replace it with the placeholder and keep the value in the handler |
| Checker: "description differs" | Copy the core's description into the handler exactly |
| Skill not listed | The session was started before the handler existed. Start a new session |
| A secret is needed | Record a reference (keychain item or environment variable name), give the person the command to store the value, and never handle the value yourself |

## Staying in sync later

- After pulling new commits, any core with a new placeholder needs a matching handler
  row; run the checker over everything to find them.
- A new core in any repo needs a handler: follow step 4 for just that core.
- To change a model, effort, folder, or other machine value, edit the handler only.
- To change what a skill does, edit the core, then commit it in the repo (the person's
  call, not yours).
