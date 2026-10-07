#!/usr/bin/env bash
# Warm the preflight memory so handlers find a fresh "ok" and never wait on the
# network. Meant for a session-start hook; returns immediately, prints nothing,
# and does the checks in a detached background process.
#
# Usage: preflight-warm.sh [repo-dir ...]
#   With no arguments, warms every sibling "*-ai-skills" repo of this one
#   (sre-ai-skills, secops-ai-skills, ...) on branch main of remote origin.
# Honors the same PREFLIGHT_* environment as preflight.sh.
set -u

here="$(cd "$(dirname "$0")" && pwd -P)"
preflight="$here/preflight.sh"
self_repo="$(git -C "$here" rev-parse --show-toplevel 2>/dev/null || true)"

repos=("$@")
if [ "${#repos[@]}" -eq 0 ] && [ -n "$self_repo" ]; then
  for d in "$(dirname "$self_repo")"/*-ai-skills; do
    [ -d "$d/.git" ] && repos+=("$d")
  done
fi

[ "${#repos[@]}" -gt 0 ] || exit 0

(
  for r in "${repos[@]}"; do
    bash "$preflight" "$r" main origin >/dev/null 2>&1
  done
) >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
