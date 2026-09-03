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
  cockpit
  WEEKLY="$ROOT/team/$LOGIN/weeks/$(date +%G-W%V).md"
  SCRATCH="$(ls -t "$ROOT/team/$LOGIN/sessions/scratch/"*.md "$ROOT/sessions/scratch/$LOGIN/"*.md 2>/dev/null | head -1)"
}

# THE cockpit of this repo — one per repo, never one per worktree. The #212 resolver owns
# the rule where the repo carries it; the same rule inline where it does not, because the
# package ships to repos that have no vault scripts. A cwd-relative state/current.md written
# from a worktree is gitignored there and never comes back: 4 were found stranded in one repo.
cockpit() {
  CURRENT="$(python3 "$ROOT/scripts/state_home.py" path 2>/dev/null)"
  [ -n "${CURRENT:-}" ] || CURRENT="$ROOT/team/$LOGIN/current.md"
  [ -f "$CURRENT" ] || CURRENT="$ROOT/state/current.md"
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
CURRENT=$CURRENT
WEEKLY=$([ -f "$WEEKLY" ] && echo "$WEEKLY" || echo none)
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

# The first harvest of the day used to read the scratch from offset 0. On a multi-panel machine
# that file is SHARED: measured 146 lines read, almost all of them another panel's flow
# (polaris-os#89). The cap is on the FOREIGN prefix, never on position: every line carrying this
# session's id is emitted wherever it sits, and the head is trimmed to fit what is left of the cap.
# A cap applied by position would drop exactly the own-id line that arrived last.
cmd_harvest_slice() {
  resolve
  local sid="${1:-${POLARIS_SID:-}}" from cap
  [ -n "${SCRATCH:-}" ] && [ -f "$SCRATCH" ] || { echo "checkpoint: no scratch, nothing to read"; return 0; }
  from="$(harvest_from)"; cap="${HARVEST_CAP:-40}"
  awk -v from="$from" -v sid="$sid" -v cap="$cap" '
    NR > from { line[++n] = $0; if (sid != "" && index($0, sid)) { own[n] = 1; o++ } }
    END { head = cap - o; if (head < 0) head = 0
          for (i = 1; i <= n; i++) if (own[i] || i <= head) print line[i] }' "$SCRATCH"
}

cmd_harvest_done() {
  resolve
  [ -n "${SCRATCH:-}" ] && [ -f "$SCRATCH" ] || { echo "checkpoint: no scratch, nothing to mark"; return 0; }
  printf '\n<!-- harvested: %s -->\n' "$(date '+%F %H:%M')" >> "$SCRATCH"
  echo "checkpoint: watermark moved in $SCRATCH"
}

cmd_commit() {
  resolve
  [ $# -gt 0 ] || set -- "$SESSION_LOG"
  local sc="$HERE/session_commit.sh"
  [ -x "$sc" ] || { echo "checkpoint: session_commit.sh missing at $sc — commit by hand, pathspec-only" >&2; return 1; }
  local rel=(); local p
  for p in "$@"; do rel+=("${p#$MAIN_WT/}"); done
  ( cd "$MAIN_WT" && "$sc" "${rel[@]}" )   # session_commit takes N paths; ticked weekly plan rides along
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
  local CUR="$CURRENT"
  if [ -f "$CUR" ] && [ -f "$SESSION_LOG" ] && [ "$CUR" -ot "$SESSION_LOG" ]; then
    echo "FAIL: $CUR predates today's session log — reconcile it (Updated: line + Open add-and-flag, never close another owner's line)"; fail=1
  fi

  # State is OVERWRITTEN, never stacked: one Updated: line, the newest. The prose has
  # said so since v0.8.1 and got skipped anyway — measured 2026-08-31, with the rule
  # already written: 13 stacked lines in one repo, 5 in another, 1 only where a human
  # had pruned by hand. A rule with no gate is a wish; this is the gate.
  if [ -f "$CUR" ]; then
    local n_upd words
    n_upd=$(grep -c '^Updated:' "$CUR" 2>/dev/null) || true
    if [ "${n_upd:-0}" -gt 1 ]; then
      echo "FAIL: $CUR has $n_upd 'Updated:' lines — keep the newest and overwrite it; the history belongs to the session log"; fail=1
    fi
    # CONTENT, not mtime (polaris-os#84). An empty `touch` makes the file newer than the log and
    # walks straight through the gate above — measured as the bypass that closes this hole. So the
    # `Updated:` line must actually carry TODAY: the checkpoint's own stamp, written by
    # state_upsert.py, not a timestamp anybody can forge with one command. Per #240 that line is
    # date and owner ONLY — the checkpoint title lives in the session log and in `Recent Context`,
    # so the content asserted here is the date, not #84's original title-in-Updated form.
    # Fires only where an `Updated:` line exists: a cockpit shaped otherwise is a different case.
    if [ -f "$SESSION_LOG" ] && [ "${n_upd:-0}" = "1" ] && ! grep -q "^Updated:.*$today" "$CUR"; then
      echo "FAIL: $CUR carries '$(grep -m1 '^Updated:' "$CUR")' but this session logged today — a touch is not a checkpoint; re-run the state_upsert step"; fail=1
    fi
    # Size WARNs, never blocks. The file is frequently another panel's mid-session state,
    # and stranding that session costs more than one oversized file. /end owns the pruning.
    words=$(wc -w < "$CUR" | tr -d ' ')
    if [ "${words:-0}" -gt 1500 ]; then
      echo "WARN: $CUR is ~$(( words * 4 / 3 )) tokens (target <2000) — prune the closed threads at /end"
    fi
  fi

  # Plan tick — the OTHER undeclared drop of the v2.0.0 rewrite, restored by founder
  # verdict (polaris-os#85): plans are the roadmap. Owed ONLY when the weekly file
  # exists — absent file, zero noise; present and untouched by the checkpoint, red.
  if [ -f "$WEEKLY" ] && [ -f "$SESSION_LOG" ] && [ "$WEEKLY" -ot "$SESSION_LOG" ]; then
    echo "FAIL: weekly plan $(basename "$WEEKLY") exists but was not ticked — record progress on its outcome, then commit it with the session log"; fail=1
  fi

  [ "$fail" = "0" ] && echo "checkpoint: verified"
  return "$fail"
}

# --- selfcheck ----------------------------------------------------------------
# Adversarial fixtures for the current.md gates (polaris-os#202). Every branch the
# gate introduces gets an input that forces it — a probe that only walks the happy
# path proves the code ran, not that it works.
cmd_selfcheck() {
  local tmp pass=0 fail=0 out
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  git -C "$tmp" init -q .
  git -C "$tmp" config --local polaris.login probe
  mkdir -p "$tmp/_polaris/team/probe/sessions" "$tmp/_polaris/state"
  : > "$tmp/_polaris/config.yml"
  printf '## 10:00 — probe entry\n- Key context: x\n- Files: y\n' \
    > "$tmp/_polaris/team/probe/sessions/$(date +%F)-@probe.md"

  # $1 name · $2 current.md body ("" = no file) · $3 expected regex · $4 expected exit (0|1)
  case_() {
    local name="$1" body="$2" want="$3" wantrc="$4" rc
    if [ -z "$body" ]; then rm -f "$tmp/_polaris/state/current.md"
    else printf '%b' "$body" > "$tmp/_polaris/state/current.md"; sleep 1; touch "$tmp/_polaris/state/current.md"; fi
    out="$( cd "$tmp" && "$HERE/checkpoint.sh" verify 2>&1 )"; rc=$?
    if [ "$rc" = "$wantrc" ] && printf '%s' "$out" | grep -qE "$want"; then
      pass=$((pass+1)); echo "  ok   $name"
    else
      fail=$((fail+1)); echo "  FAIL $name (rc=$rc want=$wantrc) :: $(printf '%s' "$out" | tr '\n' '|')"
    fi
  }

  local TODAY; TODAY="$(date +%F)"
  echo "checkpoint selfcheck — current.md gates"
  case_ "stacked Updated: lines are refused" \
        "Updated: 2026-08-30 — a\nUpdated: $TODAY — b\n# Priorita\n" \
        "FAIL:.*2 'Updated:' lines" 1
  case_ "three stacked lines name the real count" \
        "Updated: a\nUpdated: b\nUpdated: c\n" \
        "FAIL:.*3 'Updated:' lines" 1
  case_ "one Updated: line passes" \
        "Updated: $TODAY — a\n# Priorita attive\n1. lane\n" \
        "checkpoint: verified" 0
  case_ "no Updated: line does not crash the gate" \
        "# Priorita attive\n1. lane\n" \
        "checkpoint: verified" 0
  case_ "'Last Updated:' mid-line is not a state line" \
        "Updated: $TODAY\nsee Last Updated: b below\n" \
        "checkpoint: verified" 0
  case_ "absent current.md is skipped, not invented" "" "checkpoint: verified" 0
  case_ "oversized file warns with its own number" \
        "Updated: $TODAY\n$(python3 -c 'print("word "*1600)')\n" \
        "WARN: .*current\.md is ~[0-9]+ tokens" 0   # the gate names the RESOLVED cockpit

  # polaris-os#84 — the two cases the content gate adds. A touch moves mtime and nothing else:
  # the first case is exactly the bypass, the second proves the gate still passes a real one.
  case_ "content gate: a stale Updated: line is refused however fresh the file is" \
        "Updated: 2026-08-30 — a\n# Priorita attive\n1. lane\n" \
        "FAIL:.*a touch is not a checkpoint" 1
  case_ "content gate: today's stamp passes" \
        "Updated: $TODAY — @probe\n# Priorita attive\n1. lane\n" \
        "checkpoint: verified" 0

  echo "selfcheck: $pass passed, $fail failed"
  [ "$fail" = "0" ]
}

case "${1:-}" in
  prepare)      cmd_prepare ;;
  harvest-slice) shift; cmd_harvest_slice "${1:-}" ;;
  harvest-done) cmd_harvest_done ;;
  commit)       shift; cmd_commit "$@" ;;
  due-done)     shift; cmd_due_done "${1:-}" ;;
  verify)       cmd_verify ;;
  --selfcheck)  cmd_selfcheck ;;
  *) echo "usage: checkpoint.sh {prepare|due-done <name>|harvest-slice [sid]|harvest-done|commit [path]|verify|--selfcheck}" >&2; exit 64 ;;
esac
