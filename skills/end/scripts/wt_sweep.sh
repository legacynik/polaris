#!/usr/bin/env bash
# wt_sweep.sh — keep worktrees clean without ever touching anyone's work.
#
# Safety, hard (lessons 2026-08-03/04): a DIRTY worktree is NEVER touched —
# report only. Removal only for CLEAN worktrees whose HEAD is already merged
# into the default branch (content lives on main; branch deleted with -d,
# which refuses unmerged). Never the main worktree, never the one we run in.
#
# Usage: wt_sweep.sh            apply (remove merged+clean, prune, report)
#        wt_sweep.sh --report   report only, remove nothing (checkpoint mode)
#        wt_sweep.sh --selfcheck
# Exit: 0 ok (report printed) · 1 selfcheck failed · 2 not a git repo
set -euo pipefail

mode="${1:-apply}"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"  # the selfcheck cd-s away

default_branch() {
  git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null \
    | sed 's|^origin/||' || echo main
}

sweep() {
  local root cur def head removed=0 kept_dirty=0 kept_unmerged=0
  root="$(git worktree list --porcelain | head -1 | sed 's|^worktree ||')"
  cur="$(git rev-parse --show-toplevel)"
  def="$(default_branch)"
  git worktree prune
  while IFS= read -r wt; do
    [ "$wt" = "$root" ] && continue
    [ "$wt" = "$cur" ] && continue
    [ -d "$wt" ] || continue
    if [ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]; then
      kept_dirty=$((kept_dirty+1))
      echo "· dirty, NOT touched: $wt ($(git -C "$wt" status --porcelain | wc -l | tr -d ' ') files)"
      continue
    fi
    head="$(git -C "$wt" rev-parse HEAD)"
    if git merge-base --is-ancestor "$head" "refs/remotes/origin/$def" 2>/dev/null \
       || git merge-base --is-ancestor "$head" "refs/heads/$def" 2>/dev/null; then
      if [ "$mode" = "--report" ]; then
        echo "· removable (clean, merged into $def): $wt"
      else
        local br
        br="$(git -C "$wt" rev-parse --abbrev-ref HEAD)"
        git worktree remove "$wt"
        echo "✂ removed (clean, merged into $def): $wt${br:+ [$br]}"
        # Best-effort: -d refuses a branch not merged into HEAD (merged only on origin, say).
        # The worktree is gone either way; the branch that stays is named, never swallowed.
        if [ "$br" != "HEAD" ] && ! git branch -d "$br" >/dev/null 2>&1; then
          echo "· branch $br kept: git branch -d refused it (not merged into HEAD) — delete it by hand once checked"
        fi
      fi
      removed=$((removed+1))
    else
      kept_unmerged=$((kept_unmerged+1))
      echo "· alive (clean, NOT merged — paused): $wt · $(git -C "$wt" log -1 --format='%h %cr')"
    fi
  done < <(git worktree list --porcelain | sed -n 's|^worktree ||p')
  echo "wt-sweep: ${removed} $( [ "$mode" = "--report" ] && echo removable || echo removed) · ${kept_dirty} dirty (untouched) · ${kept_unmerged} paused"
}

selfcheck() {
  local d ok=0 out out2
  d="$(mktemp -d)"
  ( cd "$d" && git init -qb main r && cd r \
    && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base \
    && git worktree add -q ../wt-merged -b merged >/dev/null \
    && git worktree add -q ../wt-dirty -b dirty >/dev/null \
    && echo x > ../wt-dirty/f.txt \
    && git worktree add -q ../wt-ahead -b ahead >/dev/null \
    && git -C ../wt-ahead -c user.email=t@t -c user.name=t commit -q --allow-empty -m work )
  out="$(cd "$d/r" && bash "$SELF" apply)"
  echo "$out"
  echo "$out" | grep -q "removed .*wt-merged"        || { echo "FAIL: merged+clean not removed"; ok=1; }
  [ -d "$d/wt-dirty" ]                               || { echo "FAIL: dirty worktree REMOVED"; ok=1; }
  echo "$out" | grep -q "dirty, NOT touched"         || { echo "FAIL: dirty not reported"; ok=1; }
  [ -d "$d/wt-ahead" ]                               || { echo "FAIL: unmerged worktree REMOVED"; ok=1; }
  echo "$out" | grep -q "alive (clean, NOT merged"   || { echo "FAIL: paused not reported"; ok=1; }
  # Report mode needs something it COULD remove, or "removes nothing" proves nothing.
  ( cd "$d/r" && git worktree add -q ../wt-merged2 -b merged2 >/dev/null )
  out2="$(cd "$d/r" && bash "$SELF" --report)"
  [ -d "$d/wt-merged2" ]                             || { echo "FAIL: report mode REMOVED a worktree"; ok=1; }
  echo "$out2" | grep -q "removable .*wt-merged2"    || { echo "FAIL: report mode did not name it"; ok=1; }
  rm -rf "$d"
  [ $ok -eq 0 ] && echo "selfcheck: ok (merged removed · dirty untouched · paused alive · report removes nothing)"
  return $ok
}

case "$mode" in
  --selfcheck) selfcheck ;;
  --report|apply) git rev-parse --git-dir >/dev/null 2>&1 || exit 2; sweep ;;
  *) echo "usage: wt_sweep.sh [--report|--selfcheck]" >&2; exit 2 ;;
esac
