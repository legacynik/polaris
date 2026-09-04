"""The gate's own finding: nothing executed `/end`. These tests do.

Every block here is read out of the shipped `end/SKILL.md` with `skill_block` and run verbatim on a
host repo built from the templates, exactly as `test_update_gates` does for `/update`. A skill body
that stops calling its script, or calls it with an argument the script refuses, fails here instead
of passing a grep.

That is not hypothetical: the shipped Step 4 passed `--todos "$ROOT/state/todos.md"` on a repo whose
contract has no todos file — the shape `host_repo()` itself builds — and every close came back
`BLOCKED … UNWRITABLE` (F2). And Step 5's `git add` refuses the WHOLE pathspec when one optional
file is absent, so a missing weekly plan silently landed nothing (F1's neighbour).
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from host_repo import LOGIN, PKG, git, host_repo, run_block, seed_state, written

DAY = subprocess.run(["date", "+%F"], capture_output=True, text=True).stdout.strip()


def cockpit(repo: Path) -> Path:
    path = seed_state(repo, "current.md")
    written(path, "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02")
    return path


def merged(repo: Path) -> dict:
    """A branch really merged into main here, so the repo half of the truth is real."""
    git(repo, "switch", "-qc", "feat/b")
    (repo / "b.md").write_text("b\n")
    git(repo, "add", "b.md")
    git(repo, "commit", "-qm", "b")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge b", "feat/b")
    git(repo, "branch", "-qD", "feat/b")
    return {"pr": {"77": {"state": "MERGED", "headRefOid": head, "headRefName": "feat/b",
                          "mergeCommit": {"oid": git(repo, "rev-parse", "HEAD").stdout.strip()}}}}


def tracker(repo: Path, scenario: dict) -> dict:
    """A `gh` on PATH that answers from a fixture instead of the network."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "gh").write_text(f'#!/bin/sh\nexec python3 "{PKG / "tests" / "fake_gh.py"}" "$@"\n')
    (shim / "gh").chmod(0o755)
    return {"PATH": f"{shim}:{os.environ['PATH']}", "POLARIS_FAKE_GH": json.dumps(scenario)}


def session_files(repo: Path) -> list[Path]:
    root = repo / "_polaris" / "team" / LOGIN
    (root / "handoff").mkdir(parents=True, exist_ok=True)
    log = root / "sessions" / f"{DAY}-@{LOGIN}.md"
    log.write_text(f"## 18:00 — session end · lane chiusa · wt: main · branch: main\n- Files: x\n")
    (root / "handoff" / f"{DAY}.md").write_text(f"# Handoff {DAY} 18:00 — @{LOGIN}\n")
    return [log, root / "handoff" / f"{DAY}.md"]


def dirt(repo: Path) -> list[str]:
    return [ln for ln in git(repo, "status", "--short").stdout.splitlines() if "_polaris/" in ln]


class Step4RunsOnARepoWithoutTodos(unittest.TestCase):
    """F2 — the contract does not require `state/todos.md`, and the prune must not need it."""

    def prepared(self):
        repo = host_repo()
        scenario = merged(repo)
        cockpit(repo)
        session_files(repo)
        return repo, tracker(repo, scenario)

    def test_the_read_only_block_reports_the_verdict(self):
        repo, env = self.prepared()
        out = run_block("end", "read-only", repo, **env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("PROVEN=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_the_apply_block_closes_the_thread_without_a_todos_file(self):
        repo, env = self.prepared()
        self.assertFalse((repo / "_polaris" / "state" / "todos.md").exists())
        out = run_block("end", "--apply", repo, **env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())
        self.assertIn('"todo": "skipped"', out.stdout)

    def test_the_apply_block_still_moves_the_row_when_the_file_is_there(self):
        repo, env = self.prepared()
        todos = seed_state(repo, "todos.md")
        written(todos, "| `feat/b` — chiude #77 | | y |", "W36")
        out = run_block("end", "--apply", repo, **env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("`feat/b`", todos.read_text().split("## Completed")[1])


class Step5RunsAndLeavesNothingBehind(unittest.TestCase):
    def test_the_block_lands_the_files_that_exist_and_skips_the_ones_that_do_not(self):
        """A missing weekly plan or ledger must not take the handoff down with it."""
        repo = host_repo()
        paths = session_files(repo)
        out = run_block("end", '"$SC" --end', repo)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        for path in paths:
            rel = str(path.relative_to(repo))
            self.assertEqual(git(repo, "show", f"HEAD:{rel}").returncode, 0, f"{rel} not landed")
        self.assertEqual(dirt(repo), [])

    def test_a_hook_that_refuses_the_commit_leaves_a_clean_index_and_a_full_spool(self):
        """F1 — undeclared branch protection: honest failure, but nothing left staged."""
        repo = host_repo()
        paths = session_files(repo)
        hook = repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        run_block("end", '"$SC" --end', repo)
        staged = git(repo, "diff", "--cached", "--name-only").stdout
        self.assertNotIn("_polaris/", staged, "a staged handoff is swallowed by the next commit")
        spool = repo / ".git" / "polaris-deferred"
        for path in paths:
            self.assertTrue((spool / path.relative_to(repo)).is_file(), f"{path.name} not spooled")


class TheOtherBlocksRun(unittest.TestCase):
    def test_recent_context_writes_into_the_shipped_cockpit(self):
        repo = host_repo()
        cockpit(repo)
        out = run_block("end", '"$RC" "$CURRENT"', repo)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertIn("### ", body.split("## Recent Context")[1])

    def test_the_lane_phase_block_degrades_on_a_repo_with_no_remote(self):
        repo = host_repo()
        out = run_block("end", "classificazione prima dell'handoff", repo)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("nessun remote", out.stdout)


if __name__ == "__main__":
    unittest.main()
