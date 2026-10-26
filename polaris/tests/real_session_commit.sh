#!/usr/bin/env bash
# REAL test: exercise the exact lines the SKILL.md prescribes, on a real repo with real worktrees,
# simulating BOTH install paths. Adversarial: every new branch must be hit.
#
# The contract since 2026-09-04: the session log commits on the CURRENT branch of the checkout that
# wrote it, always. Three declared refusals, exit 2, and nothing is ever copied anywhere.
set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"   # the polaris/ package dir
W="$(mktemp -d)"; FAKE_HOME="$W/home"
mkdir -p "$FAKE_HOME/.agents/skills/end" "$FAKE_HOME/.agents/skills/start"
cp -R "$SRC/skills/end/scripts" "$FAKE_HOME/.agents/skills/end/scripts"   # simulate `npx skills` install
cp -R "$SRC/skills/start/scripts" "$FAKE_HOME/.agents/skills/start/scripts"

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
spool() { find "$(git rev-parse --git-common-dir)/polaris-deferred" -type f 2>/dev/null; }

# ---- resolver exactly as written in the SKILL.md, from inside the LINKED worktree
cd "$W/wt-x" || exit 1
MAIN_WT="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"
ROOT="$MAIN_WT/_polaris"; [ -f "$ROOT/config.yml" ] || ROOT="$MAIN_WT"
HOME="$FAKE_HOME"; unset CLAUDE_PLUGIN_ROOT
SC="${CLAUDE_PLUGIN_ROOT:-}/skills/end/scripts/session_commit.sh"
[ -x "$SC" ] || SC="$HOME/.agents/skills/end/scripts/session_commit.sh"
[ "$(cd "$MAIN_WT" && pwd -P)" = "$(cd "$R" && pwd -P)" ] && ck ok "One home resolves the main worktree from a linked one" || ck no "MAIN_WT=$MAIN_WT"
[ -x "$SC" ] && ck ok "resolver finds the script on a skills-CLI (npx) machine, PLUGIN_ROOT unset" || ck no "resolver empty"

# R1 TWO checkouts and NEITHER on the default branch. This used to defer forever and leave the
# session log untracked in the tree; the log now lands on the branch this checkout is on, with
# exactly the file this run wrote and nothing another panel had staged.
LOG="$ROOT/team/acme-dev/sessions/$(date +%F)-@acme-dev.md"
echo "## 10:00 — checkpoint from the linked worktree" > "$LOG"
STRAY="$ROOT/team/acme-dev/sessions/2026-09-02-@acme-dev.md"
printf '## 09:00 — another day, never committed\n' > "$STRAY"
cd "$MAIN_WT" || exit 1
echo "SECRET=1" > .env; echo junk > junk.txt; git add -f .env junk.txt   # another panel's staging
OUT="$("$SC" "$LOG" 2>&1)"
echo "$OUT" | grep -q "committed on feat/y" && ck ok "R1 two checkouts, none on the default: it commits on the current branch" || ck no "R1 $OUT"
git show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "10:00" && ck ok "R1 the checkpoint reached a ref" || ck no "R1 never landed"
[ "$(git show --name-only --format= HEAD | grep -c 'sessions/')" = 1 ] && ck ok "R1 exactly this run's file landed" || ck no "R1 swept another session's log"
git status --short -- "$STRAY" | grep -q '^??' && ck ok "R1 the stray log is still untracked" || ck no "R1 touched a file this run never wrote"
git show --name-only --format= HEAD | grep -qE '\.env|junk.txt' && ck no "R1 dragged a foreign staged file" || ck ok "R1 no foreign drag (.env/junk excluded)"
git diff --cached --name-only | grep -q junk.txt && ck ok "R1 the foreign staging is exactly as it was" || ck no "R1 unstaged another panel's work"
[ -z "$(git status --short -- "$LOG")" ] && ck ok "R1 the tree is clean on the session log" || ck no "R1 left the tree dirty"
[ -z "$(spool)" ] && ck ok "R1 nothing was copied to a spool" || ck no "R1 wrote a spool"

# R2 a sibling worktree IS on the default branch — and it changes nothing. The log belongs to the
# branch the session happened on, and the ABSOLUTE path `/end` actually passes still resolves.
git reset -q HEAD .env junk.txt
git worktree add -q "$W/wt-main" main
echo "## 12:00 — from the parked tree" >> "$LOG"
OUT="$("$SC" "$LOG" 2>&1)"          # $LOG is absolute, exactly as end/SKILL.md writes it
echo "$OUT" | grep -q "committed on feat/y" && ck ok "R2 a sibling on the default does not take the commit" || ck no "R2 $OUT"
git show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "12:00" && ck ok "R2 an absolute path still lands here" || ck no "R2 content never landed"
git -C "$W/wt-main" log -1 --format=%s | grep -q init && ck ok "R2 the default worktree was left alone" || ck no "R2 wrote onto main"
[ -z "$(git status --short -- "$LOG")" ] && ck ok "R2 the tree is clean afterwards" || ck no "R2 left the tree dirty"
git worktree remove --force "$W/wt-main"; git worktree remove --force "$W/wt-x"
git checkout -q main

# R3 /end mode: ledgers + journal line, on main → committed together with the handoff subject
echo "## $(date +%F) — decision (@acme-dev)" > "$ROOT/decisions.md"
echo "## $(date +%F) — lesson (@acme-dev)" > "$ROOT/lessons.md"
echo "session $(date +%F) @acme-dev" > .wiki/journal/2026-07-26.md
printf '# Handoff\n' > "$ROOT/team/acme-dev/handoff/$(date +%F).md"
echo "## 19:00 — session end" >> "$LOG"
OUT="$("$SC" --end "$LOG" "$ROOT/team/acme-dev/handoff/$(date +%F).md" "$ROOT/decisions.md" "$ROOT/lessons.md" ".wiki/journal/2026-07-26.md" 2>&1)"
git log -1 --format=%s | grep -q "session handoff" && ck ok "R3 --end commits with the handoff subject" || ck no "R3 $OUT"
for f in _polaris/decisions.md _polaris/lessons.md .wiki/journal/2026-07-26.md; do
  git show --name-only --format= HEAD | grep -qx "$f" && ck ok "R3 --end committed $f" || ck no "R3 missing $f"
done
[ -z "$(git status --short -- "$LOG" "$ROOT/decisions.md" "$ROOT/lessons.md")" ] && ck ok "R3 C5: /end leaves the Polaris paths clean" || ck no "R3 finished dirty"

# R4 the first declared refusal: a policy against a direct commit on the DEFAULT branch. Exit 2,
# one line, zero commits, and the file stays exactly where the session wrote it.
git config polaris.commit-policy no-direct-default
echo "## 20:00 — session end" >> "$LOG"
BEFORE="$(git rev-parse HEAD)"
OUT="$("$SC" --end "$LOG" "$ROOT/decisions.md" 2>&1)"; RC=$?
[ "$RC" -eq 2 ] && ck ok "R4 --end exits 2 under a no-direct-commit policy" || ck no "R4 rc=$RC $OUT"
echo "$OUT" | grep -q "polaris.commit-policy" && ck ok "R4 the refusal names the policy" || ck no "R4 $OUT"
[ "$(git rev-parse HEAD)" = "$BEFORE" ] && ck ok "R4 nothing was committed against the policy" || ck no "R4 forced a forbidden commit"
[ -n "$(git status --short -- "$LOG")" ] && ck ok "R4 the file is still in the working tree" || ck no "R4 the file vanished"
[ -z "$(spool)" ] && ck ok "R4 no copy was made anywhere" || ck no "R4 wrote a spool"
# the same policy on a feature branch is not this repo's rule: it commits.
git checkout -q -b feat/z
"$SC" --end "$LOG" "$ROOT/decisions.md" >/dev/null 2>&1
git show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "20:00" && ck ok "R4 the policy applies to the default branch only" || ck no "R4 leaked onto a feature branch"
git config --unset polaris.commit-policy

# R5 gitignored cockpit can never be laundered in through --end
echo x > "$ROOT/state/current.md"
"$SC" --end "$ROOT/state/current.md" >/dev/null 2>&1; [ $? -eq 2 ] && ck ok "R5 --end refuses state/current.md" || ck no "R5 accepted the cockpit pointer"

# R6 the other refusal: a detached HEAD. A repo with NO commit is not one — it lands.
echo "## 21:00 — detached" >> "$LOG"
git checkout -q --detach HEAD
OUT="$("$SC" "$LOG" 2>&1)"; RC=$?
[ "$RC" -eq 2 ] && echo "$OUT" | grep -q detached && ck ok "R6 a detached HEAD refuses with its own reason" || ck no "R6 rc=$RC $OUT"
[ -n "$(git status --short -- "$LOG")" ] && ck ok "R6 the detached run left the file in the tree" || ck no "R6 the file vanished"
U="$W/unborn"; mkdir -p "$U/_polaris/team/acme-dev/sessions"
( cd "$U" && git init -q -b main . && git config user.email t@t && git config user.name t
  echo "## first" > _polaris/team/acme-dev/sessions/s.md
  "$SC" _polaris/team/acme-dev/sessions/s.md >/dev/null 2>&1
  git show HEAD:_polaris/team/acme-dev/sessions/s.md 2>/dev/null | grep -q first ) \
  && ck ok "R6 a repo with no commit lands its first checkpoint" || ck no "R6 the unborn repo never landed"
git checkout -q feat/z

# R7 a spool left by an older version is counted by `checkpoint.sh prepare` and never touched.
CK="$HOME/.agents/skills/end/scripts/checkpoint.sh"
mkdir -p "$(git rev-parse --git-common-dir)/polaris-deferred/_polaris"
echo old > "$(git rev-parse --git-common-dir)/polaris-deferred/_polaris/old.md"
OUT="$(bash "$CK" prepare 2>&1)"
echo "$OUT" | grep -q "SPOOL_LEGACY=1" && ck ok "R7 a legacy spool is counted by name" || ck no "R7 $OUT"
[ -n "$(spool)" ] && ck ok "R7 prepare left the legacy spool alone" || ck no "R7 prepare ate it"

# R9 G1 — the panel's own worktree keeps its log. A linked worktree on `feat/mine`, the MAIN
# checkout parked on `feat/z`: the log is written under the LINKED worktree's contract and lands
# on `feat/mine`. Before this the resolver sent both the write and the commit to the main checkout.
git worktree add -q "$W/wt-mine" -b feat/mine
MAIN_HEAD="$(git rev-parse HEAD)"
( cd "$W/wt-mine" || exit 1
  eval "$(bash "$HOME/.agents/skills/start/scripts/resume_paths.sh")"
  case "$ROOT" in */wt-mine/_polaris) ;; *) echo "  FAIL R9 ROOT is not this worktree: $ROOT"; exit 1 ;; esac
  case "$CURRENT" in */repo/_polaris/*) ;; *) echo "  FAIL R9 the cockpit left the main worktree: $CURRENT"; exit 1 ;; esac
  mkdir -p "$ROOT/team/acme-dev/sessions"
  echo "## 22:00 — from my own worktree" > "$ROOT/team/acme-dev/sessions/$(date +%F)-@acme-dev.md"
  cd "$(git rev-parse --show-toplevel)"
  "$SC" "$ROOT/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" >/dev/null 2>&1
  git show HEAD:"_polaris/team/acme-dev/sessions/$(date +%F)-@acme-dev.md" | grep -q "22:00" ) \
  && ck ok "R9 a linked worktree writes and commits its own log" || ck no "R9 the log did not land here"
[ "$(git -C "$W/wt-mine" rev-parse --abbrev-ref HEAD)" = feat/mine ] && ck ok "R9 it stayed on its own branch" || ck no "R9 changed branch"
[ "$(git rev-parse HEAD)" = "$MAIN_HEAD" ] && ck ok "R9 the main checkout took nothing" || ck no "R9 wrote onto the main checkout's branch"
git worktree remove --force "$W/wt-mine"

# R10 G2 — a path git refuses is named with its reason, exits 2, and the rest of the set lands.
mkdir -p "$R/nested/journal" && git -C "$R/nested" init -q -b main
echo "session line" > "$R/nested/journal/j.md"
echo "## $(date +%F) — another lesson (@acme-dev)" >> "$ROOT/lessons.md"
OUT="$("$SC" --end "$R/nested/journal/j.md" "$ROOT/lessons.md" 2>&1)"; RC=$?
[ "$RC" -eq 2 ] && ck ok "R10 a path git refuses exits 2" || ck no "R10 rc=$RC $OUT"
echo "$OUT" | grep -q "git refuses .*(nested repo)" && ck ok "R10 the refusal names path and reason" || ck no "R10 $OUT"
git show --name-only --format= HEAD | grep -qx _polaris/lessons.md && ck ok "R10 the other paths still landed" || ck no "R10 the whole handoff died with one path"

# R8 neither install path present → resolver empty, so the skill must fall back to the manual rule
SC2="${CLAUDE_PLUGIN_ROOT:-}/skills/end/scripts/session_commit.sh"
[ -x "$SC2" ] || SC2="$W/nonexistent-home/.agents/skills/end/scripts/session_commit.sh"
[ -x "$SC2" ] && ck no "R8 resolver found a phantom script" || ck ok "R8 resolver honestly empty (manual-rule branch)"

cd /; rm -rf "$W"
echo; [ "$fails" -eq 0 ] && echo "REAL TEST: all scenarios PASS" || echo "REAL TEST: $fails FAILURE(S)"
exit "$fails"
