#!/usr/bin/env python3
"""perimeter.py — derives the real perimeter of the change from git, mechanically.

Answers F6/F7/G2.6 (the real-test proves the SHA, not the flow): the perimeter
is not what the agent SAYS it looked at, it is what `git diff` shows,
recomputed on every call. New-branch detection (G1.6) is delegated to
`branches.py`.

Usage:
    perimeter.py --repo R [--base REF] [--head REF|STAGED] --hash-only
    perimeter.py --repo R [--base REF] [--head REF|STAGED]      # full JSON
    perimeter.py --selfcheck

`--head STAGED` (default) uses the tree `git commit` would create now
(`git write-tree`) — so the hash also captures changes not yet
committed, not just the last commit. For an already-committed branch/PR pass
`--head <sha-or-ref>`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from branches import detect_new_branches  # noqa: E402


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _default_branch(repo: Path) -> str | None:
    """The full REMOTE ref, not its last segment.

    `rsplit("/", 1)[-1]` on `refs/remotes/origin/HEAD` returned `"main"`, i.e.
    exactly the local name resolve_base's docstring forbids: the base
    ended up on the checkout's `main` branch, which in a multi-worktree repo is
    routinely dozens of commits behind origin/main. Measured on
    Acme-quotes on 2026-08-30: merge-base with `main` = 6d8cf38f and 237 files of
    perimeter, merge-base with `origin/main` = b45e443b and 59 — 178 files of
    someone else's work claimed as our own, silently. The selfcheck missed it because
    its fixture has no origin/HEAD and fell back to HEAD~1.
    """
    try:
        ref = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        return None  # no origin/HEAD: do NOT guess a name (doctrine: never assume main)
    prefix = "refs/remotes/"
    return ref[len(prefix):] if ref.startswith(prefix) else ref


def resolve_base(repo: Path, explicit: str | None) -> str:
    """Real base: explicit > merge-base with the TRUE default branch > declared HEAD~1.
    Never the literal name 'main'/'master': a stale branch with that name silently
    produces a wrong perimeter — a false green (red R1, merge 2026-08-16)."""
    if explicit:
        return git(repo, "rev-parse", explicit)
    default = _default_branch(repo)
    if default:
        try:
            return git(repo, "merge-base", "HEAD", default)
        except subprocess.CalledProcessError:
            pass
    print("perimeter: base cannot be determined (no --base, no origin/HEAD) — "
          "using HEAD~1 as a DECLARED FALLBACK; for a PR pass --base", file=sys.stderr)
    try:
        return git(repo, "rev-parse", "HEAD~1")
    except subprocess.CalledProcessError:
        return git(repo, "rev-parse", "HEAD")  # single-commit repo: the base is HEAD itself


def head_tree_hash(repo: Path, head: str) -> str:
    """The tree hash is the content key: it changes if ONE line changes."""
    if head == "STAGED":
        return git(repo, "write-tree")
    return git(repo, "rev-parse", f"{head}^{{tree}}")


def build_perimeter(repo: Path, base_ref: str | None, head_ref: str) -> dict:
    base = resolve_base(repo, base_ref)
    head_tree = head_tree_hash(repo, head_ref)
    diff_text = git(repo, "diff", base, head_tree)
    files = [l for l in git(repo, "diff", "--name-only", base, head_tree).splitlines() if l]
    return {
        "base": base,
        "head_tree": head_tree,
        "content_hash": head_tree,
        "files": files,
        "new_branches": detect_new_branches(diff_text),
    }


def _fixture_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")


def _commit_all(repo: Path, msg: str) -> None:
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", msg)


def _selfcheck() -> int:
    """Builds a throwaway git repo and exercises every branch of this script."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _fixture_repo(repo)
        f = repo / "a.py"
        f.write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
        _commit_all(repo, "base")
        base_sha = git(repo, "rev-parse", "HEAD")

        f.write_text(
            "def f(x):\n    if x:\n        return 1\n    else:\n        return -1\n    return 0\n"
        )
        git(repo, "add", ".")
        p = build_perimeter(repo, base_sha, "STAGED")
        assert p["files"] == ["a.py"], f"file not detected: {p['files']}"
        branches = [b["snippet"] for b in p["new_branches"]]
        assert any("else" in b for b in branches), f"new else not detected: {branches}"
        h_staged = p["content_hash"]

        _commit_all(repo, "fix")
        h_commit = git(repo, "rev-parse", "HEAD^{tree}")
        assert h_staged == h_commit, "STAGED hash and the resulting commit hash must match"

        f.write_text(f.read_text() + "# rumore\n")
        git(repo, "add", ".")
        h_noise = build_perimeter(repo, base_sha, "STAGED")["content_hash"]
        assert h_noise != h_commit, "one extra line must change the hash (key = content)"

    # R1 (merge 2026-08-16): a STALE 'main' branch must never silently become the base.
    # Three commits: 'main' stays at the first, HEAD~1 is the second — if the base
    # were 'main' (old behaviour) the two shas would differ.
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        subprocess.run(["git", "init", "-q", "-b", "develop", str(repo)], check=True)
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (repo / "f.txt").write_text("a\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "one")
        git(repo, "branch", "main")
        (repo / "f.txt").write_text("a\nb\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "two")
        (repo / "f.txt").write_text("a\nb\nc\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "three")
        base = resolve_base(repo, None)
        assert base == git(repo, "rev-parse", "HEAD~1") != git(repo, "rev-parse", "main"), \
            "R1: without origin/HEAD the base is the declared fallback HEAD~1, never the name 'main'"
    # R1b (2026-08-30): the case R1 does not touch. R1 tests a repo WITHOUT origin/HEAD,
    # so it falls back and never exercises _default_branch. With origin/HEAD
    # present, the old rsplit("/",1)[-1] returned "main" and the merge-base landed
    # on the LOCAL branch with that name — which in a multi-worktree checkout is stale.
    with tempfile.TemporaryDirectory() as td:
        up, repo = Path(td) / "up", Path(td) / "clone"
        subprocess.run(["git", "init", "-q", "-b", "main", str(up)], check=True)
        git(up, "config", "user.email", "t@t"); git(up, "config", "user.name", "t")
        (up / "f.txt").write_text("a\n"); git(up, "add", "."); git(up, "commit", "-qm", "one")
        subprocess.run(["git", "clone", "-q", str(up), str(repo)], check=True)
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (up / "f.txt").write_text("a\nb\n"); git(up, "add", "."); git(up, "commit", "-qm", "two")
        git(repo, "fetch", "-q", "origin")
        git(repo, "checkout", "-q", "-b", "feature", "origin/main")
        (repo / "g.txt").write_text("x\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "feature work")
        stale_local = git(repo, "rev-parse", "main")
        assert stale_local != git(repo, "rev-parse", "origin/main"), "fixture: the local main must be stale"
        base = resolve_base(repo, None)
        assert base == git(repo, "rev-parse", "origin/main"), \
            f"R1b: the base must come from origin/main, not the stale local main (base={base})"
        assert base != stale_local, "R1b: the base must NEVER be the local main"

    print("SELFCHECK OK — files/branches/hash on a throwaway repo + R1 base-never-guessed "
          "+ R1b origin/HEAD-is-not-the-local-main, 8 assertions")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path)
    ap.add_argument("--base")
    ap.add_argument("--head", default="STAGED")
    ap.add_argument("--hash-only", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if not a.repo:
        ap.error("--repo required")
    perim = build_perimeter(a.repo, a.base, a.head)
    if a.hash_only:
        print(perim["content_hash"])
    else:
        print(json.dumps(perim, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
