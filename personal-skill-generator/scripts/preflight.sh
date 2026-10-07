#!/usr/bin/env bash
# Preflight for a handler: is the skills repo holding the core on the expected
# branch and up to date with its remote? Read-only except for `git fetch`, which
# only updates remote-tracking refs. Never switches, pulls, stashes, or resets
# (unless PREFLIGHT_FF=1 is set, see below).
#
# Usage: preflight.sh <core-dir> <branch> <remote>
# Exit:  0 = ok to run the skill, 1 = pause and tell the user (reasons printed)
#
# Once per request: one request can run several handlers (a skill that chains to
# another, or parallel subagents), and each runs this script. A passing result
# is remembered per repo+branch+remote for PREFLIGHT_TTL seconds (default 1800,
# 0 turns it off), so only the first run checks the network; the rest print a
# one-line "PREFLIGHT: ok (cached ...)". Concurrent runs wait for the first one
# instead of all fetching. A pause is never remembered, and the memory is dropped
# if HEAD moves. `preflight-warm.sh` fills the memory ahead of time.
#
# The network check is one `git ls-remote` (a single cheap request); a fetch only
# happens when the remote branch moved.
#
# Optional environment (all off or defaulted, so behavior is unchanged without them):
#   PREFLIGHT_TTL=1800    seconds a passing result is trusted (0 = never cache)
#   PREFLIGHT_LAZY=1      stale-while-revalidate: a result older than the TTL but
#                         younger than PREFLIGHT_STALE (default 21600) is accepted
#                         now and re-verified by a detached background run. A
#                         "behind" found later pauses the NEXT run, not this one.
#   PREFLIGHT_FF=1        when only behind (no local commits, clean tracked files,
#                         on the expected branch), fast-forward with `merge --ff-only`
#                         instead of pausing. Never creates a merge or discards work.
set -u

core="${1:?usage: preflight.sh <core-dir> <branch> <remote>}"
branch="${2:?usage: preflight.sh <core-dir> <branch> <remote>}"
remote="${3:?usage: preflight.sh <core-dir> <branch> <remote>}"

# Never prompt, never hang on a dead network.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5"

problems=()
notes=()
tmp=""
lock=""
have_lock=0

cleanup() {
  [ -n "$tmp" ] && rm -f "$tmp" 2>/dev/null
  [ "$have_lock" -eq 1 ] && rmdir "$lock" 2>/dev/null
  return 0
}
trap cleanup EXIT

pause() {
  echo "PREFLIGHT: pause"
  [ -n "${root:-}" ] && echo "repo:      $root"
  [ -n "${current:-}" ] && echo "branch:    $current (expected $branch)"
  [ -n "${behind:-}" ] && [ "${behind:-0}" -gt 0 ] && echo "position:  behind $remote/$branch by $behind, ahead by ${ahead:-0}"
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
    echo "  or set PREFLIGHT_FF=1 to let this check fast-forward a clean checkout itself"
  fi
  exit 1
}

# Run a command with a wall-clock limit, output to a file (macOS has no `timeout`).
# The output goes to a file, never a pipe, so the watcher cannot hold a caller's
# command substitution open until its sleep ends.
run_with_timeout() {
  local secs="$1" out="$2"; shift 2
  if command -v timeout >/dev/null 2>&1; then timeout "$secs" "$@" >"$out" 2>&1; return $?; fi
  if command -v gtimeout >/dev/null 2>&1; then gtimeout "$secs" "$@" >"$out" 2>&1; return $?; fi
  "$@" >"$out" 2>&1 &
  local pid=$!
  ( sleep "$secs"; kill "$pid" 2>/dev/null ) >/dev/null 2>&1 &
  local watcher=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  pkill -P "$watcher" 2>/dev/null
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

num() { case "$1" in ''|*[!0-9]*) echo "$2" ;; *) echo "$1" ;; esac; }
ttl="$(num "${PREFLIGHT_TTL:-1800}" 1800)"
stale_max="$(num "${PREFLIGHT_STALE:-21600}" 21600)"
lazy="${PREFLIGHT_LAZY:-0}"
ff="${PREFLIGHT_FF:-0}"
head_sha="$(git -C "$root" rev-parse HEAD)"
state_dir="${XDG_CACHE_HOME:-$HOME/.cache}/skill-preflight"
key="$(printf '%s\n%s\n%s\n' "$root" "$branch" "$remote" | shasum | cut -c1-16)"
stamp="$state_dir/$key.ok"
lock="$state_dir/$key.lock"
cached=0
age=0
ahead=0
behind=0

# A stamp is "<epoch> <head> <ahead> <behind>"; it counts only while younger than
# $1 seconds and HEAD is unchanged.
read_stamp() {
  local max="$1"
  [ "$ttl" -gt 0 ] && [ -f "$stamp" ] || return 1
  local t h a b
  read -r t h a b < "$stamp" 2>/dev/null || return 1
  [ -n "$t" ] && [ "$h" = "$head_sha" ] || return 1
  local a_age=$(( $(date +%s) - t ))
  [ "$a_age" -lt "$max" ] || return 1
  ahead="$a"; behind="$b"; age="$a_age"; cached=1
}

if [ "$ttl" -gt 0 ]; then
  mkdir -p "$state_dir" 2>/dev/null && chmod 700 "$state_dir" 2>/dev/null
  read_stamp "$ttl" || {
    if [ "$lazy" = "1" ] && read_stamp "$stale_max"; then
      # Accept the older result now; re-verify off the critical path.
      notes+=("verified ${age}s ago; re-checking in the background (PREFLIGHT_LAZY=1)")
      PREFLIGHT_LAZY=0 nohup bash "$0" "$core" "$branch" "$remote" >/dev/null 2>&1 &
      disown 2>/dev/null
    else
      # Take the lock so parallel runs wait for the first one rather than all fetching.
      waited=0   # quarter-seconds
      until mkdir "$lock" 2>/dev/null && have_lock=1; do
        # A lock older than the check limit belongs to a dead run; clear it.
        if [ -d "$lock" ] && [ -n "$(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then rmdir "$lock" 2>/dev/null; continue; fi
        [ "$waited" -lt 180 ] || break
        sleep 0.25; waited=$((waited + 1))
        read_stamp "$ttl" && break
      done
      if [ "$have_lock" -eq 1 ]; then
        read_stamp "$ttl" || true  # the previous holder may have just finished
      fi
    fi
  }
fi

ref="refs/remotes/$remote/$branch"

if [ "$cached" -eq 0 ]; then
  tmp="$(mktemp "${TMPDIR:-/tmp}/preflight.XXXXXX")"

  # One cheap request: where is the remote branch now?
  if ! run_with_timeout 15 "$tmp" git -C "$root" ls-remote --heads "$remote" "refs/heads/$branch"; then
    problems+=("could not reach $remote to check $branch, so 'latest' cannot be verified: $(head -n1 "$tmp" | cut -c1-140)")
    pause
  fi
  remote_sha="$(awk 'NR==1{print $1}' "$tmp")"
  if [ -z "$remote_sha" ]; then
    problems+=("$remote has no branch '$branch'")
    pause
  fi

  # Fetch only when the remote branch moved past what we already track.
  local_ref_sha="$(git -C "$root" rev-parse --verify --quiet "$ref" 2>/dev/null || true)"
  if [ "$local_ref_sha" != "$remote_sha" ]; then
    if ! run_with_timeout 30 "$tmp" git -C "$root" -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15 \
        fetch --quiet "$remote" "$branch"; then
      problems+=("could not fetch $remote/$branch, so 'latest' cannot be verified: $(head -n1 "$tmp" | cut -c1-140)")
      pause
    fi
    if ! git -C "$root" rev-parse --verify --quiet "$ref" >/dev/null; then
      problems+=("$remote has no branch '$branch'")
      pause
    fi
  fi

  counts="$(git -C "$root" rev-list --left-right --count "HEAD...$ref")"
  ahead="$(echo "$counts" | awk '{print $1}')"
  behind="$(echo "$counts" | awk '{print $2}')"

  # Opt-in: catch up by fast-forward when that cannot lose or merge anything.
  if [ "$ff" = "1" ] && [ "$behind" -gt 0 ] && [ "$ahead" -eq 0 ] && [ "$current" = "$branch" ] \
      && [ -z "$(git -C "$root" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    if git -C "$root" merge --ff-only --quiet "$ref" >/dev/null 2>&1; then
      notes+=("fast-forwarded $behind commit(s) from $remote/$branch (PREFLIGHT_FF=1)")
      behind=0
      head_sha="$(git -C "$root" rev-parse HEAD)"
    fi
  fi

  if [ "$ttl" -gt 0 ] && [ -d "$state_dir" ]; then
    if [ "$behind" -eq 0 ]; then
      printf '%s %s %s %s\n' "$(date +%s)" "$head_sha" "$ahead" "$behind" > "$stamp" 2>/dev/null
    else
      rm -f "$stamp" 2>/dev/null
    fi
  fi
fi

[ "$behind" -eq 0 ] || problems+=("$behind commit(s) behind $remote/$branch; the checkout is not the latest")
[ "$ahead" -eq 0 ] || notes+=("$ahead local commit(s) not pushed to $remote/$branch")

# Tracked-file changes are what could make the core differ from what was approved.
# A fresh result gets the full count; a cached one gets the cheap yes/no.
if [ "$cached" -eq 0 ]; then
  dirty="$(git -C "$root" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  [ "$dirty" -eq 0 ] || notes+=("$dirty uncommitted change(s) in the working tree")
else
  git -C "$root" diff-index --quiet HEAD -- 2>/dev/null || notes+=("uncommitted change(s) in tracked files")
fi

if [ "${#problems[@]}" -gt 0 ]; then
  pause
fi

if [ "$cached" -eq 1 ]; then
  echo "PREFLIGHT: ok (cached, verified ${age}s ago; $current up to date with $remote/$branch)"
else
  echo "PREFLIGHT: ok"
  echo "repo:      $root"
  echo "branch:    $current, up to date with $remote/$branch (ahead $ahead, behind $behind)"
fi
for n in "${notes[@]+"${notes[@]}"}"; do [ -n "$n" ] && echo "note:      $n"; done
exit 0
