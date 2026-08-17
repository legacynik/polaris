#!/usr/bin/env bash
# checkpoint.sh — the deterministic half of /update.
#
# The skill body should carry judgment only; everything mechanical lives here so it
# costs zero context and cannot be skipped by a model that is in a hurry.
#
#   prepare       resolve root/login/branch/paths, print them, run the hygiene sweep
#   harvest-done  move the scratch watermark forward
#   commit [path] land the session log (delegates to session_commit.sh)
#   verify        fail loudly if a step was skipped
#
# Never exits non-zero on a missing optional input — it says what is missing and stops,
# because a checkpoint tool that breaks a session is worse than no checkpoint tool.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- resolution ---------------------------------------------------------------
# One home: every write lands in the MAIN worktree, whatever tree this panel sits in.
# Per-worktree copies diverge on N branches and lose data at merge.
resolve() {
  MAIN_WT="$(git worktree list --porcelain 2>/dev/null | head -1 | sed 's|^worktree ||')"
  [ -n "${MAIN_WT:-}" ] || { echo "checkpoint: not a git repo" >&2; exit 2; }
  ROOT="$MAIN_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$MAIN_WT"
  LOGIN="$(git config --local --get polaris.login 2>/dev/null || gh api user --jq .login 2>/dev/null)"
  [ -n "${LOGIN:-}" ] || { echo "checkpoint: cannot resolve login (gh auth?)" >&2; exit 2; }
  BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  WT="$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")"
  SESSION_LOG="$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md"
  SCRATCH="$(ls -t "$ROOT/team/$LOGIN/sessions/scratch/"*.md "$ROOT/sessions/scratch/$LOGIN/"*.md 2>/dev/null | head -1)"
}

# Watermark = byte offset of the last harvest. Reading the delta keeps the checkpoint
# cheap; re-reading a 30KB scratch on every /update turns a checkpoint into a session eater.
harvest_from() {
  [ -n "${SCRATCH:-}" ] && [ -f "$SCRATCH" ] || { echo 0; return; }
  local mark
  mark=$(grep -n '<!-- harvested' "$SCRATCH" 2>/dev/null | tail -1 | cut -d: -f1)
  [ -n "$mark" ] && echo "$mark" || echo 0
}

cmd_prepare() {
  resolve
  cat <<EOF
ROOT=$ROOT
LOGIN=$LOGIN
BRANCH=$BRANCH
WT=$WT
SESSION_LOG=$SESSION_LOG
SCRATCH=${SCRATCH:-none}
HARVEST_FROM_LINE=$(harvest_from)
EOF
  # Hygiene: report, never fix silently. A sweep that moves files without saying so
  # is how a "cleanup" eats someone else's handoff.
  local strays
  strays=$(ls "$ROOT"/sessions/*.md 2>/dev/null | wc -l | tr -d ' ')
  [ "$strays" != "0" ] && echo "HYGIENE=legacy session logs at \$ROOT/sessions/: $strays (migrate deliberately, check readers first)"
  [ -n "${SCRATCH:-}" ] || echo "HYGIENE=no scratch found for this session — harvest step is a no-op"
  due_report
  return 0
}

# --- recurring work, surfaced by the ritual that actually runs -----------------
# `state/due.md`: one line per recurring job — `YYYY-MM-DD · name · every Nd`.
# Printed here because /update is run daily and /end often is not: a reminder that
# rides the ritual nobody skips is a reminder that fires. Marked done via `due-done`,
# which rewrites the date to today+N — the schedule advances itself, so a job can
# never silently stop being due.
DUE_FILE() { echo "$ROOT/state/due.md"; }

due_report() {
  local f; f="$(DUE_FILE)"; [ -f "$f" ] || return 0
  local today; today="$(date +%F)"
  while IFS= read -r line; do
    case "$line" in ''|'#'*) continue ;; esac
    local when name
    when="$(echo "$line" | cut -d'·' -f1 | tr -d ' ')"
    name="$(echo "$line" | cut -d'·' -f2 | sed 's/^ *//;s/ *$//')"
    [ -n "$when" ] && [ "$when" \< "$today" -o "$when" = "$today" ] && echo "DUE=$name (scaduto dal $when) — esegui, poi: checkpoint.sh due-done $name"
  done < "$f"
  return 0
}

cmd_due_done() {
  resolve
  local name="${1:-}"; [ -n "$name" ] || { echo "usage: checkpoint.sh due-done <name>" >&2; return 64; }
  local f; f="$(DUE_FILE)"; [ -f "$f" ] || { echo "checkpoint: no $f"; return 1; }
  local every next
  every="$(grep "· *$name *·" "$f" | head -1 | sed 's/.*every *\([0-9]*\)d.*/\1/')"
  [ -n "$every" ] || { echo "checkpoint: '$name' not found in $f" >&2; return 1; }
  next="$(date -v +"${every}"d +%F 2>/dev/null || date -d "+${every} days" +%F)"
  # rewrite only that line's date; every other job keeps its own schedule
  awk -v n="$name" -v d="$next" -F'·' 'BEGIN{OFS="·"} $2 ~ ("^ *"n" *$") {$1=d" "} {print}' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  echo "checkpoint: $name → prossima $next"
}

cmd_harvest_done() {
  resolve
  [ -n "${SCRATCH:-}" ] && [ -f "$SCRATCH" ] || { echo "checkpoint: no scratch, nothing to mark"; return 0; }
  printf '\n<!-- harvested: %s -->\n' "$(date '+%F %H:%M')" >> "$SCRATCH"
  echo "checkpoint: watermark moved in $SCRATCH"
}

cmd_commit() {
  resolve
  local target="${1:-$SESSION_LOG}"
  local sc="$HERE/session_commit.sh"
  [ -x "$sc" ] || { echo "checkpoint: session_commit.sh missing at $sc — commit by hand, pathspec-only" >&2; return 1; }
  ( cd "$MAIN_WT" && "$sc" "${target#$MAIN_WT/}" )
}

# verify exists because a step that lives only in prose eventually gets skipped —
# including by whoever wrote the prose. Observed 2026-08-08: the author of the harvest
# step skipped it on the same day he added it.
cmd_verify() {
  resolve
  local fail=0 today
  today="$(date +%F)"

  if [ ! -f "$SESSION_LOG" ]; then
    echo "FAIL: no session log at $SESSION_LOG"; fail=1
  elif ! grep -q "^## " "$SESSION_LOG"; then
    echo "FAIL: session log has no checkpoint entry"; fail=1
  else
    local last
    last=$(grep "^## " "$SESSION_LOG" | tail -1)
    case "$last" in
      *"—"*) : ;;                      # titled entry, as the format requires
      *) echo "WARN: last entry has no title — '$last'"; ;;
    esac
    grep -q "Key context" "$SESSION_LOG" || echo "WARN: no Key context today — decisions, findings and your own errors have nowhere else to live"
    grep -q "^- Files" "$SESSION_LOG"   || echo "WARN: no Files field — nothing links this session back to the code"
  fi

  if [ -n "${SCRATCH:-}" ] && [ -f "$SCRATCH" ]; then
    grep -q "harvested: $today" "$SCRATCH" || { echo "FAIL: scratch not harvested today (run harvest-done)"; fail=1; }
  fi

  # current.md is the open-items ledger (v0.8.1: nothing open is ever lost). A checkpoint
  # that leaves it older than the session log strands every open lane on panel memory.
  # Restored 2026-08-17 — dropped without a changelog line in the v2.0.0 rewrite (498ed70).
  local CUR="$ROOT/state/current.md"
  if [ -f "$CUR" ] && [ -f "$SESSION_LOG" ] && [ "$CUR" -ot "$SESSION_LOG" ]; then
    echo "FAIL: state/current.md predates today's session log — reconcile it (Updated: line + Open add-and-flag, never close another owner's line)"; fail=1
  fi

  [ "$fail" = "0" ] && echo "checkpoint: verified"
  return "$fail"
}

case "${1:-}" in
  prepare)      cmd_prepare ;;
  harvest-done) cmd_harvest_done ;;
  commit)       shift; cmd_commit "${1:-}" ;;
  due-done)     shift; cmd_due_done "${1:-}" ;;
  verify)       cmd_verify ;;
  *) echo "usage: checkpoint.sh {prepare|due-done <name>|harvest-done|commit [path]|verify}" >&2; exit 64 ;;
esac
