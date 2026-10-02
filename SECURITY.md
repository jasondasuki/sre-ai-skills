# Security policy

## Reporting a vulnerability

Please report security issues privately. Do not open a public issue.

Use GitHub's private vulnerability reporting:
<https://github.com/jasondasuki/sre-ai-skills/security/advisories/new>

Include what you found, where it is, and how to reproduce it. Expect an
acknowledgement within a week.

## Scope

This repository holds portable skill cores: Markdown instructions and small
shell helpers. It contains no credentials by design, and the checker in
`personal-skill-generator/scripts/check-skill.sh` enforces that. If you find a
secret, an absolute path, or an internal hostname in any file, report it the
same way.

## Contributions

Only the maintainer can push to `main`. Fork the repository and open a pull
request to propose a change.
