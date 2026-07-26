#!/usr/bin/env bash
# REAL test: exercise the exact lines the SKILL.md prescribes, on a real repo with a real worktree,
# simulating BOTH install paths. Adversarial: every new branch must be hit.
set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"   # the polaris/ package dir
W="$(mktemp -d)"; FAKE_HOME="$W/home"
mkdir -p "$FAKE_HOME/.agents/skills/update"
cp -R "$SRC/skills/update/scripts" "$FAKE_HOME/.agents/skills/update/scripts"   # simulate `npx skills` install

# --- a real repo with the contract layout, a feature branch, and a linked worktree
R="$W/repo"; mkdir -p "$R"; cd "$R" || exit 1
git init -q -b main; git config user.email t@t; git config user.name t; git config polaris.login legacynik
mkdir -p _polaris/team/legacynik/{sessions,weeks,handoff} _polaris/state .wiki/journal
printf '_polaris/state/current.md\n_polaris/state/current-state.md\n' > .gitignore
echo "root: _polaris" > _polaris/config.yml
git add .gitignore _polaris/config.yml; git commit -qm init
git remote add origin "$R"; git update-ref refs/remotes/origin/main HEAD
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
git branch -q feat/x; git worktree add -q "$W/wt-x" feat/x        # linked worktree, real
git checkout -q feat/y 2>/dev/null || git checkout -q -b feat/y   # MAIN worktree parked on a feature branch

fails=0
ck() { [ "$1" = ok ] && echo "  PASS $2" || { echo "  FAIL $2"; fails=$((fails+1)); }; }

# ---- resolver exactly as written in the SKILL.md, from inside the LINKED worktree
cd "$W/wt-x" || exit 1
MAIN_WT="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"
ROOT="$MAIN_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$MAIN_WT"
HOME="$FAKE_HOME"; unset CLAUDE_PLUGIN_ROOT
SC="${CLAUDE_PLUGIN_ROOT:-}/skills/update/scripts/session_commit.sh"
[ -x "$SC" ] || SC="$HOME/.agents/skills/update/scripts/session_commit.sh"
[ "$(cd "$MAIN_WT" && pwd -P)" = "$(cd "$R" && pwd -P)" ] && ck ok "One home resolves the main worktree from a linked one" || ck no "MAIN_WT=$MAIN_WT"
[ -x "$SC" ] && ck ok "resolver finds the script on a skills-CLI (npx) machine, PLUGIN_ROOT unset" || ck no "resolver empty"

# R1 main worktree parked on feat/y → checkpoint must DEFER, file must survive on disk
LOG="$ROOT/team/legacynik/sessions/$(date +%F)-@legacynik.md"
echo "## 10:00 — checkpoint from the linked worktree" > "$LOG"
cd "$MAIN_WT" || exit 1
OUT="$("$SC" "$LOG" 2>&1)"; echo "$OUT" | grep -q deferred && ck ok "R1 defer on a parked feature branch" || ck no "R1 $OUT"
[ -s "$LOG" ] && ck ok "R1 checkpoint still on disk (single copy)" || ck no "R1 checkpoint lost"
git log --oneline --all | grep -q checkpoint && ck no "R1 committed anyway" || ck ok "R1 no commit anywhere"

# R2 another panel leaves junk staged; back on main the deferred checkpoint lands, junk stays out
echo "SECRET=1" > .env; echo junk > junk.txt; git add -f .env junk.txt
git checkout -q main
OUT="$("$SC" "$LOG" 2>&1)"; echo "$OUT" | grep -q "committed on main" && ck ok "R2 deferred checkpoint lands on main" || ck no "R2 $OUT"
git show --name-only --format= HEAD | grep -qE '\.env|junk.txt' && ck no "R2 dragged a foreign staged file" || ck ok "R2 no foreign drag (.env/junk excluded)"
git show HEAD:"_polaris/team/legacynik/sessions/$(date +%F)-@legacynik.md" | grep -q "10:00" && ck ok "R2 content intact after defer→land" || ck no "R2 content lost"

# R3 /end mode: ledgers + journal line, on main → committed together with the handoff subject
echo "## $(date +%F) — decision (@legacynik)" > "$ROOT/decisions.md"
echo "## $(date +%F) — lesson (@legacynik)" > "$ROOT/lessons.md"
echo "session $(date +%F) @legacynik" > .wiki/journal/2026-07-26.md
printf '# Handoff\n' > "$ROOT/team/legacynik/handoff/$(date +%F).md"
OUT="$("$SC" --end "$LOG" "$ROOT/team/legacynik/handoff/$(date +%F).md" "$ROOT/decisions.md" "$ROOT/lessons.md" ".wiki/journal/2026-07-26.md" 2>&1)"
git log -1 --format=%s | grep -q "session handoff" && ck ok "R3 --end commits with the handoff subject" || ck no "R3 $OUT"
for f in _polaris/decisions.md _polaris/lessons.md .wiki/journal/2026-07-26.md; do
  git show --name-only --format= HEAD | grep -qx "$f" && ck ok "R3 --end committed $f" || ck no "R3 missing $f"
done

# R4 --end on a feature branch → defers (the exact loss observed: handoff stranded on ef7e7af)
git checkout -q feat/y
mkdir -p "$(dirname "$LOG")"          # the branch predates the log path: /end must mkdir -p before appending
echo "## 20:00 — session end" >> "$LOG"
BEFORE="$(git rev-parse HEAD)"
OUT="$("$SC" --end "$LOG" "$ROOT/decisions.md" 2>&1)"
echo "$OUT" | grep -q deferred && ck ok "R4 --end defers on a feature branch" || ck no "R4 $OUT"
[ "$(git rev-parse HEAD)" = "$BEFORE" ] && ck ok "R4 nothing committed on feat/y" || ck no "R4 committed on feat/y"

# R5 gitignored cockpit can never be laundered in through --end
echo x > "$ROOT/state/current.md"
"$SC" --end "$ROOT/state/current.md" >/dev/null 2>&1; [ $? -eq 2 ] && ck ok "R5 --end refuses state/current.md" || ck no "R5 accepted the cockpit pointer"

# R7 the deferred file collides with the tracked version on main: git must REFUSE, never clobber
OUT="$(git checkout main 2>&1)"; RC=$?
if [ $RC -ne 0 ]; then
  grep -q "20:00" "$LOG" && ck ok "R7 checkout refused, deferred append intact (no silent loss)" || ck no "R7 append lost"
  # KNOWN CEILING: the append cannot ride the branch switch. Copy aside → switch → re-append.
  cp "$LOG" "$W/pending.md"; git checkout -q -f main
  cat "$W/pending.md" >> "$LOG"
  grep -q "20:00" "$LOG" && ck ok "R7 deferred append recoverable by copy-aside (manual, documented)" || ck no "R7 append not recoverable"
else
  grep -q "20:00" "$LOG" && ck ok "R7 checkout carried the deferred append to main" || ck no "R7 append silently dropped by checkout"
fi
"$SC" "$LOG" >/dev/null 2>&1
git show HEAD:"_polaris/team/legacynik/sessions/$(date +%F)-@legacynik.md" | grep -q "20:00" && ck ok "R7 the deferred append finally lands on main" || ck no "R7 never landed"

# R6 neither install path present → resolver empty, so the skill must fall back to the manual rule
SC2="${CLAUDE_PLUGIN_ROOT:-}/skills/update/scripts/session_commit.sh"
[ -x "$SC2" ] || SC2="$W/nonexistent-home/.agents/skills/update/scripts/session_commit.sh"
[ -x "$SC2" ] && ck no "R6 resolver found a phantom script" || ck ok "R6 resolver honestly empty (manual-rule branch)"

cd /; rm -rf "$W"
echo; [ "$fails" -eq 0 ] && echo "REAL TEST: all scenarios PASS" || echo "REAL TEST: $fails FAILURE(S)"
exit "$fails"
