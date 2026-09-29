"""D4, D6 — the checkpoint gates: overwrite, content-not-mtime, a capped harvest, a ticked plan.

`polaris-os#202` AC1: two `/update` on one thread from two sessions leave ONE line in the cockpit
and TWO entries in the session log. `#84`: `verify` must read the cockpit's CONTENT — a bare
`touch` fools an mtime gate. `#89`: the first harvest of the day must not read a shared multi-panel
scratch from offset 0. `#85`: plan-tick is RESTORED, and a gate proves it.

The overwrite case runs the bash block the shipped `update/SKILL.md` carries, so a body that stops
calling `state_upsert.py` fails here instead of passing.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, env_for, host_repo, run_block, run_script, seed_state, written

def today() -> str:
    """Read the clock at USE, never at import: the shipped scripts call `date +%F` when they run,
    and a module-level constant disagrees with them for one run a day, at midnight."""
    return date.today().isoformat()


def session_log(repo) -> Path:
    return repo / "_polaris" / "team" / LOGIN / "sessions" / f"{today()}-@{LOGIN}.md"


def checkpoint(repo, *args: str) -> subprocess.CompletedProcess:
    return run_script("update", "checkpoint.sh", *args, cwd=str(repo), env=env_for(repo))


class OneLinePerThread(unittest.TestCase):
    """AC1 — the cockpit is state; the session log is the ledger."""

    def test_two_sessions_on_one_thread_leave_one_cockpit_line_and_two_log_entries(self):
        repo = host_repo()
        log = session_log(repo)
        for hour in ("10:00", "17:00"):
            out = run_block("update", '"$UP" thread', repo,
                            LANE_LINE=f"- `memory` — branch `main`; checkpoint {hour} · since 2026-09-29")
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            with log.open("a") as fh:
                fh.write(f"## {hour} — checkpoint\n- Key context: x\n- Files: y\n")
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertEqual(body.count("`memory`"), 1, "the second update replaced the first line")
        self.assertIn("checkpoint 17:00", body)
        stamps = [ln for ln in body.splitlines() if ln.startswith("Updated:")]
        self.assertEqual(len(stamps), 1, f"the cockpit is state, not a ledger: {stamps}")
        entries = [ln for ln in log.read_text().splitlines() if ln.startswith("## ")]
        self.assertEqual(len(entries), 2, "the session log is the ledger and always appends")

    def test_a_new_lane_adds_one_line_without_touching_the_existing_lane(self):
        repo = host_repo()
        first = run_block("update", '"$UP" thread', repo,
                          LANE_LINE="- `memory` — branch `main`; first · since 2026-09-29")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = run_block("update", '"$UP" thread', repo,
                           LANE_LINE="- `billing` — branch `main`; new · since 2026-09-29")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertEqual(body.count("`memory`"), 1)
        self.assertEqual(body.count("`billing`"), 1)

    def test_nothing_material_means_nothing_written(self):
        repo = host_repo()
        before = (repo / "_polaris" / "state" / "current.md").read_bytes()
        checkpoint(repo, "prepare")
        self.assertEqual((repo / "_polaris" / "state" / "current.md").read_bytes(), before)
        diff = subprocess.run(["git", "-C", str(repo), "diff", "--stat", "--",
                               "_polaris/state/current.md"], capture_output=True, text=True)
        self.assertEqual(diff.stdout.strip(), "")


class VerifyReadsContent(unittest.TestCase):
    """#84 — a touched cockpit with no checkpoint in it must fail, mtime notwithstanding."""

    def prepared(self):
        repo = host_repo()
        log = session_log(repo)
        log.write_text("## 10:00 — probe\n- Key context: x\n- Files: y\n")
        subprocess.run(["git", "-C", str(repo), "add", "--", str(log)], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "checkpoint"], check=True)
        current = repo / "_polaris" / "state" / "current.md"
        return repo, current

    def test_a_bare_touch_on_a_stale_cockpit_is_refused(self):
        repo, current = self.prepared()
        current.write_text("Updated: 2026-08-30 — @acme-dev\n\n## Open\n\n- `a` — x\n")
        subprocess.run(["touch", str(current)], check=True)
        out = checkpoint(repo, "verify")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("Updated:", out.stdout)

    def test_todays_checkpoint_in_the_updated_line_passes(self):
        repo, current = self.prepared()
        current.write_text(f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n")
        out = checkpoint(repo, "verify")
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_every_bypass_this_gate_closes_has_its_own_fixture(self):
        out = run_script("update", "checkpoint.sh", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout)
        for bypass in ("bypass 1", "bypass 2", "bypass 3", "no checkpoint of ours"):
            self.assertIn(bypass, out.stdout, f"no fixture forces {bypass}")
        cases = int(re.search(r"selfcheck: (\d+) passed", out.stdout).group(1))
        self.assertGreaterEqual(cases, 9, "polaris-os#84 owes at least 2 more cases than the 7")

    def test_a_cockpit_redated_by_hand_without_a_checkpoint_is_refused(self):
        """The date-only gate passed this; the run binding does not."""
        repo, current = self.prepared()
        current.write_text(f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n")
        out = checkpoint(repo, "verify", "un titolo che questa run non ha mai scritto")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("wrote no checkpoint", out.stdout)

    def test_a_cockpit_with_no_updated_line_is_refused(self):
        repo, current = self.prepared()
        current.write_text("## Open\n\n- `a` — x\n")
        self.assertEqual(checkpoint(repo, "verify").returncode, 1)


class DurableArchiveGate(unittest.TestCase):
    def test_prepare_refuses_a_foreign_unstaged_archive_before_editing(self):
        repo = host_repo()
        archive = repo / "_polaris" / "lessons.md"
        archive.write_text("## Old lesson\n")
        subprocess.run(["git", "-C", str(repo), "add", "--", str(archive)], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "old lesson"], check=True)
        archive.write_text(archive.read_text() + "Foreign unstaged edit.\n")

        out = checkpoint(repo, "prepare")
        self.assertEqual(out.returncode, 2, out.stdout)
        self.assertIn("ARCHIVE_DIRTY", out.stdout + out.stderr)
        self.assertIn("Foreign unstaged edit.", archive.read_text())

    def test_every_lesson_pointer_must_be_committed(self):
        repo = host_repo()
        session_log(repo).write_text(
            "## 10:00 — two lessons\n- Key context: #lezione two reusable mistakes\n"
            "- Lesson: First rule\n- Lesson: Second rule\n- Files: _polaris/lessons.md\n"
        )
        archive = repo / "_polaris" / "lessons.md"
        archive.write_text(f"## {today()} — First rule (@{LOGIN})\n")
        subprocess.run(["git", "-C", str(repo), "add", "--", str(session_log(repo)), str(archive)], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "partial archive"], check=True)
        (repo / "_polaris" / "state" / "current.md").write_text(
            f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n"
        )
        partial = checkpoint(repo, "verify", "two lessons")
        self.assertEqual(partial.returncode, 1, partial.stdout)
        self.assertIn("Second rule", partial.stdout)

    def test_uncommitted_session_log_is_not_a_saved_checkpoint(self):
        repo = host_repo()
        session_log(repo).write_text("## 10:00 — unsaved checkpoint\n- Files: none\n")
        (repo / "_polaris" / "state" / "current.md").write_text(
            f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n"
        )
        unsaved = checkpoint(repo, "verify", "unsaved checkpoint")
        self.assertEqual(unsaved.returncode, 1, unsaved.stdout)
        self.assertIn("not committed", unsaved.stdout)

    def test_lesson_checkpoint_requires_a_committed_matching_record(self):
        repo = host_repo()
        title = "Live eval needs explicit opt-in"
        session_log(repo).write_text(
            f"## 10:00 — lesson checkpoint\n- Key context: #lezione {title}\n"
            f"- Lesson: {title}\n- Files: _polaris/lessons.md\n"
        )
        subprocess.run(["git", "-C", str(repo), "add", "--", str(session_log(repo))], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "checkpoint"], check=True)
        (repo / "_polaris" / "state" / "current.md").write_text(
            f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n"
        )
        missing = checkpoint(repo, "verify", "lesson checkpoint")
        self.assertEqual(missing.returncode, 1, missing.stdout)
        self.assertIn("lesson", missing.stdout.lower())

        archive = repo / "_polaris" / "lessons.md"
        archive.write_text(f"## {today()} — {title} (@{LOGIN})\nRule: opt in.\n")
        uncommitted = checkpoint(repo, "verify", "lesson checkpoint")
        self.assertEqual(uncommitted.returncode, 1, uncommitted.stdout)
        subprocess.run(["git", "-C", str(repo), "add", "--", str(archive)], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "archive lesson"], check=True)
        saved = checkpoint(repo, "verify", "lesson checkpoint")
        self.assertEqual(saved.returncode, 0, saved.stdout)
        archive.write_text(archive.read_text() + "Unsaved correction.\n")
        dirty = checkpoint(repo, "verify", "lesson checkpoint")
        self.assertEqual(dirty.returncode, 1, dirty.stdout)

    def test_decision_checkpoint_requires_a_committed_matching_record(self):
        repo = host_repo()
        title = "Keep one active plan per area"
        session_log(repo).write_text(
            f"## 10:00 — decision checkpoint\n- Key context: #decisione {title}\n"
            f"- Decision: {title}\n- Files: _polaris/decisions.md\n"
        )
        subprocess.run(["git", "-C", str(repo), "add", "--", str(session_log(repo))], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "checkpoint"], check=True)
        (repo / "_polaris" / "state" / "current.md").write_text(
            f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n"
        )
        missing = checkpoint(repo, "verify", "decision checkpoint")
        self.assertEqual(missing.returncode, 1, missing.stdout)
        self.assertIn("decision", missing.stdout.lower())

        archive = repo / "_polaris" / "decisions.md"
        archive.write_text(f"## {today()} — {title} (@{LOGIN})\nChose one plan.\n")
        uncommitted = checkpoint(repo, "verify", "decision checkpoint")
        self.assertEqual(uncommitted.returncode, 1, uncommitted.stdout)
        subprocess.run(["git", "-C", str(repo), "add", "--", str(archive)], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "archive decision"], check=True)
        saved = checkpoint(repo, "verify", "decision checkpoint")
        self.assertEqual(saved.returncode, 0, saved.stdout)


class TheHarvestIsCapped(unittest.TestCase):
    """#89 — a shared scratch is mostly other panels' flow; own lines are never lost."""

    def scratch(self, repo, mix: tuple) -> Path:
        own, foreign = mix
        path = repo / "_polaris" / "team" / LOGIN / "sessions" / "scratch"
        path.mkdir(parents=True, exist_ok=True)
        f = path / "flow.md"
        rows = [f"[sid-other-{i}] flusso di un altro pannello" for i in range(foreign)]
        for i in range(own):
            rows.insert(min(len(rows), (i + 1) * (foreign // max(own, 1))),
                        f"[sid-mine] mia riga {i}")
        f.write_text("\n".join(rows) + "\n")
        return f

    def test_an_eighty_percent_foreign_scratch_reads_under_the_cap(self):
        repo = host_repo()
        self.scratch(repo, (30, 120))
        out = checkpoint(repo, "harvest-slice", "sid-mine")
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
        self.assertLessEqual(len(lines), 40, f"read {len(lines)} lines of a 150-line scratch")
        self.assertEqual(sum(1 for ln in lines if "sid-mine" in ln), 30, "0 own-id loss")

    def test_an_own_line_last_in_a_foreign_scratch_is_still_harvested(self):
        repo = host_repo()
        path = repo / "_polaris" / "team" / LOGIN / "sessions" / "scratch"
        path.mkdir(parents=True, exist_ok=True)
        (path / "flow.md").write_text("\n".join(["[sid-other] x"] * 199 + ["[sid-mine] ultima"]))
        out = checkpoint(repo, "harvest-slice", "sid-mine")
        self.assertEqual(out.stdout.count("ultima"), 1, "the cap must not be positional")

    def test_a_single_panel_scratch_is_read_whole(self):
        repo = host_repo()
        self.scratch(repo, (30, 0))
        out = checkpoint(repo, "harvest-slice", "sid-mine")
        self.assertEqual(len([ln for ln in out.stdout.splitlines() if ln.strip()]), 30)


class ThePlanTickIsRestored(unittest.TestCase):
    """#85 — RESTORE is the declared state; this is the gate that proves it."""

    def weekly(self, repo) -> Path:
        week = date.today().strftime("%G-W%V")
        return repo / "_polaris" / "team" / LOGIN / "weeks" / f"{week}.md"

    def test_an_existing_weekly_plan_left_unticked_fails_verify(self):
        repo = host_repo()
        self.weekly(repo).write_text("# Week\n\n## Outcome\n\nx\n")
        subprocess.run(["touch", "-t", "202601010000", str(self.weekly(repo))], check=True)
        session_log(repo).write_text("## 10:00 — probe\n- Key context: x\n- Files: y\n")
        (repo / "_polaris" / "state" / "current.md").write_text(
            f"Updated: {today()} — @{LOGIN}\n\n## Open\n\n- `a` — x\n")
        out = checkpoint(repo, "verify")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("not ticked", out.stdout)

    def test_the_changelog_declares_restore_and_not_supersede(self):
        changelog = (Path(__file__).resolve().parents[2] / "CHANGELOG.md").read_text()
        self.assertIn("plan tick is back", changelog)
        self.assertNotIn("plan-tick superseded", changelog)


class TodosFollowTheThread(unittest.TestCase):
    """D4 — an update that cites a todo refreshes its row, and never re-stamps `Added:`."""

    def test_the_active_row_is_replaced_with_its_original_stamp(self):
        """The file is the SHIPPED template and the first row is placed by the SHIPPED writer."""
        repo = host_repo()
        todos = seed_state(repo, "todos.md")
        written(todos, "| #11 — primo giro | | ctx |", "W32")
        out = run_script("update", "state_upsert.py", "week", str(todos), "--week", "W36",
                         input="| #11 — secondo giro | | ctx |\n")
        self.assertEqual(out.returncode, 0, out.stderr)
        body = todos.read_text()
        self.assertIn("| #11 — secondo giro | W32 | ctx |", body)
        self.assertNotIn("W36", body)
        self.assertEqual(body.count("#11"), 1)

    def test_an_escaped_pipe_in_the_task_keeps_the_stamp_and_the_context(self):
        """A `\\|` is content: splitting on it shifted every later cell left and ate `Added`."""
        repo = host_repo()
        todos = seed_state(repo, "todos.md")
        written(todos, r"| `a\|b` — nome | | ctx |", "W32")
        run_script("update", "state_upsert.py", "week", str(todos), "--week", "W36",
                   input="| `a\\|b` — nuovo | | ctx2 |\n")
        body = todos.read_text()
        self.assertIn(r"| `a\|b` — nuovo | W32 | ctx2 |", body)
        self.assertEqual(body.count(r"a\|b"), 1)

    def test_update_may_refresh_a_row_but_never_create_one(self):
        repo = host_repo()
        todos = seed_state(repo, "todos.md")
        written(todos, "| #11 — primo | | ctx |", "W32")
        before = todos.read_text()
        out = run_script("update", "state_upsert.py", "week", str(todos), "--week", "W36",
                         "--no-add", input="| #99 — mai vista | | |\n")
        self.assertEqual(out.returncode, 2)
        self.assertIn("NO_SUCH_ROW", out.stderr)
        self.assertEqual(todos.read_text(), before)


if __name__ == "__main__":
    unittest.main()
