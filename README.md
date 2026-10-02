# sre-ai-skills

Portable cores for personal agent skills. Each directory here is the
general function of one skill. The machine-specific half (a thin handler holding
the working directory, model, effort, MCP server names, and references to
secrets) lives next to the agent runtime's skills directory on each computer, never
here.

```
<skill-name>/SKILL.md      core: what the skill does, with {{VARIABLE}} placeholders
<skill-name>/references/   longer docs the core loads on demand
<skill-name>/scripts/      deterministic helpers
```

Setting up a new computer (or pointing an AI agent at this repo)? Follow
[ONBOARDING.md](ONBOARDING.md).

Create and maintain skills with `personal-skill-generator`. Check one pair with:

```bash
bash personal-skill-generator/scripts/check-skill.sh <core-dir> <handler-dir>
```

The cores must stay free of absolute paths, model IDs, MCP server names, and
credentials; the checker enforces that. `.workspaces/` holds test runs and is
git-ignored.
