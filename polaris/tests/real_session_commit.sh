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
git init -q -b main; git config user.email t@t; git config user.name t; git config polaris.login acme-dev
mkdir -p _polaris/team/acme-dev/{sessions,weeks,handoff} _polaris/state .wiki/journal
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

# R1 TWO checkouts and NEITHER on the default branch → nothing may land today. Before polaris#12
# this printed «this repo has one checkout» with a second checkout right there, committed the
# session onto whatever branch another panel had parked the main checkout on, and drained the spool
# onto it too. The entry now waits in the spool that `/start` counts, and the reason names the branch.
LOG="$ROOT/team/acme-dev/sessions/$(date +%F)-@acme-dev.md"
echo "## 10:00 — checkpoint from the linked worktree" > "$LOG"
cd "$MAIN_WT" || exit 1
echo "SECRET=1" > .env; echo junk > junk.txt; git add -f .env junk.txt   # another panel's staging
BEFORE="$(git rev-parse HEAD)"
OUT="$("$SC" "$LOG" 2>&1)"
echo "$OUT" | grep -q deferred && ck ok "R1 two checkouts and none on the default defer" || ck no "R1 $OUT"
echo "$OUT" | grep -q "one checkout" && ck no "R1 read two checkouts as one" || ck ok "R1 never claims one checkout"
echo "$OUT" | grep -q "feat/y" && ck ok "R1 the reason names the parked main checkout" || ck no "R1 silent about the branch: $OUT"
[ "$(git rev-parse HEAD)" = "$BEFORE" ] && ck ok "R1 nothing landed on another panel's branch" || ck no "R1 committed anyway"
[ -n "$(find "$(git rev-parse --git-common-dir)/polaris-deferred" -type f 2>/dev/null)" ] \
  && ck ok "R1 the entry is in the spool, not lost" || ck no "R1 the deferral vanished"
[ -z "$(git status --short -- "$LOG")" ] && ck ok "R1 AC4: git status clean on the session log" || ck no "R1 left the tree dirty"
git diff --cached --name-only | grep -q junk.txt && ck ok "R1 the foreign staging is exactly as it was" || ck no "R1 unstaged another panel's work"

# R1b ONE checkout, off the default → there is no next default-branch session to wait for, so it
# commits HERE — with exactly the file this run wrote. A log from another day sitting untracked in
# the same directory is not this run's, and a pathspec that swept it up is the other half of #12.
git worktree remove --force "$W/wt-x"
echo "## 10:00 — checkpoint from the linked worktree" > "$LOG"
STRAY="$ROOT/team/acme-dev/sessions/2026-09-02-@acme-dev.md"
printf '## 09:00 — another day, never committed\n' > "$STRAY"
OUT="$("$SC" "$LOG" 2>&1)"
echo "$OUT" | grep -q "committing here" && ck ok "R1b a single checkout commits on its own branch" || ck no "R1b $OUT"
git show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "10:00" && ck ok "R1b the checkpoint reached a ref" || ck no "R1b never landed"
[ "$(git show --name-only --format= HEAD | grep -c 'sessions/')" = 1 ] && ck ok "R1b exactly this run's file landed" || ck no "R1b swept another session's log"
git status --short -- "$STRAY" | grep -q '^??' && ck ok "R1b the stray log is still untracked" || ck no "R1b touched a file this run never wrote"
git show --name-only --format= HEAD | grep -qE '\.env|junk.txt' && ck no "R1b dragged a foreign staged file" || ck ok "R1b no foreign drag (.env/junk excluded)"

# R2 a sibling worktree IS on the default branch → it takes the checkpoint, this tree keeps no
# orphan copy, and the ABSOLUTE path `/end` actually passes survives the hand-off. It did not:
# git refuses a pathspec outside the worktree, and the run said "no session-state change, skip"
# while the handoff sat uncommitted.
git reset -q HEAD .env junk.txt
git worktree add -q "$W/wt-main" main
echo "## 12:00 — from the parked tree" >> "$LOG"
OUT="$("$SC" "$LOG" 2>&1)"          # $LOG is absolute, exactly as end/SKILL.md writes it
echo "$OUT" | grep -q "worktree at" && ck ok "R2 the default worktree is handed the commit" || ck no "R2 $OUT"
git -C "$W/wt-main" show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "12:00" && ck ok "R2 an absolute path still lands on the default branch" || ck no "R2 content never landed"
# What may stay is only what this branch already TRACKS — never an untracked orphan, and never
# silently: an orphan is dirt AC4 forbids, a tracked file is this branch's own content and is named.
if [ -z "$(git status --short -- "$LOG")" ]; then
  ck ok "R2 the deferring tree keeps nothing"
else
  git status --short -- "$LOG" | grep -q '^??' && ck no "R2 left an untracked orphan" \
    || { echo "$OUT" | grep -q "tracked and still modified here" \
         && ck ok "R2 what stays is tracked here, and is named" || ck no "R2 silent about what stayed"; }
fi
git worktree remove --force "$W/wt-main"
"$SC" "$LOG" >/dev/null 2>&1        # land this branch's own copy, then move on
git checkout -q main

# R3 /end mode: ledgers + journal line, on main → committed together with the handoff subject
echo "## $(date +%F) — decision (@acme-dev)" > "$ROOT/decisions.md"
echo "## $(date +%F) — lesson (@acme-dev)" > "$ROOT/lessons.md"
echo "session $(date +%F) @acme-dev" > .wiki/journal/2026-07-26.md
printf '# Handoff\n' > "$ROOT/team/acme-dev/handoff/$(date +%F).md"
OUT="$("$SC" --end "$LOG" "$ROOT/team/acme-dev/handoff/$(date +%F).md" "$ROOT/decisions.md" "$ROOT/lessons.md" ".wiki/journal/2026-07-26.md" 2>&1)"
git log -1 --format=%s | grep -q "session handoff" && ck ok "R3 --end commits with the handoff subject" || ck no "R3 $OUT"
for f in _polaris/decisions.md _polaris/lessons.md .wiki/journal/2026-07-26.md; do
  git show --name-only --format= HEAD | grep -qx "$f" && ck ok "R3 --end committed $f" || ck no "R3 missing $f"
done

# R4 a DECLARED policy against direct commits on the default branch → deferred, never forced (#141)
git config polaris.commit-policy no-direct-default
echo "## 20:00 — session end" >> "$LOG"
BEFORE="$(git rev-parse HEAD)"
OUT="$("$SC" --end "$LOG" "$ROOT/decisions.md" 2>&1)"
echo "$OUT" | grep -q deferred && ck ok "R4 --end defers under a no-direct-commit policy" || ck no "R4 $OUT"
[ "$(git rev-parse HEAD)" = "$BEFORE" ] && ck ok "R4 nothing was committed against the policy" || ck no "R4 forced a forbidden commit"
# The honest ceiling of a defer: an UNTRACKED copy goes to the spool and leaves the tree; a file
# already tracked here cannot, because removing it would be a deletion — so it is NAMED, not hidden.
echo "$OUT" | grep -q "tracked and still modified here" && ck ok "R4 the file it could not clear is named, not hidden" || ck no "R4 silent about what stayed: $OUT"

# R5 gitignored cockpit can never be laundered in through --end
echo x > "$ROOT/state/current.md"
"$SC" --end "$ROOT/state/current.md" >/dev/null 2>&1; [ $? -eq 2 ] && ck ok "R5 --end refuses state/current.md" || ck no "R5 accepted the cockpit pointer"

# R7 what the policy deferred is NOT lost: it drains on the next run that is allowed to commit.
# The spool lives under the common git dir, so it is branch-independent — this is what `/start`
# counts, and a deferral that never drains would be data loss with a reassuring message.
[ -n "$(find "$(git rev-parse --git-common-dir)/polaris-deferred" -type f 2>/dev/null)" ] \
  && ck ok "R7 the deferred entry is in the spool" || ck no "R7 the deferral vanished"
git config --unset polaris.commit-policy
# Drained in the SAME mode that deferred it: a checkpoint may not commit `decisions.md`, so a
# checkpoint-mode drain would correctly leave the ledger in the spool and the assertion below
# would be reading its own wrong question.
"$SC" --end "$LOG" "$ROOT/decisions.md" >/dev/null 2>&1
git show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "20:00" && ck ok "R7 the deferred append drains and lands" || ck no "R7 never landed"
[ -z "$(find "$(git rev-parse --git-common-dir)/polaris-deferred" -type f 2>/dev/null)" ] \
  && ck ok "R7 the spool is empty once it drained" || ck no "R7 the spool still holds a drained entry"

# R6 neither install path present → resolver empty, so the skill must fall back to the manual rule
SC2="${CLAUDE_PLUGIN_ROOT:-}/skills/update/scripts/session_commit.sh"
[ -x "$SC2" ] || SC2="$W/nonexistent-home/.agents/skills/update/scripts/session_commit.sh"
[ -x "$SC2" ] && ck no "R6 resolver found a phantom script" || ck ok "R6 resolver honestly empty (manual-rule branch)"

cd /; rm -rf "$W"
echo; [ "$fails" -eq 0 ] && echo "REAL TEST: all scenarios PASS" || echo "REAL TEST: $fails FAILURE(S)"
exit "$fails"
