"""PM-C / D2 — a thread leaves `## Open` only against proven merge truth.

Replaces the manual step `/end` carried while removal was parked: *«la rimozione AUTOMATICA è
parcheggiata... `merge_truth` risponde `None` quando il ref locale del branch non esiste più»*.
The answer to that finding is not a remover that trusts `bool(merged)`: it is a verdict that asks
the TRACKER for the state and the REPO for reachability, and refuses to act when either is silent.

Fail-closed on purpose: one candidate whose state cannot be read blocks the whole run. A pruner
that removes four lanes and silently skips the fifth is exactly the "success that removed nothing"
this replaces, inverted.
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from host_repo import LOGIN, PKG, git, host_repo, run_script, seed_state, written

MISSING = "0" * 40


def merged_lane(repo: Path, keep: bool = False) -> tuple[str, str]:
    """A real merged branch: (head oid, merge commit oid). `keep` leaves the branch reusable."""
    git(repo, "switch", "-qc", "feat/b")
    (repo / "b.md").write_text("b\n")
    git(repo, "add", "b.md")
    git(repo, "commit", "-qm", "b")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge b", "feat/b")
    merge = git(repo, "rev-parse", "HEAD").stdout.strip()
    if not keep:
        git(repo, "branch", "-qD", "feat/b")
    return head, merge


def cockpit(repo: Path) -> Path:
    """The shipped template with two lanes placed by the shipped writer — built once per repo."""
    path = repo / "_polaris" / "state" / "current.md"
    if path.is_file() and "feat/b" in path.read_text():
        return path
    path = seed_state(repo, "current.md")
    written(path, "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02")
    written(path, "- `feat/a` (acme-api) — nessuna citazione · since 2026-09-01")
    return path


def todos(repo: Path) -> Path:
    path = seed_state(repo, "todos.md")
    written(path, "| `feat/b` — chiude #77 | | y |", "W36")
    return path


def log_of(repo: Path) -> Path:
    """Today's append-only session log — seeded once, then only ever read or appended to."""
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / "2026-09-04-@acme-dev.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text("## 18:00 — session end · lane chiusa\n- Files: x\n")
    return path


def prune(repo: Path, scenario: dict, *extra: str) -> subprocess.CompletedProcess:
    """Run the shipped pruner with the fake tracker on PATH, as `/end` calls it."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "gh").write_text(f'#!/bin/sh\nexec python3 "{PKG / "tests" / "fake_gh.py"}" "$@"\n')
    (shim / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}",
           "POLARIS_FAKE_GH": json.dumps(scenario)}
    return run_script("end", "prune_threads.py", str(cockpit(repo)), "--log", str(log_of(repo)),
                      "--todos", str(todos(repo)), "--owner", LOGIN, "--now", "2026-09-04",
                      *extra, cwd=str(repo), env=env)


def pr(head: str, merge: str, name: str = "feat/b", state: str = "MERGED") -> dict:
    return {"pr": {"77": {"state": state, "mergeCommit": {"oid": merge},
                          "headRefOid": head, "headRefName": name}}}


class ProvenMergeRemovesTheThread(unittest.TestCase):
    def test_the_lane_leaves_open_and_its_verdict_lands_in_the_session_log(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        out = prune(repo, pr(head, merge), "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertNotIn("feat/b", body, "closing means removing")
        self.assertIn("feat/a", body, "a thread citing nothing is never a candidate")
        self.assertIn("feat/b", log_of(repo).read_text(), "the verdict follows the thread")
        self.assertIn("MERGED", log_of(repo).read_text())

    def test_the_session_log_only_grows(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        before = log_of(repo).read_text()
        prune(repo, pr(head, merge), "--apply")
        after = log_of(repo).read_text()
        self.assertTrue(after.startswith(before), "the log is append-only, never rewritten")
        self.assertGreater(len(after), len(before), "the verdict is written down, not implied")
        self.assertEqual(after.count("## "), before.count("## "), "entries never decrease")

    def test_the_todo_row_moves_to_completed(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        prune(repo, pr(head, merge), "--apply")
        done = (repo / "_polaris" / "state" / "todos.md").read_text().split("## Completed")[1]
        self.assertIn("`feat/b`", done)

    def test_without_apply_it_only_reports(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        out = prune(repo, pr(head, merge))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("PROVEN=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())


class UnprovenTruthKeepsTheThread(unittest.TestCase):
    def test_a_merge_this_checkout_cannot_see_is_ambiguous(self):
        repo = host_repo()
        out = prune(repo, pr(MISSING, MISSING), "--apply")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("AMBIGUOUS=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_a_branch_reused_after_the_merge_is_ambiguous(self):
        repo = host_repo()
        head, merge = merged_lane(repo, keep=True)
        git(repo, "switch", "-q", "feat/b")
        (repo / "c.md").write_text("c\n")
        git(repo, "add", "c.md")
        git(repo, "commit", "-qm", "riuso")
        git(repo, "switch", "-q", "main")
        out = prune(repo, pr(head, merge), "--apply")
        self.assertIn("AMBIGUOUS=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_an_open_pr_is_not_a_closed_thread(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        out = prune(repo, pr(head, merge, state="OPEN"), "--apply")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("OPEN=", out.stdout)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())


class ASilentTrackerBlocksEverything(unittest.TestCase):
    """gh absent, erroring, rate-limited or answering nothing: no removal, exit 2, named line."""

    def test_a_tracker_error_names_the_line_and_removes_nothing(self):
        repo = host_repo()
        out = prune(repo, {"pr": {"77": "__error__"}, "issue": {"77": "__error__"}}, "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("BLOCKED=", out.stdout)
        self.assertIn("feat/b", out.stdout, "the refusal must name the line it could not resolve")
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_one_blocked_candidate_blocks_the_provable_one_too(self):
        repo = host_repo()
        head, merge = merged_lane(repo)
        path = cockpit(repo)
        written(path, "- `feat/c` (acme-api) — chiude #79 · since 2026-09-03")
        scenario = pr(head, merge)
        scenario["pr"]["79"] = "__error__"
        scenario["issue"] = {"79": "__error__"}
        out = prune(repo, scenario, "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("BLOCKED=", out.stdout)
        self.assertIn("PROVEN=", out.stdout, "the provable one is still reported, just not applied")
        self.assertIn("feat/b", path.read_text(), "fail-closed: a partial prune is not a prune")

    def test_no_gh_at_all_is_a_refusal_not_a_pass(self):
        repo = host_repo()
        out = run_script("end", "prune_threads.py", str(cockpit(repo)), "--log", str(log_of(repo)),
                         "--owner", LOGIN, "--now", "2026-09-04", "--apply",
                         cwd=str(repo), env={"PATH": "/nonexistent", "HOME": str(repo.parent)})
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("BLOCKED=", out.stdout, "an absent tracker is a refusal with a reason")
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())


class AClosedIssueIsNotAMergedPr(unittest.TestCase):
    def test_a_completed_issue_cited_as_an_issue_closes_the_thread(self):
        repo = host_repo()
        out = prune(repo, {"issue": {"77": {"state": "CLOSED", "stateReason": "COMPLETED"}}},
                    "--apply")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertNotIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_not_planned_is_not_completed(self):
        repo = host_repo()
        out = prune(repo, {"issue": {"77": {"state": "CLOSED", "stateReason": "NOT_PLANNED"}}},
                    "--apply")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("feat/b", (repo / "_polaris" / "state" / "current.md").read_text())

    def test_a_thread_citing_a_pr_never_falls_back_to_the_issue(self):
        repo = host_repo()
        path = seed_state(repo, "current.md")
        written(path, "- `feat/b` (acme-api) — attende PR 77 · since 2026-09-02")
        out = prune(repo, {"issue": {"77": {"state": "CLOSED", "stateReason": "COMPLETED"}}},
                    "--apply")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("BLOCKED=", out.stdout, "a PR citation is resolved as a PR or not at all")
        self.assertIn("feat/b", path.read_text())


class TheScriptChecksItself(unittest.TestCase):
    def test_selfcheck_is_a_real_check(self):
        out = run_script("end", "prune_threads.py", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
