"""D4, D6 — the checkpoint gates: overwrite, content-not-mtime, a capped harvest, a ticked plan.

`polaris-os#202` AC1: two `/update` on one thread from two sessions leave ONE line in the cockpit
and TWO entries in the session log. `#84`: `verify` must read the cockpit's CONTENT — a bare
`touch` fools an mtime gate. `#89`: the first harvest of the day must not read a shared multi-panel
scratch from offset 0. `#85`: plan-tick is RESTORED, and a gate proves it.

The overwrite case runs the bash block the shipped `update/SKILL.md` carries, so a body that stops
calling `state_upsert.py` fails here instead of passing.
"""
from __future__ import annotations

import subprocess
import unittest
from datetime import date
from pathlib import Path

from host_repo import LOGIN, env_for, host_repo, run_block, run_script, seed_state

TODAY = date.today().isoformat()


def session_log(repo) -> Path:
    return repo / "_polaris" / "team" / LOGIN / "sessions" / f"{TODAY}-@{LOGIN}.md"


def checkpoint(repo, *args: str) -> subprocess.CompletedProcess:
    return run_script("update", "checkpoint.sh", *args, cwd=str(repo), env=env_for(repo))


class OneLinePerThread(unittest.TestCase):
    """AC1 — the cockpit is state; the session log is the ledger."""

    def test_two_sessions_on_one_thread_leave_one_cockpit_line_and_two_log_entries(self):
        repo = host_repo()
        log = session_log(repo)
        for hour in ("10:00", "17:00"):
            out = run_block("update", '"$UP" thread', repo)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            with log.open("a") as fh:
                fh.write(f"## {hour} — checkpoint\n- Key context: x\n- Files: y\n")
        body = (repo / "_polaris" / "state" / "current.md").read_text()
        self.assertEqual(body.count("<branch>"), 1, "the second update replaced the first line")
        stamps = [ln for ln in body.splitlines() if ln.startswith("Updated:")]
        self.assertEqual(len(stamps), 1, f"the cockpit is state, not a ledger: {stamps}")
        entries = [ln for ln in log.read_text().splitlines() if ln.startswith("## ")]
        self.assertEqual(len(entries), 2, "the session log is the ledger and always appends")

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
        current.write_text(f"Updated: {TODAY} — @{LOGIN}\n\n## Open\n\n- `a` — x\n")
        out = checkpoint(repo, "verify")
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_every_bypass_this_gate_closes_has_its_own_fixture(self):
        out = run_script("update", "checkpoint.sh", "--selfcheck")
        self.assertEqual(out.returncode, 0, out.stdout)
        for bypass in ("bypass 1", "bypass 2", "bypass 3", "no checkpoint of ours"):
            self.assertIn(bypass, out.stdout, f"no fixture forces {bypass}")
        self.assertIn("11 passed", out.stdout, "polaris-os#84 owes at least 2 more cases than 7")

    def test_a_cockpit_redated_by_hand_without_a_checkpoint_is_refused(self):
        """The date-only gate passed this; the run binding does not."""
        repo, current = self.prepared()
        current.write_text(f"Updated: {TODAY} — @{LOGIN}\n\n## Open\n\n- `a` — x\n")
        out = checkpoint(repo, "verify", "un titolo che questa run non ha mai scritto")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("wrote no checkpoint", out.stdout)

    def test_a_cockpit_with_no_updated_line_is_refused(self):
        repo, current = self.prepared()
        current.write_text("## Open\n\n- `a` — x\n")
        self.assertEqual(checkpoint(repo, "verify").returncode, 1)


class TheHarvestIsCapped(unittest.TestCase):
    """#89 — a shared scratch is mostly other panels' flow; own lines are never lost."""

    def scratch(self, repo, own: int, foreign: int) -> Path:
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
        self.scratch(repo, own=30, foreign=120)
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
        self.scratch(repo, own=30, foreign=0)
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
            f"Updated: {TODAY} — @{LOGIN}\n\n## Open\n\n- `a` — x\n")
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
        repo = host_repo()
        todos = seed_state(repo, "todos.md")
        todos.write_text("## Active\n\n- #11 — primo giro · Added: W32\n")
        out = run_script("update", "state_upsert.py", "week", str(todos), "--week", "W36",
                         input="- #11 — secondo giro\n")
        self.assertEqual(out.returncode, 0, out.stderr)
        body = todos.read_text()
        self.assertIn("secondo giro", body)
        self.assertIn("Added: W32", body)
        self.assertNotIn("Added: W36", body)
        self.assertEqual(body.count("#11"), 1)


if __name__ == "__main__":
    unittest.main()
