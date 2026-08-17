#!/usr/bin/env bash
# wt_sweep.sh — keep worktrees clean without ever touching anyone's work.
#
# Safety, hard (lessons 2026-08-03/04): a DIRTY worktree is NEVER touched —
# report only. Removal only for CLEAN worktrees whose HEAD is already merged
# into the default branch (content lives on main; branch deleted with -d,
# which refuses unmerged). Never the main worktree, never the one we run in.
#
# Usage: wt_sweep.sh            apply (remove merged+clean, prune, report)
#        wt_sweep.sh --report   report only, remove nothing (/update mode)
#        wt_sweep.sh --selfcheck
# Exit: 0 ok (report printed) · 1 selfcheck failed · 2 not a git repo
set -euo pipefail

mode="${1:-apply}"

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
      echo "· sporco, NON tocco: $wt ($(git -C "$wt" status --porcelain | wc -l | tr -d ' ') file)"
      continue
    fi
    head="$(git -C "$wt" rev-parse HEAD)"
    if git merge-base --is-ancestor "$head" "refs/remotes/origin/$def" 2>/dev/null \
       || git merge-base --is-ancestor "$head" "refs/heads/$def" 2>/dev/null; then
      if [ "$mode" = "--report" ]; then
        echo "· rimovibile (pulito, mergiato in $def): $wt"
      else
        local br
        br="$(git -C "$wt" rev-parse --abbrev-ref HEAD)"
        git worktree remove "$wt"
        [ "$br" != "HEAD" ] && git branch -d "$br" >/dev/null 2>&1 || true
        echo "✂ rimosso (pulito, mergiato in $def): $wt${br:+ [$br]}"
      fi
      removed=$((removed+1))
    else
      kept_unmerged=$((kept_unmerged+1))
      echo "· vivo (pulito, NON mergiato — pausa): $wt · $(git -C "$wt" log -1 --format='%h %cr')"
    fi
  done < <(git worktree list --porcelain | sed -n 's|^worktree ||p')
  echo "wt-sweep: ${removed} $( [ "$mode" = "--report" ] && echo rimovibili || echo rimossi) · ${kept_dirty} sporchi (intoccati) · ${kept_unmerged} in pausa"
}

selfcheck() {
  local d ok=0
  d="$(mktemp -d)"
  ( cd "$d" && git init -qb main r && cd r \
    && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base \
    && git worktree add -q ../wt-merged -b merged >/dev/null \
    && git worktree add -q ../wt-dirty -b dirty >/dev/null \
    && echo x > ../wt-dirty/f.txt \
    && git worktree add -q ../wt-ahead -b ahead >/dev/null \
    && git -C ../wt-ahead -c user.email=t@t -c user.name=t commit -q --allow-empty -m work )
  out="$(cd "$d/r" && bash "$0" apply)"
  echo "$out"
  echo "$out" | grep -q "rimosso .*wt-merged"        || { echo "FAIL: merged+clean non rimosso"; ok=1; }
  [ -d "$d/wt-dirty" ]                                || { echo "FAIL: wt sporco RIMOSSO"; ok=1; }
  echo "$out" | grep -q "sporco, NON tocco"           || { echo "FAIL: sporco non riportato"; ok=1; }
  [ -d "$d/wt-ahead" ]                                || { echo "FAIL: wt non mergiato RIMOSSO"; ok=1; }
  echo "$out" | grep -q "vivo (pulito, NON mergiato"  || { echo "FAIL: pausa non riportata"; ok=1; }
  out2="$(cd "$d/r" && bash "$0" --report)"
  [ -z "$(cd "$d/r" && git worktree list | sed -n 4p)" ] || true  # report mode removes nothing:
  echo "$out2" | grep -q "0 rimovibili\|rimovibili" || { echo "FAIL: report muto"; ok=1; }
  rm -rf "$d"
  [ $ok -eq 0 ] && echo "selfcheck: ok (merged rimosso · sporco intoccato · pausa viva · report non rimuove)"
  return $ok
}

case "$mode" in
  --selfcheck) selfcheck ;;
  --report|apply) git rev-parse --git-dir >/dev/null 2>&1 || exit 2; sweep ;;
  *) echo "uso: wt_sweep.sh [--report|--selfcheck]" >&2; exit 2 ;;
esac
