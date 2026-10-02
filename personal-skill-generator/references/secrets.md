# Secrets in handler-and-core skills

A skill may need a credential: an API key, a token, a password. The rule is that
the handler records **where** the credential lives and **how to fetch it**, and
nothing in the skill ever contains the value. The core does not even know where
it lives.

## Reference types

Pick one per secret and record it in the handler's secrets table.

| Type | Reference form | How it is resolved |
|---|---|---|
| Keychain item | `keychain:<service>` (account is the login user) | read from the macOS login Keychain at the moment of use |
| Environment variable | `env:<NAME>` | read from the process environment at the moment of use |
| Private file | `file:<path>#<KEY>` | read one `KEY=value` line from an owner-only file at the moment of use |

Prefer Keychain, then an environment variable. Use a private file only when the
user asks for it or the other two are impractical.

## Using a secret without exposing it

Everything a command prints becomes part of the conversation, so never fetch a
secret in one command and use it in the next. Resolve it inside the same command
that uses it and pass it through the environment or stdin, not on the command
line:

```bash
# Keychain: resolved and consumed in one shell, never printed
API_TOKEN="$(security find-generic-password -s "<service>" -a "$USER" -w)" \
  sh -c 'curl -sS -H "Authorization: Bearer $API_TOKEN" "<url>"'
```

Rules that follow from that:

- Never print, echo, log, or write the value. This includes debug output,
  `set -x`, error messages, saved HTML or JSON, and test fixtures.
- Never put the value in a URL, a command-line argument, or a file under the
  repo. Arguments are visible to every process on the machine.
- If a tool echoes the credential back (some APIs include it in responses), strip
  it before showing or saving output.
- If you do see a secret in an output by accident, do not quote it; say that it
  appeared, in which output, and recommend rotating it.

## Storing a secret (what to tell the user)

The user should do this in their own terminal, so the value never enters this
conversation:

```bash
# Keychain: prompts for the value; nothing is stored in shell history
security add-generic-password -s "<service>" -a "$USER" -U -w
```

Or export the variable from a shell startup file they control. Tell them the
exact service or variable name you recorded in the handler.

## If a secret was pasted into the chat

1. Do not repeat it. Do not write it anywhere.
2. Say it was shared in the conversation and that rotating it is the safe choice
   if it protects anything valuable.
3. Offer the storage command above and record only the reference.
4. Only if the user explicitly asks you to store it for them: create a private
   file in the handler directory with owner-only permissions (set the umask
   before creating it), write one `KEY=value` line, record a `file:` reference,
   and never display the file's contents afterwards.

## What the handler's secrets table looks like

| Name | Reference | Used for |
|---|---|---|
| `SOME_API_TOKEN` | `keychain:<service>` | the API the skill calls |

If a skill needs no credentials, the table says so in one line instead of being
omitted, so a reader knows it was considered.
