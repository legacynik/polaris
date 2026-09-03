#!/usr/bin/env python3
"""handoff_radar — aggregate EVERY session handoff across panels, worktrees, branches.

/start reads main's state/current.md + the newest session log — but with 5+ parallel
panels, handoffs hide in 3 other places and get silently lost:
  1. stray per-worktree state/current.md (written inside a worktree, main never sees it)
  2. session logs committed on unmerged branches (session_commit lands on the CURRENT branch)
  3. uncommitted session logs sitting in a worktree
This scans all of them, read-only, no LLM, <2s. Output feeds /start so the operator
sees ALL end-of-sessions and decides where to resume. Fail-open per repo.

Scope is the repo it is run from (T15). It used to carry a hardcoded vault path and a
hardcoded repo list, which pinned it to one machine and made it unshippable in the public
package — so every product repo got "radar assente" and kept its strays invisible. Pass
`--repo` once per repository to widen the sweep.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SINCE = "14 days ago"


def _git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, timeout=20)
        return out.stdout
    except Exception:
        return ""


def _worktrees(repo: Path) -> list[Path]:
    trees = []
    for line in _git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            trees.append(Path(line[9:]))
    return trees


def _polaris_root(tree: Path) -> Path:
    return tree / "_polaris" if (tree / "_polaris").is_dir() else tree


def _last_checkpoint(text: str) -> str:
    blocks = [b for b in text.split("\n## ") if b.strip()]
    return ("## " + blocks[-1]).strip()[:600] if len(blocks) > 1 else text.strip()[-600:]


def stray_currents(repo: Path, main_tree: Path) -> list[str]:
    found = []
    for tree in _worktrees(repo):
        if tree == main_tree:
            continue
        cur = _polaris_root(tree) / "state" / "current.md"
        if cur.exists():
            mtime = datetime.fromtimestamp(cur.stat().st_mtime).strftime("%m-%d %H:%M")
            head = next((l for l in cur.read_text().splitlines() if l.startswith("Updated:")), "?")
            found.append(f"  ⚠ stray current.md in {tree.name} (mtime {mtime}) — {head[:120]}")
    return found


def branch_only_sessions(repo: Path) -> list[str]:
    """One row per (commit, handoff). Deduplicating on the PATH alone hid a whole commit:
    two commits on two branches carried the same session file and only the first was
    reported (measured 2026-09-03 — `b41833fd` was invisible behind `bcafc529`)."""
    out = _git(repo, "log", "--all", "--not", "main", f"--since={SINCE}",
               "--format=%h %D", "--name-only", "--", "*sessions/*.md")
    cur_ref, seen, found = "", set(), []
    for line in out.splitlines():
        if " " in line and not line.endswith(".md"):
            cur_ref = line.strip()   # sha AND decoration: the sha is what a report cites
        elif line.endswith(".md") and "sessions/" in line and (cur_ref, line) not in seen:
            seen.add((cur_ref, line))
            found.append(f"  ⚠ handoff su branch non mergiato [{cur_ref.strip()[:40]}]: {line}")
    return found[:8]


def uncommitted_sessions(repo: Path) -> list[str]:
    found = []
    for tree in _worktrees(repo):
        for line in _git(tree, "status", "--short", "--", "*sessions/*.md").splitlines():
            path = tree / line[3:].strip()
            if path.exists():
                found.append(f"  ⚠ handoff NON committato in {tree.name}: {line[3:].strip()}")
                found.append("    " + _last_checkpoint(path.read_text()).splitlines()[0])
    return found[:8]


def cockpit(repo: Path) -> Path | None:
    """THE cockpit of this repo for whoever is running it: the caller's migrated home, else
    any migrated home, else the legacy file. Taking the alphabetically first `team/*/` printed
    a colleague's cockpit and called it "the one cockpit of this repo"."""
    root = _polaris_root(repo)
    login = _git(repo, "config", "--local", "--get", "polaris.login").strip()
    mine = root / "team" / login / "current.md" if login else None
    legacy = root / "state" / "current.md"
    if mine and mine.exists():
        return mine
    return next(iter(sorted(root.glob("team/*/current.md"))), None) or \
        (legacy if legacy.exists() else None)


def scan(repo: Path) -> None:
    rows = stray_currents(repo, repo) + branch_only_sessions(repo) + uncommitted_sessions(repo)
    print(f"## {repo.name}: " + ("tutto convergiuto su main ✓" if not rows else ""))
    for row in rows:
        print(row)
    if cur := cockpit(repo):
        print(f"\n## Convergenza ({cur})")
        for line in cur.read_text().splitlines():
            if line.startswith(("Updated:", "- `", "## ")):
                print(line[:200])


def main() -> int:
    ap = argparse.ArgumentParser(description="cross-panel handoff radar (read-only)")
    ap.add_argument("--repo", action="append", type=Path, default=[],
                    help="repository to scan; repeatable. Default: the repo of the cwd.")
    repos = [p.resolve() for p in ap.parse_args().repo]
    if not repos:  # git lists the MAIN worktree first — the one home cockpits resolve against
        first = (_git(Path.cwd(), "worktree", "list", "--porcelain").splitlines() or [""])[0]
        if not first.startswith("worktree "):
            print("handoff_radar: not a git repository — pass --repo <path>", file=sys.stderr)
            return 2
        repos = [Path(first[len("worktree "):])]
    # A named repo that is not one is a typo, not an all-clear: printing "tutto convergiuto"
    # over a directory the radar cannot read is a false green.
    for repo in repos:
        if not _git(repo, "rev-parse", "--git-dir").strip():
            print(f"handoff_radar: not a git repository: {repo}", file=sys.stderr)
            return 2
    print("# Handoff radar — tutti gli end-of-session, tutti i panel\n")
    for repo in repos:
        scan(repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
