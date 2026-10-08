"""polaris-os#538 — a checkpoint removes what the tracker has proven done, and only that.

`/update` used to touch one line: its own lane. A panel that checkpoints and never reaches `/end`
therefore left the cockpit false: a lane whose pull request merged a day earlier still under
`## Open`, an issue already closed still second in `## Active Priorities`.

`checkpoint.sh reconcile` (script `state_reconcile.py`) is deliberately narrower than `/end`:
it removes a ONE-LINE entry, with nothing hanging under it, whose every citation is proven done,
and only if that exact line is still there when it writes. An entry with children, a citation of
another repository, abandoned work, anything unreadable: all of it waits for `/end`, which closes
by judgment. Everything outside a removed line stays byte-identical.
"""
from __future__ import annotations

import json
import os
import sys
import time
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, PKG, env_for, git, host_repo, run_script
from prune_fixture import merged_lane, pr

STAMP = "<!-- pol:priorities updated=2026-09-01 -->"
B = "- `feat/b` (acme-api) — chiude #77 · since 2026-09-02"
A = "- `feat/a` (acme-api) — nessuna citazione · since 2026-09-01"
P77 = "1. #77 chiudere la lane b"
STILL_OPEN = {"pr": {"77": {"state": "OPEN", "mergeCommit": None,
                            "headRefOid": "0" * 40, "headRefName": "feat/b"}}}
DOWN = {"pr": {"77": "__error__"}, "issue": {"77": "__error__"}}


def cockpit(repo: Path, priorities: list[str], lanes: list[str], newline: str = "\n") -> Path:
    """Written by hand, byte for byte: these cases are about what does NOT change."""
    body = ["Updated: 2026-09-03 — @acme-dev", "", "## Active Priorities", "", STAMP, *priorities,
            "", "## Open", "", *lanes, "", "## Recent Context", "", "- una sessione di ieri", ""]
    path = repo / "_polaris" / "state" / "current.md"
    path.write_bytes(newline.join(body).encode("utf-8"))
    return path


def session_log(repo: Path, body: str = "## 10:00 — checkpoint · una voce\n- Files: x\n") -> Path:
    path = repo / "_polaris" / "team" / LOGIN / "sessions" / f"{date.today().isoformat()}-@{LOGIN}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def reconcile(repo: Path, scenario: dict, every: str = "0", cwd: Path | None = None):
    """`checkpoint.sh reconcile` with the fake tracker on PATH, as the skill body calls it.

    `every` is the throttle window in minutes; the cases that are not about it switch it off."""
    shim = repo.parent / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "gh").write_text(f'#!/bin/sh\nexec python3 "{PKG / "tests" / "fake_gh.py"}" "$@"\n')
    (shim / "gh").chmod(0o755)
    env = {**env_for(repo), "PATH": f"{shim}:{os.environ['PATH']}",
           "POLARIS_FAKE_GH": json.dumps(scenario)}
    env.pop("POLARIS_RECONCILE_EVERY", None)
    if every:
        env["POLARIS_RECONCILE_EVERY"] = every
    return run_script("update", "checkpoint.sh", "reconcile", cwd=str(cwd or repo), env=env)


def proven_repo(priorities: list[str], lanes: list[str], newline: str = "\n"):
    repo = host_repo()
    head, merge = merged_lane(repo)
    path = cockpit(repo, priorities, lanes, newline)
    return repo, path, session_log(repo), pr({"head": head, "merge": merge})


def with_issue(scenario: dict, number: str, state: str) -> dict:
    scenario.setdefault("issue", {})[number] = {"state": state, "stateReason": None}
    return scenario


class WhatIsProvenDoneLeaves(unittest.TestCase):

    def test_a_merged_lane_and_the_priority_citing_it_leave_and_nothing_else_moves(self):
        repo, path, log, scenario = proven_repo(
            [P77, "2. scrivere la spec", "3. parlare con il cliente"], [B, A])
        before = path.read_text()
        out = reconcile(repo, scenario)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        expected = before.replace(B + "\n", "").replace(P77 + "\n", "") \
            .replace("2. scrivere la spec", "1. scrivere la spec") \
            .replace("3. parlare con il cliente", "2. parlare con il cliente")
        self.assertEqual(path.read_text(), expected, "something other than the two proven lines changed")
        self.assertIn(B, log.read_text(), "the whole line and its verdict follow the lane into the log")
        self.assertIn(P77, log.read_text())

    def test_the_stamp_keeps_the_day_end_last_ordered_the_work(self):
        repo, path, _, scenario = proven_repo([P77, "2. scrivere la spec"], [B])
        reconcile(repo, scenario)
        check = run_script("update", "state_priorities.py", "check", str(path), "--now", "2026-09-20")
        self.assertIn("PRIORITIES_STALE=19d", check.stdout)

    def test_a_second_run_changes_nothing(self):
        repo, path, log, scenario = proven_repo([P77], [B, A])
        reconcile(repo, scenario)
        before, logged = path.read_bytes(), log.read_bytes()
        reconcile(repo, scenario)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(log.read_bytes(), logged)

    def test_line_endings_a_bom_and_a_missing_final_newline_survive_byte_for_byte(self):
        repo, path, _, scenario = proven_repo([P77, "2. scrivere la spec"], [B, A], "\r\n")
        raw = b"\xef\xbb\xbf" + path.read_bytes().rstrip(b"\r\n")
        path.write_bytes(raw)
        reconcile(repo, scenario)
        expected = raw.replace((B + "\r\n").encode(), b"").replace((P77 + "\r\n").encode(), b"") \
            .replace(b"2. scrivere la spec", b"1. scrivere la spec")
        self.assertEqual(path.read_bytes(), expected)

    def test_numbers_that_were_not_a_plain_sequence_are_left_as_written(self):
        repo, path, _, scenario = proven_repo([P77, "5. scrivere la spec", "9. parlare con il cliente"], [A])
        before = path.read_text()
        reconcile(repo, scenario)
        self.assertEqual(path.read_text(), before.replace(P77 + "\n", ""))

    def test_qualified_headings_are_the_same_sections(self):
        repo, path, _, scenario = proven_repo([P77], [B])
        path.write_text(path.read_text().replace("## Open", "## Open — thread vivi")
                        .replace("## Active Priorities", "## Active Priorities — l'ordine del lavoro"))
        reconcile(repo, scenario)
        self.assertNotIn("#77", path.read_text())


class WhatIsNotProvenStays(unittest.TestCase):

    def unchanged(self, priorities, lanes, scenario_edit=None):
        repo, path, _, scenario = proven_repo(priorities, lanes)
        before = path.read_bytes()
        out = reconcile(repo, scenario_edit(scenario) if scenario_edit else scenario)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(path.read_bytes(), before, out.stdout)
        return out

    def test_a_silent_tracker_removes_nothing_and_the_checkpoint_goes_on(self):
        out = self.unchanged([P77], [B], lambda s: DOWN)
        self.assertIn("nothing removed", out.stdout)

    def test_an_unreadable_citation_keeps_its_own_line_and_not_the_one_beside_it(self):
        repo, path, _, scenario = proven_repo([P77, "2. #99 altra cosa"], [A])
        scenario["pr"]["99"] = "__error__"
        before = path.read_text()
        reconcile(repo, scenario)
        self.assertEqual(path.read_text(), before.replace(P77 + "\n", "").replace("2. #99", "1. #99"))

    def test_one_closed_and_one_open_citation_stay(self):
        self.unchanged(["1. #77 e #78 vanno insieme"], ["- `feat/b` (acme-api) — chiude #77, poi #78"],
                       lambda s: with_issue(s, "78", "OPEN"))

    def test_work_closed_as_not_planned_waits_for_end(self):
        """DEAD is a judgment about abandoned work. On a real cockpit two such lanes still carried
        a live warning in their prose."""
        out = self.unchanged([P77], [B], lambda s: {
            "issue": {"77": {"state": "CLOSED", "stateReason": "NOT_PLANNED"}}})
        self.assertIn("/end", out.stdout, "the output must say who decides it")

    def test_a_lane_with_anything_hanging_under_it_is_never_touched(self):
        """The verdict would read the head line; the child may cite work that is still open."""
        self.unchanged([], [B, "  - resta da fare: #78 (migrazione)", A], lambda s: with_issue(s, "78", "OPEN"))
        self.unchanged([], [B, "ATTENZIONE: non rilasciare prima del collaudo", "", A])
        self.unchanged([], [B, "", "    resume: vedi handoff di ieri", "", A])

    def test_a_priority_with_a_second_line_is_never_touched(self):
        self.unchanged([P77, "   e poi rilasciare con calma", "2. scrivere la spec"], [A])

    def test_prose_fences_and_sub_bullets_in_the_priorities_survive_a_removal(self):
        repo, path, _, scenario = proven_repo(
            ["Owner: @acme-dev — rivedere venerdì", P77, "2. scrivere la spec",
             "   - sotto-punto della spec", "```bash", "3. esempio in un blocco #77", "```", "+ punto col più"], [A])
        before = path.read_text()
        reconcile(repo, scenario)
        self.assertEqual(path.read_text(), before.replace(P77 + "\n", "")
                         .replace("2. scrivere la spec", "1. scrivere la spec"))

    def test_another_repositorys_number_and_an_anchor_are_not_ours_to_prove(self):
        self.unchanged(["1. attendere altro-org/altro-repo#77", "2. vedi docs/guida.md#77"],
                       ["- `feat/x` (acme-api) — aspetta acme/billing#77"])

    def test_without_an_entry_in_todays_log_nothing_is_removed(self):
        for body in (None, "```\n## 10:00 — dentro un blocco\n```\n", "appunti senza voce\n"):
            repo, path, log, scenario = proven_repo([P77], [B])
            log.write_text(body) if body else log.unlink()
            before = path.read_bytes()
            out = reconcile(repo, scenario)
            self.assertEqual(path.read_bytes(), before, f"removed with the log at {body!r}")
            self.assertEqual(out.returncode, 0)

    def test_a_log_that_cannot_be_written_removes_nothing(self):
        repo, path, log, scenario = proven_repo([P77], [B])
        before = path.read_bytes()
        log.chmod(0o444)
        try:
            out = reconcile(repo, scenario)
        finally:
            log.chmod(0o644)
        self.assertEqual(path.read_bytes(), before, "a lane left with no verdict written anywhere")
        self.assertIn("nothing removed", out.stdout)

    def test_a_merge_this_checkout_cannot_see_stays(self):
        self.unchanged([P77], [B], lambda s: pr({"head": "0" * 40, "merge": "1" * 40}))


class AnotherWriterIsNeverOverwritten(unittest.TestCase):
    """The tracker takes a minute to answer. What another panel wrote meanwhile is the truth."""

    def module(self):
        sys.path.insert(0, str(PKG / "skills" / "update" / "scripts"))
        import state_reconcile
        return state_reconcile

    def test_a_lane_rewritten_while_the_tracker_answered_stays(self):
        _, path, _, _ = proven_repo([], [B, A])
        path.write_text(path.read_text().replace(B, "- `feat/b` (acme-api) — #77 landed, ora serve #80"))
        before = path.read_bytes()
        self.assertEqual(self.module().apply(path, [("## Open", B, "PR #77 MERGED")]), [])
        self.assertEqual(path.read_bytes(), before)

    def test_a_note_hung_under_the_lane_meanwhile_keeps_it(self):
        _, path, _, _ = proven_repo([], [B, A])
        path.write_text(path.read_text().replace(B, B + "\n  - non chiudere: manca la migrazione"))
        before = path.read_bytes()
        self.assertEqual(self.module().apply(path, [("## Open", B, "PR #77 MERGED")]), [])
        self.assertEqual(path.read_bytes(), before)

    def test_priorities_another_panel_just_reordered_keep_their_new_order(self):
        _, path, _, _ = proven_repo([P77, "2. vecchio secondo"], [A])
        path.write_text(path.read_text().replace(
            P77 + "\n2. vecchio secondo", "1. NUOVA prima\n2. #77 chiudere la lane b\n3. NUOVA terza"))
        self.module().apply(path, [("## Active Priorities", P77, "PR #77 MERGED")])
        self.assertIn("1. NUOVA prima\n2. #77 chiudere la lane b\n3. NUOVA terza\n", path.read_text(),
                      "the line this run judged is gone: the one there now was written by someone else")


class ACheckpointStaysCheap(unittest.TestCase):

    def test_only_removals_and_one_count_reach_the_output(self):
        """Measured on a real cockpit: 14 lanes printed in full at every checkpoint."""
        repo, _, _, scenario = proven_repo([P77], [B, A, "- `feat/c` (acme-api) — aspetta #78"])
        out = reconcile(repo, with_issue(scenario, "78", "OPEN")).stdout
        self.assertLessEqual(len(out.splitlines()), 4, out)
        self.assertIn("2 removed", out)

    def test_a_second_run_inside_the_window_asks_the_tracker_nothing(self):
        """Measured: 109 seconds for 13 lanes. Once per window is enough for every panel."""
        repo, path, _, scenario = proven_repo([], [B])
        reconcile(repo, STILL_OPEN, every="")                    # the window opens here
        before = path.read_bytes()
        out = reconcile(repo, scenario, every="")
        self.assertEqual(path.read_bytes(), before, "the tracker was asked again inside the window")
        self.assertIn("skipped", out.stdout)

    def test_a_run_that_learned_nothing_does_not_open_the_window(self):
        repo, path, _, scenario = proven_repo(["1. scrivere la spec"], [B])
        reconcile(repo, DOWN, every="")
        reconcile(repo, scenario, every="")
        self.assertNotIn("feat/b", path.read_text(), "a run that learned nothing postponed the next one")

    def test_one_number_nobody_can_read_does_not_keep_the_window_shut(self):
        """A colour code or a step number reads as a citation forever: it must not cost a
        tracker round at every checkpoint of every panel."""
        repo, _, _, scenario = proven_repo([], ["- `feat/c` (acme-api) — colore #336699", B])
        reconcile(repo, STILL_OPEN, every="")
        self.assertIn("skipped", reconcile(repo, scenario, every="").stdout)

    def test_a_stamp_from_the_future_does_not_silence_it(self):
        repo, path, _, scenario = proven_repo([], [B])
        stamp = repo / ".git" / "polaris-reconcile"
        stamp.write_text("")
        os.utime(stamp, (time.time() + 10 ** 7,) * 2)
        reconcile(repo, scenario, every="")
        self.assertNotIn("feat/b", path.read_text())

    def test_the_window_is_one_for_every_worktree_of_the_repo(self):
        repo, _, _, scenario = proven_repo([], [B])
        other = repo.parent / "wt-other"
        git(repo, "worktree", "add", "-q", str(other), "-b", "lane-x")
        reconcile(repo, STILL_OPEN, every="")
        log = other / "_polaris" / "team" / LOGIN / "sessions" / f"{date.today().isoformat()}-@{LOGIN}.md"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("## 11:00 — altro pannello\n")
        self.assertIn("skipped", reconcile(repo, scenario, every="", cwd=other).stdout)

    def test_it_exits_zero_even_where_the_login_cannot_be_resolved(self):
        repo, path, _, _ = proven_repo([], [B])
        before = path.read_bytes()
        git(repo, "config", "--unset", "polaris.login")
        out = reconcile(repo, DOWN)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(path.read_bytes(), before)


class TwoBranchesOneSessionLog(unittest.TestCase):
    """Every panel commits its log on the branch it sits on, so one day's file is born twice."""

    LOG = f"_polaris/team/{LOGIN}/sessions/2026-09-04-@{LOGIN}.md"
    RULE = "_polaris/team/*/sessions/*.md merge=union\n"

    def two_branches(self, attribute: bool) -> tuple[Path, int]:
        repo = host_repo()
        if attribute:
            (repo / ".gitattributes").write_text(self.RULE)
            git(repo, "add", ".gitattributes")
            git(repo, "commit", "-qm", "attributes")
        for branch, entry in (("lane-a", "## 10:00 — panel A\n"), ("lane-b", "## 11:00 — panel B\n")):
            git(repo, "switch", "-qc", branch, "main")
            (repo / self.LOG).parent.mkdir(parents=True, exist_ok=True)   # git drops an emptied dir
            (repo / self.LOG).write_text(entry)
            git(repo, "add", self.LOG)
            git(repo, "commit", "-qm", branch)
        git(repo, "switch", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "-m", "a", "lane-a")
        return repo, git(repo, "merge", "--no-ff", "-m", "b", "lane-b").returncode

    def test_with_the_union_attribute_both_entries_survive_and_nothing_conflicts(self):
        repo, code = self.two_branches(attribute=True)
        self.assertEqual(code, 0, "two panels' logs of one day conflicted")
        merged = (repo / self.LOG).read_text()
        self.assertIn("panel A", merged)
        self.assertIn("panel B", merged)
        self.assertNotIn("<<<<<<<", merged)

    def test_without_it_the_same_merge_conflicts(self):
        _, code = self.two_branches(attribute=False)
        self.assertNotEqual(code, 0, "the control must conflict, or the case above proves nothing")

    def hint(self, repo: Path) -> str:
        out = run_script("update", "checkpoint.sh", "prepare", cwd=str(repo), env=env_for(repo)).stdout
        return next((ln for ln in out.splitlines() if ln.startswith("LOG_MERGE=")), "")

    def adopts_the_printed_line(self, repo: Path) -> None:
        missing = self.hint(repo)
        self.assertIn("LOG_MERGE=missing", missing)
        self.assertFalse((repo / ".gitattributes").exists(), "prepare wrote a tracked file of the host repo")
        (repo / ".gitattributes").write_text(missing.split(".gitattributes: ", 1)[1] + "\n")
        self.assertEqual(self.hint(repo), "LOG_MERGE=union")

    def test_the_line_prepare_prints_is_the_line_that_works_and_it_writes_nothing(self):
        self.adopts_the_printed_line(host_repo())

    def test_the_line_also_works_where_the_contract_root_is_the_repo_root(self):
        repo = host_repo()
        git(repo, "mv", "_polaris/config.yml", "config.yml")
        git(repo, "mv", "_polaris/state", "state")
        self.adopts_the_printed_line(repo)


if __name__ == "__main__":
    unittest.main()
