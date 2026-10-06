#!/usr/bin/env bash
# Preflight for a handler: is the skills repo holding the core on the expected
# branch and up to date with its remote? Read-only except for `git fetch`, which
# only updates remote-tracking refs. Never switches, pulls, stashes, or resets.
#
# Usage: preflight.sh <core-dir> <branch> <remote>
# Exit:  0 = ok to run the skill, 1 = pause and tell the user (reasons printed)
#
# Once per request: one request can run several handlers (a skill that chains to
# another, or parallel subagents), and each runs this script. A passing result
# is remembered per repo+branch+remote for PREFLIGHT_TTL seconds (default 600,
# 0 turns it off), so only the first run fetches; the rest print "PREFLIGHT: ok"
# plus a "cached" note. Concurrent runs wait for the first one instead of all
# fetching. A pause is never remembered, and the memory is dropped if HEAD moves.
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

ttl="${PREFLIGHT_TTL:-600}"
case "$ttl" in ''|*[!0-9]*) ttl=600 ;; esac
head_sha="$(git -C "$root" rev-parse HEAD)"
state_dir="${XDG_CACHE_HOME:-$HOME/.cache}/skill-preflight"
key="$(printf '%s\n%s\n%s\n' "$root" "$branch" "$remote" | shasum | cut -c1-16)"
stamp="$state_dir/$key.ok"
lock="$state_dir/$key.lock"
cached=0
ahead=0
behind=0

# A stamp is "<epoch> <head> <ahead> <behind>"; it counts only while fresh and HEAD is unchanged.
read_stamp() {
  [ "$ttl" -gt 0 ] && [ -f "$stamp" ] || return 1
  local t h a b
  read -r t h a b < "$stamp" 2>/dev/null || return 1
  [ -n "$t" ] && [ "$h" = "$head_sha" ] && [ $(( $(date +%s) - t )) -lt "$ttl" ] || return 1
  ahead="$a"; behind="$b"; cached=1
}

if [ "$ttl" -gt 0 ]; then
  mkdir -p "$state_dir" 2>/dev/null && chmod 700 "$state_dir" 2>/dev/null
  read_stamp || {
    # Take the lock so parallel runs wait for the first one rather than all fetching.
    waited=0
    have_lock=0
    until mkdir "$lock" 2>/dev/null && have_lock=1; do
      # A lock older than the fetch limit belongs to a dead run; clear it.
      if [ -d "$lock" ] && [ -n "$(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then rmdir "$lock" 2>/dev/null; continue; fi
      [ "$waited" -lt 45 ] || break
      sleep 1; waited=$((waited + 1))
      read_stamp && break
    done
    if [ "$have_lock" -eq 1 ]; then
      trap 'rmdir "$lock" 2>/dev/null' EXIT
      read_stamp || true  # the previous holder may have just finished
    fi
  }
fi

if [ "$cached" -eq 0 ]; then
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

  if [ "$ttl" -gt 0 ] && [ -d "$state_dir" ]; then
    if [ "$behind" -eq 0 ]; then
      printf '%s %s %s %s\n' "$(date +%s)" "$head_sha" "$ahead" "$behind" > "$stamp" 2>/dev/null
    else
      rm -f "$stamp" 2>/dev/null
    fi
  fi
else
  notes+=("verified moments ago by another run in this request; fetch skipped (PREFLIGHT_TTL=${ttl}s)")
fi

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
