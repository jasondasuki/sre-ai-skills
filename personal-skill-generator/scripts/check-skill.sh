#!/usr/bin/env bash
# Check a handler + core skill pair for consistency and leaks.
# Usage: check-skill.sh <core-dir> <handler-dir>
# Exit status: 0 when no errors (warnings allowed), 1 when any error.
set -u

core="${1:?usage: check-skill.sh <core-dir> <handler-dir>}"
handler="${2:?usage: check-skill.sh <core-dir> <handler-dir>}"
core="${core%/}"
handler="${handler%/}"

errors=0
err()  { echo "ERROR: $*"; errors=$((errors + 1)); }
warn() { echo "WARN:  $*"; }
ok()   { echo "ok:    $*"; }

# frontmatter <file>: print the lines between the first pair of --- markers
frontmatter() {
  awk 'NR==1 && /^---[[:space:]]*$/ {f=1; next} f && /^---[[:space:]]*$/ {exit} f' "$1"
}
# fm_value <file> <key>: value of a single-line frontmatter key
fm_value() {
  frontmatter "$1" | sed -n "s/^$2:[[:space:]]*//p" | head -n1
}
has_key() {
  frontmatter "$1" | grep -qE "^$2:"
}
# table_value <file> <VAR>: the Value column of a "| `VAR` | value | ..." row
table_value() {
  awk -F'|' -v k="$2" '
    { name=$2; gsub(/[ `]/, "", name) }
    name == k { v=$3; sub(/^[ ]+/, "", v); sub(/[ ]+$/, "", v); gsub(/`/, "", v); print v; exit }
  ' "$1"
}

core_md="$core/SKILL.md"
handler_md="$handler/SKILL.md"

[ -f "$core_md" ]    || err "core file missing: $core_md"
[ -f "$handler_md" ] || err "handler file missing: $handler_md"
[ "$errors" -eq 0 ] || { echo "$errors error(s)"; exit 1; }

name="$(basename "$core")"

# ---- frontmatter -----------------------------------------------------------
for k in name description; do
  has_key "$core_md" "$k" || err "core frontmatter lacks '$k'"
done
for k in model effort; do
  has_key "$core_md" "$k" && err "core frontmatter has '$k' - machine values belong in the handler"
done
for k in name description model effort; do
  has_key "$handler_md" "$k" || err "handler frontmatter lacks '$k'"
done

[ "$(fm_value "$core_md" name)" = "$name" ] || err "core name does not match its directory '$name'"
[ "$(fm_value "$handler_md" name)" = "$name" ] || err "handler name does not match '$name'"
[ "$(basename "$handler")" = "$name" ] || err "handler directory '$(basename "$handler")' does not match core directory '$name'"

cd_desc="$(fm_value "$core_md" description)"
hd_desc="$(fm_value "$handler_md" description)"
[ "$cd_desc" = "$hd_desc" ] || err "description differs between core and handler"

# ---- machine-specific literals and secrets in the core ---------------------
# Everything under the core except this checker (it holds the patterns).
scan_files() {
  find "$core" -type f ! -path "$core/scripts/check-skill.sh" ! -path "*/.git/*" -print
}
scan() { # scan <label> <regex>
  local label="$1" re="$2" hits
  hits="$(scan_files | xargs grep -InE "$re" 2>/dev/null | cut -c1-160)"
  if [ -n "$hits" ]; then
    err "core contains $label (use a handler variable instead):"
    echo "$hits" | sed 's/^/        /'
  fi
}
scan "an absolute home path" '(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+)'
scan "a path under a home-directory dot folder" '(~|\$HOME)/\.[A-Za-z0-9_-]+/'
scan "an MCP server tool name" 'mcp__[A-Za-z0-9_-]+__'

# A value the handler defines must never appear literally in the core. This
# catches model IDs, paths, and identifiers without naming any vendor.
while IFS='|' read -r _ vname vval _; do
  vname="$(echo "$vname" | tr -d '` ')"
  case "$vname" in ""|SKILL_NAME|EFFORT|CORE_BRANCH|CORE_REMOTE|Variable|Name|---*) continue ;; esac
  vval="$(echo "$vval" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/`//g')"
  [ "${#vval}" -ge 6 ] || continue
  case "$vval" in *" "*) continue ;; esac   # prose rows are not literal values
  hits="$(scan_files | xargs grep -InF -- "$vval" 2>/dev/null | cut -c1-160)"
  if [ -n "$hits" ]; then
    err "core hardcodes the value of $vname (use the placeholder instead):"
    echo "$hits" | sed 's/^/        /'
  fi
done < <(grep -E '^\| `[A-Z][A-Z0-9_]*`' "$handler_md")

secret_re='(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})'
secret_hits="$(scan_files | xargs grep -InE "$secret_re" 2>/dev/null | sed -E 's/:[^:]*$/: <credential-shaped string redacted>/')"
if [ -n "$secret_hits" ]; then
  err "core contains credential-shaped strings (locations only, values withheld):"
  echo "$secret_hits" | sed 's/^/        /'
fi

# ---- placeholders ----------------------------------------------------------
used="$(find "$core" -type f -name '*.md' ! -path "$core/templates/*" -print0 \
        | xargs -0 grep -ohE '\{\{[A-Z][A-Z0-9_]*\}\}' 2>/dev/null \
        | tr -d '{}' | sort -u)"
defined="$(grep -oE '^\| `[A-Z][A-Z0-9_]*`' "$handler_md" | tr -d '|` ' | sort -u)"

for v in $used; do
  echo "$defined" | grep -qx "$v" || err "core uses {{$v}} but the handler has no row for it"
done
for v in $defined; do
  case "$v" in SKILL_NAME|CORE_DIR|CORE_BRANCH|CORE_REMOTE|PREFLIGHT_SCRIPT|MODEL|EFFORT|SUBAGENT_MODEL|WORKDIR|OUTPUT_DIR) continue ;; esac
  echo "$used" | grep -qx "$v" || warn "handler defines $v but the core never uses it"
done

# ---- handler consistency ---------------------------------------------------
if grep -qE '<<[A-Z_]+>>' "$handler_md"; then
  err "handler still has unfilled template tokens:"
  grep -nE '<<[A-Z_]+>>' "$handler_md" | sed 's/^/        /'
fi

for pair in model:MODEL effort:EFFORT; do
  key="${pair%%:*}"; var="${pair##*:}"
  fmv="$(fm_value "$handler_md" "$key")"
  tv="$(table_value "$handler_md" "$var")"
  [ -n "$tv" ] || { err "handler table has no $var row"; continue; }
  [ "$fmv" = "$tv" ] || err "handler $key '$fmv' differs from its $var row '$tv'"
done

core_dir_val="$(table_value "$handler_md" CORE_DIR)"
if [ -z "$core_dir_val" ]; then
  err "handler table has no CORE_DIR row"
else
  core_abs="$(cd "$core" && pwd -P)"
  val_abs="$(cd "$core_dir_val" 2>/dev/null && pwd -P || true)"
  [ -n "$val_abs" ] || err "handler CORE_DIR '$core_dir_val' does not exist"
  [ -z "$val_abs" ] || [ "$val_abs" = "$core_abs" ] || err "handler CORE_DIR points to '$val_abs', expected '$core_abs'"
fi

# preflight: every handler must gate on branch and freshness before running
for v in CORE_BRANCH CORE_REMOTE PREFLIGHT_SCRIPT; do
  [ -n "$(table_value "$handler_md" $v)" ] || err "handler table has no $v row (preflight is mandatory)"
done
pf="$(table_value "$handler_md" PREFLIGHT_SCRIPT)"
if [ -n "$pf" ]; then
  [ -f "$pf" ] || err "handler PREFLIGHT_SCRIPT '$pf' does not exist"
  [ "$(grep -c 'PREFLIGHT_SCRIPT' "$handler_md")" -ge 2 ] || err "handler has the PREFLIGHT_SCRIPT row but no preflight step in 'How to run'"
  grep -q 'PREFLIGHT: pause' "$handler_md" || err "handler's preflight step does not say what to do on 'PREFLIGHT: pause'"
fi

[ -n "$(table_value "$handler_md" SUBAGENT_MODEL)" ] || warn "handler has no SUBAGENT_MODEL row (standard variable)"

workdir_val="$(table_value "$handler_md" WORKDIR)"
if [ -z "$workdir_val" ]; then
  err "handler table has no WORKDIR row"
elif [ ! -d "$workdir_val" ]; then
  warn "handler WORKDIR '$workdir_val' does not exist yet"
fi

# ---- secret hygiene in the handler directory -------------------------------
loose="$(find "$handler" -type f \( -name '*.env' -o -name '.env*' -o -name '*secret*' -o -name '*.key' -o -name '*.pem' \) \
         \( -perm -g=r -o -perm -o=r -o -perm -g=w -o -perm -o=w \) -print 2>/dev/null)"
if [ -n "$loose" ]; then
  err "private-looking files readable by others (chmod 600):"
  echo "$loose" | sed 's/^/        /'
fi
secret_hits_handler="$(grep -InE "$secret_re" "$handler_md" 2>/dev/null | sed -E 's/:[^:]*$/: <credential-shaped string redacted>/')"
if [ -n "$secret_hits_handler" ]; then
  err "handler contains credential-shaped strings (values withheld):"
  echo "$secret_hits_handler" | sed 's/^/        /'
fi

# ---- size ------------------------------------------------------------------
core_lines="$(wc -l < "$core_md" | tr -d ' ')"
[ "$core_lines" -le 500 ] || warn "core SKILL.md is $core_lines lines; move bulk into references/"

echo
if [ "$errors" -eq 0 ]; then
  ok "$name: core and handler are consistent"
  exit 0
fi
echo "$errors error(s) in $name"
exit 1
