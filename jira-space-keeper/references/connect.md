# Connecting to Jira

Read this when no Jira tools are available, on first contact with a site or
space, or when a call fails with an auth or permission error.

## Which MCP server

| Situation | Server | Sign-in |
|---|---|---|
| Jira Cloud (`*.atlassian.net`), the usual case | Atlassian Rovo MCP Server, `https://mcp.atlassian.com/v2/mcp` | OAuth 2.1 in the browser, as the user |
| Jira Cloud where the agent runs headless | Same server | API token, if the org admin allows token auth for MCP |
| Jira Server or Data Center | Community `sooperset/mcp-atlassian` | Personal access token (Data Center) or email plus API token (Cloud) |

Prefer the official server for Cloud. It acts as the signed-in person, so every
issue shows who really filed it, and there is no long-lived token to store.

## Install and sign in

Tell the user to run these themselves. The sign-in has to happen in their own
browser, and a token should never be pasted into the conversation.

**Official server, Claude Code:**

```bash
claude mcp add --transport http {{JIRA_MCP_SERVER}} https://mcp.atlassian.com/v2/mcp
```

Then, in a Claude Code session, run `/mcp`, choose `{{JIRA_MCP_SERVER}}`, and
approve access in the browser. New MCP servers usually appear only in a new
session. For other agent runtimes, add the same URL as a remote HTTP MCP server
in that runtime's MCP config and complete the OAuth prompt it shows.

**Community server (Server or Data Center):** run it with `uvx mcp-atlassian`,
setting `JIRA_URL` and either `JIRA_PERSONAL_TOKEN` (Server or Data Center) or
`JIRA_USERNAME` with `JIRA_API_TOKEN` (Cloud). The token belongs in the user's
keychain or secret manager and is passed to the server through its environment.
It never goes in a repo, a prompt, or this skill's state files.

**If the connection is refused outright:** an Atlassian org admin has to enable
the Rovo MCP server in the organization's security settings first. That is the
usual cause.

## Capability map

Match on capability, not exact name. Tool names change between server versions,
and the official v2 server exposes a few primary tools and lets the client
discover the rest on demand. If a capability seems missing, use the server's
tool discovery before concluding it is absent. The names below are what each
server used as of late 2026.

| Capability | Official server | Community server |
|---|---|---|
| List reachable sites (gives the cloud ID) | `getAccessibleAtlassianResources` | not needed: one site per server config |
| Who am I signed in as | `atlassianUserInfo` | user-profile tool |
| List visible spaces | `getVisibleJiraProjects` | list-projects tool |
| Issue types and create fields | `getJiraProjectIssueTypesMetadata`, `getJiraIssueTypeMetaWithFields` | field and create-meta tools |
| Search with JQL | `searchJiraIssuesUsingJql` | `jira_search` |
| Read one issue | `getJiraIssue` | `jira_get_issue` |
| Create an issue | `createJiraIssue` | `jira_create_issue` |
| Edit fields | `editJiraIssue` | `jira_update_issue` |
| Comment | `addCommentToJiraIssue` | add-comment tool |
| Transitions | `getTransitionsForJiraIssue`, `transitionJiraIssue` | `jira_transition_issue` |
| Find a person's account | `lookupJiraAccountId` | user-search tool |
| Link issues | `getIssueLinkTypes`, `createIssueLink` | link tools |
| Boards and sprints | `listJiraBoards`, `listJiraBoardSprints`, `manageJiraSprint` | agile tools |

When the official server asks for a `cloudId`, get it once from the site list
and pass it explicitly on every later call. A bare site URL is not enough when
the login can reach several sites.

## First-contact checklist

Run every check, then show the results as one short table before asking the
user to confirm.

| # | Check | How | If it fails |
|---|---|---|---|
| 1 | Jira tools reachable | any read call succeeds | install or sign in, as above, then wait |
| 2 | Signed-in account | the who-am-I tool | if it is not the account the user means to file as (a personal versus work login), sign out in `/mcp` and sign in again |
| 3 | Site reachable | site list includes the chosen site | the OAuth consent covers specific sites, so sign in again and grant this one; if it is still missing, the account has no access to the site |
| 4 | Space visible through MCP | the visible-spaces list includes the key | the user lacks browse permission, or an org admin's AI data policy blocks MCP access to this space even though the web UI shows it; ask the space admin which |
| 5 | Can create issues | issue-type metadata for the space lists at least one creatable type | ask the space admin for create permission; reading and triage can still work |
| 6 | Board profile | profile search (see `board-profile.md`) | bootstrap it (see `board-profile.md`) |

Ask the user, in so many words, to confirm that the account (check 2) and the
site and space (checks 3 and 4) are the ones they mean to file into. Only then
add the entry to `known-spaces.json`.

## known-spaces.json

This is local, per person and per machine. It never holds tokens. It only
decides whether the full first-contact walkthrough runs; the profile in Jira
stays the source of truth.

```json
{
  "spaces": [
    {
      "site": "example.atlassian.net",
      "cloud_id": "<from the site list>",
      "space": "OPS",
      "account": "<display name the MCP is signed in as>",
      "profile_issue": "OPS-1",
      "profile_version": 3,
      "confirmed_at": "2026-10-06T09:12:00Z"
    }
  ]
}
```

Drop an entry when the user asks to, or when a check against that space fails
with an auth or permission error. The next run then repeats first contact.
