# Redaction guide

## What the script removes

Placeholders are typed, and one value keeps one number inside a run, so
`[IP-1]` is always the same address. The mapping is never written anywhere.

| Category | Placeholder | Levels |
|---|---|---|
| Private key blocks, JWTs, cloud and source-host tokens, chat tokens, webhook URLs, `Authorization` and bearer values, values after secret-named keys (`password`, `token`, `api_key`, `client_secret`, `dsn`, and similar), secret URL parameters | `[REDACTED:SECRET]` | both |
| Password or long user part in a URL (`scheme://user:pass@host`) | `[REDACTED:CREDENTIAL]` | both |
| Long mixed-case tokens no rule named | `[REDACTED:SECRET]`, counted as `possible_unnamed_secret` | both |
| Email addresses | `[EMAIL-n]` | both |
| Phone numbers in international form | `[REDACTED:PHONE]` | both |
| Terms from the denylist lines starting with `!` | `[HOST-n]`, `[ID-n]`, `[ORG-n]` | both |
| Terms from the other denylist lines | same | outside |
| Notification handles (chat, pager, ticketing) | `[HANDLE-n]` | outside |
| IPv4, IPv6, MAC addresses | `[IP-n]`, `[MAC-n]` | outside |
| Hostnames with a common top-level domain (vendor domains kept) | `[HOST-n]` | outside |
| 12-digit numbers (cloud account numbers) | `[ACCOUNT-n]` | outside |
| Values of identifying tags (`host`, `pod_name`, `kube_namespace`, `cluster`, `account`, `project`, `user`, `customer`, `tenant`, and similar) | `[TAG-n]` | outside |
| URL query strings | `?[REDACTED:QUERY]` | outside |

Values that look like secrets but are not (`token_count=5`, `auth: failed`) are
left alone on purpose. When the script over-redacts, that is the safe direction;
restore a value by hand only if the reader needs it and the audience allows it.

## Redacting a live monitor

When the text belongs to a monitor that keeps running, the redactor runs in
place: it removes credentials and personal data (`team` level) but keeps
notification handles (`@name`, `@name@example.org`), because removing one stops a
page. Long tokens it cannot name are flagged for a person, not replaced, because
a replaced link or query breaks the alert. `outside`-level redaction is for a
shared copy only, never a live monitor: swapping a real hostname for a
placeholder in a working alert breaks it.

## The denylist file

One entry per line; blank lines and `#` comments are ignored.

- `example.org` redacts that name and every subdomain of it, and nothing that
  merely starts with it (`example.orgs` is untouched).
- `Acme` or `123456789012` redacts that exact word or number.
- `re:proj-[a-z]+-[a-z0-9-]+` is a case-insensitive regular expression.
- `!Acme` applies at both levels, for names that must never leave even the team.
- `keep: vendor.example` stops a hostname under that domain from being redacted
  at `outside` level. The script already keeps common observability-vendor and
  Kubernetes label domains.

The file holds identifiers, so keep it owner-only and out of any repository. A
skill core states the method and never the target.

## Reading pass checklist

The script cannot know these, so read the output once, as someone outside:

1. **Names of people and customers** in messages, comments, runbook text, and
   tag values such as a `customer` or `owner` tag.
2. **Internal names**: services, pods, namespaces, buckets, queues, databases,
   repositories, project and product code names. Keep the ones the audience needs
   to help; replace the rest with a role (`the checkout service`).
3. **Paths and stack frames**: file paths often carry user names, build agents,
   and repository names.
4. **Free-text secrets**: a password spoken in a comment, a key pasted into a
   message without a key name, a connection string split over lines.
5. **Anything the report flagged** as `possible_unnamed_secret`; check each
   place by eye and keep it redacted unless it is plainly harmless.
6. **Timing and volume** that reveal business facts (order counts, revenue
   metrics, user totals) when the audience is outside.
7. **Links**: a monitor or dashboard link is harmless to the team but lets an
   outsider probe the vendor tenant name in its host; at `outside` level replace
   the link with a description unless the reader needs it.

When something in the input is a live-looking credential, report its location and
type, never its value, and recommend rotation.
