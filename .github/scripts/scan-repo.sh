#!/usr/bin/env bash
# Scan the tracked files for material that must not be public: credentials,
# absolute home paths, MCP tool names. Prints locations only, never values.
# Usage: scan-repo.sh [base-ref]   (base-ref also enables the author-email check)
# Exit status: 0 when clean, 1 when any error.
set -u

errors=0
files() { git ls-files -z | grep -zv '^\.github/scripts/scan-repo\.sh$'; }

scan() { # scan <label> <regex>
  local label="$1" re="$2" hits
  hits="$(files | xargs -0 grep -InE "$re" 2>/dev/null | sed -E 's/^([^:]+:[0-9]+):.*/\1/')"
  if [ -n "$hits" ]; then
    echo "ERROR: $label found at (values withheld):"
    echo "$hits" | sed 's/^/        /'
    errors=$((errors + 1))
  fi
}

scan "a credential-shaped string" '(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})'
scan "an absolute home path" '(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+)'
scan "a path under a home-directory dot folder" '(~|\$HOME)/\.[A-Za-z0-9_-]+/'
scan "an MCP server tool name" 'mcp__[A-Za-z0-9_-]+__'

# Warning only: commits authored with a personal or work address instead of the
# GitHub noreply address publish that address in the history.
if [ -n "${1:-}" ] && git rev-parse --verify -q "$1" >/dev/null; then
  bad="$(git log --format='%h %ae' "$1"..HEAD | grep -vE '@users\.noreply\.github\.com$' || true)"
  if [ -n "$bad" ]; then
    echo "WARN:  commits not authored with a GitHub noreply address (their email becomes public):"
    echo "$bad" | awk '{print "        " $1}'
    echo "::warning::Some commits use a non-noreply author email, which becomes public history."
  fi
fi

if [ "$errors" -gt 0 ]; then
  echo "$errors check(s) failed"
  exit 1
fi
echo "ok: no credentials, home paths, or MCP tool names in tracked files"
