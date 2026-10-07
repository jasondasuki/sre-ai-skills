# First run

The path a new user follows the first time they use this skill. Show it to the
user in step 1 whenever the Jira tools are missing or the space is a first
contact. Show only the steps they still have left, in a few lines, and say which
one they are on. People mostly get stuck between steps 2 and 3, so name that
step explicitly.

## The path

1. **Install the Jira MCP server (once per machine).** In Claude Code:

   ```bash
   claude mcp add --transport http {{JIRA_MCP_SERVER}} https://mcp.atlassian.com/v2/mcp
   ```

   Any server name works. Whatever name is used goes in the handler's
   `JIRA_MCP_SERVER`. Other runtimes are covered in `connect.md`.
2. **Sign in (once per Atlassian site).** Run `/mcp`, choose the server, and
   approve access in the browser. Grant the site that holds the space, and sign
   in with the account issues should be filed as.
3. **Start a new agent session.** A server added or signed in during a session
   usually exposes no tools until the next session. `claude mcp list` can report
   it as connected while the current session still has no Jira tools.
4. **First contact, as a dry run (once per space).** For example:

   ```
   /jira-space-keeper First contact with the <KEY> space, dry run: draft its board profile and preview this task: <a real task>
   ```

   Expect, with nothing written to Jira:
   - the access checks as a short table, and a request to confirm the account,
     site, and space;
   - the space's board profile, or a draft built from its real issue types and
     required fields;
   - a preview marked `DRY RUN`: your task, plus row 0 "create profile" when
     the space has no profile yet.
5. **Settle the board profile (once per space).**
   - **The space already has one:** nothing to do. Your records follow it.
   - **No profile yet:** rerun the same request without "dry run" and approve
     the preview. Row 0 creates the profile, and everyone who files into the
     space follows it from then on. Ask a board admin to exclude the
     `space-keeper-profile` label from the board filter, so the profile does
     not sit in a triage column.
6. **Use it normally.** Each run reads the profile, checks for duplicates, shows
   one preview, and writes only after you approve. Typical requests:
   - "Log a task in <KEY>: <what> before <when>"
   - "Record these findings from the investigation on the <KEY> board"
   - another agent handing over a batch in the format in `records.md`
   - "What's untriaged in <KEY>?"
   - "Add the label alert-<system> to the <KEY> board profile: <when to use it>"

Optional: once the site is known, set it as the handler's `JIRA_SITE` so the
skill stops asking or discovering it.
