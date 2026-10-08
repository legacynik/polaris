#!/usr/bin/env bash
# checkpoint.sh — the deterministic half of /update.
#
# The skill body should carry judgment only; everything mechanical lives here so it
# costs zero context and cannot be skipped by a model that is in a hurry.
#
#   prepare       resolve root/login/branch/paths, print them, run the hygiene sweep
#   harvest-done  move the scratch watermark forward
#   reconcile     strike from the cockpit the single lines the tracker has proven done
#   open-prs      list this author's open PRs and which ones carry their reason (never refuses)
#   commit [path] land the session log (delegates to session_commit.sh)
#   verify        fail loudly if a step was skipped
#
# Never exits non-zero on a missing optional input — it says what is missing and stops,
# because a checkpoint tool that breaks a session is worse than no checkpoint tool.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- resolution ---------------------------------------------------------------
# The session log lives and commits WHERE THE PANEL RUNS: `$ROOT` is this worktree's contract, so
# the log, the handoff and the plan tick land on the branch the session actually happened on.
# Only the cockpit keeps the one-home rule — see `cockpit`, and MAIN_ROOT below.
resolve() {
  MAIN_WT="$(git worktree list --porcelain 2>/dev/null | head -1 | sed 's|^worktree ||')"
  [ -n "${MAIN_WT:-}" ] || { echo "checkpoint: not a git repo" >&2; exit 2; }
  HERE_WT="$(git rev-parse --show-toplevel 2>/dev/null)"
  MAIN_ROOT="$MAIN_WT/_polaris"; [ -f "$MAIN_ROOT/config.yml" ] || MAIN_ROOT="$MAIN_WT"
  ROOT="$HERE_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$HERE_WT"
  LOGIN="$(git config --local --get polaris.login 2>/dev/null || gh api user --jq .login 2>/dev/null)"
  [ -n "${LOGIN:-}" ] || { echo "checkpoint: cannot resolve login (gh auth?)" >&2; exit 2; }
  BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  WT="$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")"
  SESSION_LOG="$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md"
  # DB-FR-07: nothing durable may depend on `/end`. Today's handoff rides with the log.
  HANDOFF="$ROOT/team/$LOGIN/handoff/$(date +%F).md"
  cockpit
  WEEKLY="$ROOT/team/$LOGIN/weeks/$(date +%G-W%V).md"
  scratch_for "${POLARIS_SID:-}"
}

# THIS session's scratch, never the login's newest (polaris-os#536). The stop hook writes
# `<date>-<sid12>.md`, sid12 being the first twelve characters of the session uuid, one file per
# session PER DAY and per lane: a session alive across midnight owns two, and the legacy lane can
# hold a third. So the scratch is a LIST, oldest first, and every reader walks all of it.
# With an id: the files named for it, or nothing. Without one: the files of the only session that
# wrote today, or nothing — never a guess. Anything else in the lane is a note someone left
# (`2026-09-30-distill-proposal-1.md`), not a hook file, and is never read, stamped or offered.
scratch_for() {
  local sid="${1:0:12}" f name
  SCRATCH=""; SCRATCH_SID="$sid"; SCRATCH_FILES=(); SCRATCH_CANDIDATES=()
  [ -n "$sid" ] || sid="$(scratch_today | cut -c12-23 | sort -u | awk 'NR == 1 { one = $0 } END { if (NR == 1) print one }')"
  [ -n "$sid" ] && while IFS= read -r f; do
    name="${f##*/}"; [ "${name:11:12}" = "$sid" ] && SCRATCH_FILES+=("$f")
  done < <(scratch_hook_files)
  if [ ${#SCRATCH_FILES[@]} -eq 0 ]; then
    while IFS= read -r f; do [ -n "$f" ] && SCRATCH_CANDIDATES+=("$f"); done < <(scratch_today paths)
    return 0
  fi
  scratch_sort
}

# Every hook-named file of both lanes, one path per line. Pure shell: a lane holds hundreds of
# files and this runs on every command, so nothing here may fork per file.
scratch_hook_files() {
  local f name
  for f in "$MAIN_ROOT/team/$LOGIN/sessions/scratch/"*.md "$MAIN_ROOT/sessions/scratch/$LOGIN/"*.md; do
    name="${f##*/}"; name="${name%.md}"
    [[ "$name" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9a-f]{8}-[0-9a-f]{3}$ ]] && [ -f "$f" ] && printf '%s\n' "$f"
  done
  return 0
}

# The hook files MODIFIED today: names by default, full paths with `paths`. The name's date can
# be a day off the clock's (the hook stamps another zone), so only the last few days are stat-ed.
scratch_today() {
  local f name today floor; today="$(date +%F)"
  floor="$(date -v-2d +%F 2>/dev/null || date -d '2 days ago' +%F)"
  while IFS= read -r f; do
    name="${f##*/}"
    [[ "${name:0:10}" < "$floor" ]] && continue
    [ "$(date -r "$f" +%F 2>/dev/null)" = "$today" ] || continue
    if [ "${1:-}" = paths ]; then printf '%s\n' "$f"; else printf '%s\n' "$name"; fi
  done < <(scratch_hook_files)
  return 0
}

# Oldest first by FILE NAME (its date), not by mtime: the older file touched last is still older.
# SCRATCH is the newest, the one `prepare` prints and `verify` wants stamped today.
scratch_sort() {
  local f sorted=()
  while IFS= read -r f; do sorted+=("${f#*$'\t'}"); done < <(
    for f in "${SCRATCH_FILES[@]}"; do printf '%s\t%s\n' "${f##*/}" "$f"; done | sort)
  SCRATCH_FILES=("${sorted[@]}"); SCRATCH="${sorted[${#sorted[@]}-1]}"
}

# One line, said once, when no scratch could be chosen and there was something to choose from.
scratch_unchosen() {
  [ ${#SCRATCH_FILES[@]} -eq 0 ] && [ ${#SCRATCH_CANDIDATES[@]} -gt 0 ] || return 1
  local f names="" why="pass this session's id (POLARIS_SID=<id>)"
  [ -n "${SCRATCH_SID:-}" ] && why="no file is named for session ${SCRATCH_SID}"
  for f in "${SCRATCH_CANDIDATES[@]}"; do names="$names ${f##*/}"; done
  echo "checkpoint: no scratch chosen — $why; nothing read, nothing stamped; today's files:$names"
}

# A file still owes lines when something follows its last watermark that is not blank. A CRLF
# blank line, spaces and tabs are not content: counting them made `verify` fail on nothing.
scratch_pending() {
  awk -v from="$(harvest_from "$1")" '{ sub(/\r$/, "") } NR > from && NF { found = 1 } END { exit !found }' \
    "$1" 2>/dev/null
}

# THE cockpit of this repo — one per repo, never one per worktree. The #212 resolver owns
# the rule where the repo carries it; the same rule inline where it does not, because the
# package ships to repos that have no vault scripts. A cwd-relative state/current.md written
# from a worktree is gitignored there and never comes back: 4 were found stranded in one repo.
cockpit() {
  CURRENT="$(python3 "$MAIN_ROOT/scripts/state_home.py" path 2>/dev/null)"
  [ -n "${CURRENT:-}" ] || CURRENT="$MAIN_ROOT/team/$LOGIN/current.md"
  [ -f "$CURRENT" ] || CURRENT="$MAIN_ROOT/state/current.md"
}

# Watermark = byte offset of the last harvest. Reading the delta keeps the checkpoint
# cheap; re-reading a 30KB scratch on every /update turns a checkpoint into a session eater.
harvest_from() {   # [file] — the newest of the session when none is named
  local f="${1:-${SCRATCH:-}}" mark
  [ -n "$f" ] && [ -f "$f" ] || { echo 0; return; }
  # Anchored: a line that QUOTES the marker in prose is content, not a watermark.
  # -a: with a stray binary byte grep answers "Binary file matches", not a line number.
  mark=$(grep -a -n '^<!-- harvested: ' "$f" 2>/dev/null | tail -1 | cut -d: -f1)
  echo "${mark:-0}"
}

cmd_prepare() {
  resolve
  local archive_dirty
  archive_dirty="$(git -C "$HERE_WT" status --short -- "$ROOT/lessons.md" "$ROOT/decisions.md")"
  if [ -n "$archive_dirty" ]; then
    echo "ARCHIVE_DIRTY=$archive_dirty — resolve ownership before editing shared ledgers" >&2
    return 2
  fi
  cat <<EOF
ROOT=$ROOT
MAIN_WT=$MAIN_WT
LOGIN=$LOGIN
BRANCH=$BRANCH
WT=$WT
SESSION_LOG=$SESSION_LOG
HANDOFF=$HANDOFF
CURRENT=$CURRENT
WEEKLY=$([ -f "$WEEKLY" ] && echo "$WEEKLY" || echo none)
SCRATCH=${SCRATCH:-none}
HARVEST_FROM_LINE=$(harvest_from)
SCRATCH_NOTE=$(scratch_unchosen || echo none)
LOG_MERGE=$(log_merge)
EOF
  # Hygiene: report, never fix silently. A sweep that moves files without saying so
  # is how a "cleanup" eats someone else's handoff.
  local strays
  strays=$(ls "$ROOT"/sessions/*.md 2>/dev/null | wc -l | tr -d ' ')
  [ "$strays" != "0" ] && echo "HYGIENE=legacy session logs at \$ROOT/sessions/: $strays (migrate deliberately, check readers first)"
  [ -n "${SCRATCH:-}" ] || echo "HYGIENE=no scratch found for this session — harvest step is a no-op"
  spool_legacy
  due_report
  return 0
}

# Until v0.24.0 a run that could not commit copied the files into `.git/polaris-deferred` and told
# the next session to drain it. The rule now is «commit on the branch you are on», so nothing is
# ever written there again — but a repo upgraded mid-flight can still hold one. Reported by name,
# never touched: those are somebody's session entries, and moving them is not this script's call.
spool_legacy() {
  local dir n
  dir="$(git rev-parse --git-common-dir 2>/dev/null)" || return 0
  case "$dir" in /*) ;; *) dir="$(git rev-parse --show-toplevel)/$dir" ;; esac
  n=$(find "$dir/polaris-deferred" -type f 2>/dev/null | wc -l | tr -d ' ')
  [ "${n:-0}" != "0" ] && echo "SPOOL_LEGACY=$n file in $dir/polaris-deferred: portali a mano con git add, poi cancella la cartella"
  return 0
}

# --- recurring work, surfaced by the ritual that actually runs -----------------
# `state/due.md`: one line per recurring job — `YYYY-MM-DD · name · every Nd`.
# Printed here because /update is run daily and /end often is not: a reminder that
# rides the ritual nobody skips is a reminder that fires. Marked done via `due-done`,
# which rewrites the date to today+N — the schedule advances itself, so a job can
# never silently stop being due.
DUE_FILE() { echo "$MAIN_ROOT/state/due.md"; }

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

# --- open PRs (the reminder, never the wall) ----------------------------------
# «Chi apre, mergia»: una PR lasciata aperta a fine sessione va in conflitto con la lane
# dopo, e sei PR aperte insieme sullo stesso manifest sono la forma in cui il conto si
# paga tutto insieme. Quindi /end le ELENCA e dice quali portano gia' la loro ragione nel
# cockpit. Non rifiuta mai: un promemoria che blocca la chiusura e' un promemoria che
# viene aggirato (decisione founder, 2026-09-06). Ogni ramo esce 0 — anche `gh` assente.
open_prs_rows() {
  gh pr list --author @me --state open --json number,title,headRefName 2>/dev/null \
    | python3 -c 'import json,sys
try: rows = json.load(sys.stdin)
except Exception: sys.exit(1)
for p in rows: print("%s\t%s\t%s" % (p["number"], p["headRefName"], p["title"]))'
}

cmd_open_prs() {
  resolve
  local rows n=0 miss=0 num branch title
  rows="$(open_prs_rows)" || {
    echo "OPEN_PRS=unknown — gh non ha risposto: elencale a mano, /end non si ferma qui"; return 0; }
  [ -n "$rows" ] || { echo "OPEN_PRS=0 — nessuna PR aperta, niente da giustificare"; return 0; }
  while IFS=$'\t' read -r num branch title; do
    n=$((n + 1))
    if grep -qE "#$num([^0-9]|\$)" "$CURRENT" 2>/dev/null; then
      echo "OPEN_PR=#$num $branch — ragione: PRESENTE"
    else
      miss=$((miss + 1)); echo "OPEN_PR=#$num $branch — $title — ragione: MANCA"
    fi
  done <<< "$rows"
  echo "OPEN_PRS=$n · senza ragione: $miss — una riga per ciascuna in $CURRENT, poi chiudi"
  return 0
}

# The delta since each file's last watermark, whole, oldest file first. The files are this
# session's own (see scratch_for), so there is no foreign flow left to cap: the cap of polaris-os#89
# guarded a file every panel shared, and applied to a per-session file it dropped the NEWEST lines,
# which harvest-done then marked read.
cmd_harvest_slice() {
  [ -n "${1:-}" ] && POLARIS_SID="$1"
  resolve
  scratch_unchosen && return 0
  [ ${#SCRATCH_FILES[@]} -gt 0 ] || { echo "checkpoint: no scratch, nothing to read"; return 0; }
  local f
  for f in "${SCRATCH_FILES[@]}"; do
    [ -r "$f" ] || { echo "checkpoint: cannot read $f"; continue; }
    scratch_pending "$f" || continue      # only blank lines after the stamp: nothing owed
    awk -v from="$(harvest_from "$f")" 'NR > from' "$f"
  done
  return 0
}

# Every panel commits its log on the branch it sits on, so one day's file is born on several
# branches and git calls that a conflict. The built-in `union` driver keeps both sides, which is
# the only right answer for an append-only ledger. Reported, never written: the attribute is a
# tracked file of the host repo, and this script does not edit those.
log_merge() {
  local rel="${SESSION_LOG#"$HERE_WT"/}"
  if [ "$(git -C "$HERE_WT" check-attr merge -- "$rel" 2>/dev/null | sed 's/.*: //')" = union ]; then
    echo union
  else
    echo "missing — add to .gitattributes: ${rel%team/"$LOGIN"/sessions/*}team/*/sessions/*.md merge=union"
  fi
}

# The cockpit stops saying open what the tracker has proven done (polaris-os#538). Nothing is
# decided here: `state_reconcile.py` strikes single lines whose every citation is PROVEN, and
# only if they are unchanged when it writes. Abandoned work, entries with children, unreadable
# answers: all wait for `/end`. Always exit 0 — a checkpoint must not die because the tracker is down.
cmd_reconcile() {
  resolve
  local out code
  reconcile_due || return 0
  out="$(cd "$HERE_WT" && python3 "$HERE/state_reconcile.py" "$CURRENT" "$SESSION_LOG" 2>&1)"; code=$?
  case "$code" in
    0) printf '%s\n' "$out"; touch "$RECONCILE_STAMP" ;;
    3) printf '%s\n' "$out" ;;
    *) echo "checkpoint: reconcile stopped early ($(printf '%s' "$out" | tail -1 | cut -c1-120)) — anything struck is in today's log as «Reconciled out of»" ;;
  esac
  return 0
}

# Once per window for the whole repo, whichever panel asks: measured 109 seconds for 13 lanes on
# a real cockpit, and every panel checkpoints many times a day. Only a run that learned something
# opens the window; a stamp from the future (a clock that jumped) silences nothing.
reconcile_due() {
  local every="${POLARIS_RECONCILE_EVERY:-180}" age
  RECONCILE_STAMP="$(cd "$HERE_WT" && cd "$(git rev-parse --git-common-dir)" && pwd)/polaris-reconcile"
  [ "$every" -gt 0 ] 2>/dev/null && [ -f "$RECONCILE_STAMP" ] || return 0
  age=$(( ( $(date +%s) - $(date -r "$RECONCILE_STAMP" +%s) ) / 60 ))
  [ "$age" -ge 0 ] && [ "$age" -lt "$every" ] || return 0
  echo "checkpoint: reconcile skipped — done ${age} min ago (window ${every} min, POLARIS_RECONCILE_EVERY=0 forces)"
  return 1
}

# The newest file is always stamped ("move the watermark, always"); an older one only while it
# still owes lines. A stamp that could not be written is said so, never reported as moved.
cmd_harvest_done() {
  resolve
  scratch_unchosen && return 0
  [ ${#SCRATCH_FILES[@]} -gt 0 ] || { echo "checkpoint: no scratch, nothing to mark"; return 0; }
  local f
  for f in "${SCRATCH_FILES[@]}"; do
    [ "$f" = "$SCRATCH" ] || scratch_pending "$f" || continue
    if printf '\n<!-- harvested: %s -->\n' "$(date '+%F %H:%M')" >> "$f" 2>/dev/null; then
      echo "checkpoint: watermark moved in $f"
    else
      echo "checkpoint: could NOT write the watermark in $f — nothing marked there"
    fi
  done
  return 0
}

cmd_commit() {
  resolve
  # Il default porta il log E l'handoff di OGGI, se esiste: un handoff che aspetta `/end`
  # e' un handoff che muore col contesto. Uno di ieri appartiene alla sessione che lo scrisse.
  if [ $# -eq 0 ]; then
    set -- "$SESSION_LOG"
    [ -f "$HANDOFF" ] && set -- "$@" "$HANDOFF"
  fi
  local sc="$HERE/session_commit.sh"
  [ -x "$sc" ] || { echo "checkpoint: session_commit.sh missing at $sc — commit by hand, pathspec-only" >&2; return 1; }
  local rel=(); local p
  for p in "$@"; do rel+=("${p#$HERE_WT/}"); done
  ( cd "$HERE_WT" && "$sc" "${rel[@]}" )   # session_commit takes N paths; ticked weekly plan rides along
}

# verify exists because a step that lives only in prose eventually gets skipped —
# including by whoever wrote the prose. Observed 2026-08-08: the author of the harvest
# step skipped it on the same day he added it.
# `verify [<checkpoint title>]` — the title binds the run to the cockpit; see the content gate.
cmd_verify() {
  resolve
  local fail=0 today
  today="$(date +%F)"

  if [ ! -f "$SESSION_LOG" ]; then
    echo "FAIL: no session log at $SESSION_LOG"; fail=1
  elif ! grep -q "^## " "$SESSION_LOG"; then
    echo "FAIL: session log has no checkpoint entry"; fail=1
  else
    if ! git -C "$HERE_WT" ls-files --error-unmatch -- "${SESSION_LOG#"$HERE_WT"/}" >/dev/null 2>&1 \
        || ! git -C "$HERE_WT" diff --quiet HEAD -- "${SESSION_LOG#"$HERE_WT"/}"; then
      echo "FAIL: session log checkpoint is not committed at $SESSION_LOG"; fail=1
    fi
    local last
    last=$(grep "^## " "$SESSION_LOG" | tail -1)
    case "$last" in
      *"—"*) : ;;                      # titled entry, as the format requires
      *) echo "WARN: last entry has no title — '$last'"; ;;
    esac
    grep -q "Key context" "$SESSION_LOG" || echo "WARN: no Key context today — decisions, findings and your own errors have nowhere else to live"
    grep -q "^- Files" "$SESSION_LOG"   || echo "WARN: no Files field — nothing links this session back to the code"

    # Archive pointers belong to this checkpoint, not an older entry in today's shared log.
    # Check HEAD: a working-tree-only lesson disappears with the worktree.
    local entry
    entry="$(awk '/^## / { block = "" } { block = block $0 ORS } END { printf "%s", block }' "$SESSION_LOG")"
    verify_archive() {
      local tag="$1" field="$2" path="$3" refs title saved
      if printf '%s\n' "$entry" | grep -qF "#$tag" \
          || printf '%s\n' "$entry" | grep -q "^- $field:"; then
        refs="$(printf '%s\n' "$entry" | sed -n "s/^- $field: //p")"
        if [ -z "$refs" ]; then
          echo "FAIL: #$tag has no $field record pointer in this checkpoint"; fail=1; return
        fi
        saved="$(git -C "$HERE_WT" show "HEAD:${path#"$HERE_WT"/}" 2>/dev/null)" || {
          echo "FAIL: $field record is not committed at $path"; fail=1; return; }
        if ! git -C "$HERE_WT" diff --quiet HEAD -- "${path#"$HERE_WT"/}"; then
          echo "FAIL: $field record has uncommitted changes at $path"; fail=1; return
        fi
        while IFS= read -r title; do
          if ! printf '%s\n' "$saved" | awk -v t="$title" \
              'index($0, "## ") == 1 && index($0, " — " t " (") > 0 { found = 1 } END { exit !found }'; then
            echo "FAIL: $field record '$title' is not committed at $path"; fail=1
          fi
        done <<< "$refs"
      fi
    }
    verify_archive lezione Lesson "$ROOT/lessons.md"
    verify_archive decisione Decision "$ROOT/decisions.md"
  fi

  # The harvest gate reads this session's files only: today's stamp in the newest, and no older
  # one still owing lines. Without an id it cannot know which are ours, and says so.
  local f owed=0
  if [ ${#SCRATCH_FILES[@]} -gt 0 ]; then
    for f in "${SCRATCH_FILES[@]}"; do [ "$f" = "$SCRATCH" ] || ! scratch_pending "$f" || owed=1; done
    grep -a -q "^<!-- harvested: $today" "$SCRATCH" && [ "$owed" -eq 0 ] \
      || { echo "FAIL: scratch not harvested today (run harvest-done)"; fail=1; }
  else
    scratch_unchosen | sed 's/^checkpoint:/WARN: harvest not checked —/' || true
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
    # CONTENT, and bound to THIS run (polaris-os#84). An empty `touch` makes the file newer than
    # the log and walks through the freshness gate above; a `sed -i` that only re-dates `Updated:`
    # walks through a date-only gate. So the cockpit must carry today AND this contributor, and the
    # title this run wrote must be the newest entry in the append-only session log. Per #240 the
    # `Updated:` line is date and owner ONLY — the title lives in the log and in `Recent Context`,
    # which is why the title is asserted THERE and the date HERE, one fact in each place.
    if [ -f "$SESSION_LOG" ]; then
      if [ "${n_upd:-0}" = "0" ]; then
        echo "FAIL: $CUR has no 'Updated:' line but this session logged today — the checkpoint never reached the cockpit"; fail=1
      elif ! grep -qE "^Updated: *$today.*@?$LOGIN([^A-Za-z0-9_-]|\$)" "$CUR"; then
        echo "FAIL: $CUR carries '$(grep -m1 '^Updated:' "$CUR")' — expected '$today' and '@$LOGIN'; a touch is not a checkpoint, rewrite the Updated: line (step 4)"; fail=1
      fi
      # The title is optional ONLY because an older caller does not pass it; when /update passes the
      # entry it just wrote, a re-dated cockpit with no new log entry is caught here and nowhere else.
      if [ -n "${TITLE:-}" ] && ! grep "^## " "$SESSION_LOG" | tail -1 | grep -qF -- "$TITLE"; then
        echo "FAIL: the newest entry in $(basename "$SESSION_LOG") is not '$TITLE' — this run wrote no checkpoint, so nothing in the cockpit belongs to it"; fail=1
      fi
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
  git -C "$tmp" config user.email probe@example.test
  git -C "$tmp" config user.name Probe
  mkdir -p "$tmp/_polaris/team/probe/sessions" "$tmp/_polaris/state"
  : > "$tmp/_polaris/config.yml"
  printf '## 10:00 — probe entry\n- Key context: x\n- Files: y\n' \
    > "$tmp/_polaris/team/probe/sessions/$(date +%F)-@probe.md"
  git -C "$tmp" add -- "$tmp/_polaris/team/probe/sessions/$(date +%F)-@probe.md"
  git -C "$tmp" commit -qm checkpoint

  # $1 name · $2 current.md body ("" = no file) · $3 expected regex · $4 expected exit (0|1)
  case_() {
    local name="$1" body="$2" want="$3" wantrc="$4" rc
    if [ -z "$body" ]; then rm -f "$tmp/_polaris/state/current.md"
    else printf '%b' "$body" > "$tmp/_polaris/state/current.md"; sleep 1; touch "$tmp/_polaris/state/current.md"; fi
    out="$( cd "$tmp" && "$HERE/checkpoint.sh" verify "${TITLE:-}" 2>&1 )"; rc=$?
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
        "Updated: $TODAY — @probe\n# Priorita attive\n1. lane\n" \
        "checkpoint: verified" 0
  case_ "'Last Updated:' mid-line is not a state line" \
        "Updated: $TODAY — @probe\nsee Last Updated: b below\n" \
        "checkpoint: verified" 0
  case_ "absent current.md is skipped, not invented" "" "checkpoint: verified" 0
  case_ "oversized file warns with its own number" \
        "Updated: $TODAY — @probe\n$(python3 -c 'print("word "*1600)')\n" \
        "WARN: .*current\.md is ~[0-9]+ tokens" 0   # the gate names the RESOLVED cockpit

  # polaris-os#84 — the bypasses this gate exists to close, one fixture each.
  case_ "bypass 1: an empty touch on a stale cockpit" \
        "Updated: 2026-08-30 — @probe\n# Priorita attive\n1. lane\n" \
        "FAIL:.*a touch is not a checkpoint" 1
  case_ "bypass 2: a cockpit re-dated by hand, with nobody's name on it" \
        "Updated: $TODAY — a\n# Priorita attive\n1. lane\n" \
        "FAIL:.*expected .*@probe" 1
  case_ "bypass 3: no Updated: line at all, while the session logged today" \
        "# Priorita attive\n1. lane\n" \
        "FAIL:.*no 'Updated:' line" 1

  # The run binding: the title /update just wrote must be the NEWEST entry in the log.
  TITLE="probe entry" case_ "the title of this run is the newest log entry" \
        "Updated: $TODAY — @probe\n1. lane\n" "checkpoint: verified" 0
  TITLE="una cosa mai scritta" case_ "a re-dated cockpit with no checkpoint of ours is refused" \
        "Updated: $TODAY — @probe\n1. lane\n" "FAIL:.*wrote no checkpoint" 1
  # A login is matched EXACTLY: `@probeur` is a different person from `@probe`.
  case_ "a longer login that merely starts with ours does not pass" \
        "Updated: $TODAY — @probeur\n1. lane\n" "FAIL:.*expected .*@probe" 1

  echo "selfcheck: $pass passed, $fail failed"
  [ "$fail" = "0" ]
}

case "${1:-}" in
  prepare)      cmd_prepare ;;
  harvest-slice) shift; cmd_harvest_slice "${1:-}" ;;
  harvest-done) cmd_harvest_done ;;
  reconcile)    ( cmd_reconcile ) || echo "checkpoint: reconcile unavailable here — nothing removed"; exit 0 ;;
  open-prs)     cmd_open_prs ;;
  commit)       shift; cmd_commit "$@" ;;
  due-done)     shift; cmd_due_done "${1:-}" ;;
  verify)       shift; TITLE="${1:-}" cmd_verify ;;
  --selfcheck)  cmd_selfcheck ;;
  *) echo "usage: checkpoint.sh {prepare|due-done <name>|harvest-slice [sid]|harvest-done|reconcile|open-prs|commit [path]|verify [title]|--selfcheck}" >&2; exit 64 ;;
esac
