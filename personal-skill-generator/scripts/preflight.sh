#!/usr/bin/env bash
# Preflight for a handler: is the skills repo holding the core on the expected
# branch and up to date with its remote? Read-only except for `git fetch`, which
# only updates remote-tracking refs. Never switches, pulls, stashes, or resets.
#
# Usage: preflight.sh <core-dir> <branch> <remote>
# Exit:  0 = ok to run the skill, 1 = pause and tell the user (reasons printed)
set -u

core="${1:?usage: preflight.sh <core-dir> <branch> <remote>}"
branch="${2:?usage: preflight.sh <core-dir> <branch> <remote>}"
remote="${3:?usage: preflight.sh <core-dir> <branch> <remote>}"

problems=()
notes=()

pause() {
  echo "PREFLIGHT: pause"
  [ -n "${root:-}" ] && echo "repo:      $root"
  [ -n "${current:-}" ] && echo "branch:    $current (expected $branch)"
  [ -n "${behind:-}" ] && echo "position:  behind $remote/$branch by $behind, ahead by ${ahead:-0}"
  echo "problems:"
  for p in "${problems[@]}"; do echo "  - $p"; done
  if [ "${#notes[@]}" -gt 0 ]; then
    echo "notes:"
    for n in "${notes[@]}"; do echo "  - $n"; done
  fi
  if [ -n "${root:-}" ]; then
    echo "to fix (your call, nothing was changed):"
    echo "  git -C \"$root\" switch $branch"
    echo "  git -C \"$root\" pull --ff-only $remote $branch"
    echo "  (commit or stash local changes first if the switch complains)"
  fi
  exit 1
}

# Run a command with a wall-clock limit (macOS has no `timeout`).
run_with_timeout() {
  local secs="$1"; shift
  "$@" &
  local pid=$!
  ( sleep "$secs"; kill "$pid" 2>/dev/null ) &
  local watcher=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  kill "$watcher" 2>/dev/null
  wait "$watcher" 2>/dev/null
  return $rc
}

root="$(git -C "$core" rev-parse --show-toplevel 2>/dev/null)" || {
  problems+=("'$core' is not inside a git repository, so freshness cannot be verified")
  pause
}

if ! git -C "$root" rev-parse --verify --quiet HEAD >/dev/null; then
  problems+=("the repository has no commits yet, so there is nothing to compare with $remote/$branch")
  pause
fi

current="$(git -C "$root" symbolic-ref --quiet --short HEAD 2>/dev/null || echo "(detached HEAD)")"
[ "$current" = "$branch" ] || problems+=("checked out on '$current', not '$branch'")

if ! git -C "$root" remote get-url "$remote" >/dev/null 2>&1; then
  problems+=("no remote named '$remote' is configured, so 'latest' cannot be verified")
  pause
fi

# Fetch just the one branch, never prompting and never hanging.
fetch_err="$(GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10" \
  run_with_timeout 30 git -C "$root" -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15 \
  fetch --quiet "$remote" "$branch" 2>&1)"
fetch_rc=$?
if [ "$fetch_rc" -ne 0 ]; then
  problems+=("could not fetch $remote/$branch (exit $fetch_rc), so 'latest' cannot be verified: $(echo "$fetch_err" | head -n1 | cut -c1-140)")
  pause
fi

ref="refs/remotes/$remote/$branch"
if ! git -C "$root" rev-parse --verify --quiet "$ref" >/dev/null; then
  problems+=("$remote has no branch '$branch'")
  pause
fi

counts="$(git -C "$root" rev-list --left-right --count "HEAD...$ref")"
ahead="$(echo "$counts" | awk '{print $1}')"
behind="$(echo "$counts" | awk '{print $2}')"

[ "$behind" -eq 0 ] || problems+=("$behind commit(s) behind $remote/$branch; the checkout is not the latest")
[ "$ahead" -eq 0 ] || notes+=("$ahead local commit(s) not pushed to $remote/$branch")

dirty="$(git -C "$root" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
[ "$dirty" -eq 0 ] || notes+=("$dirty uncommitted change(s) in the working tree")

if [ "${#problems[@]}" -gt 0 ]; then
  pause
fi

echo "PREFLIGHT: ok"
echo "repo:      $root"
echo "branch:    $current, up to date with $remote/$branch (ahead $ahead, behind $behind)"
for n in "${notes[@]+"${notes[@]}"}"; do [ -n "$n" ] && echo "note:      $n"; done
exit 0
