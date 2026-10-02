---
name: <<NAME>>
description: <<DESCRIPTION>>
---

# <<TITLE>>

<One paragraph: what this skill does and the outcome it produces.>

## Variables this skill expects

Supplied by the machine-local handler. Use these placeholders; never write a
literal path, model, MCP server name, or credential in this file.

| Variable | Meaning |
|---|---|
| `{{WORKDIR}}` | Working directory for all commands |
| `{{OUTPUT_DIR}}` | Where outputs are written |
<Add one row per skill-specific variable. Add the subagent model variable only if
the skill spawns subagents.>

## Rules

<The constraints that matter and, for each, the reason it matters.>

## Steps

<The procedure, in imperative voice.>

## Output

<The exact shape of the result, as a template when the format matters.>
