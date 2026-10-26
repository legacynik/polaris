"""implement works the current phase only (lowest open phase bead): its child tasks and the open
beads that block it.

Observed on the plan skill's feature gate (#603): tasks are children of their phase, and bd does
not pass a parent's blockers down to its children, so `bd ready --mol` lists every phase's tasks
while `critic` or an earlier phase is still open. A loop that takes "the first ready task" builds
phase 2 on top of an unfinished phase 1. These tests feed `pick` the JSON shapes of
`bd mol show --json` and `bd ready --mol --json` (bd 1.3.1); bd itself is not called.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from next_bead import held, pick  # noqa: E402


def issue(i, step=None, status="open", phase=None, title=None):
    meta = {"step": step} if step else None
    if phase is not None:
        meta["phase"] = phase
    return {"id": i, "status": status, "metadata": meta, "title": title or i}


def child(c, parent):
    return {"issue_id": c, "depends_on_id": parent, "type": "parent-child"}


def blocks(blocker, step):
    return {"issue_id": step, "depends_on_id": blocker, "type": "blocks"}


def ready(*ids, status="open"):
    return {"steps": [{"issue": {"id": i, "status": status}, "parallel_info": {"is_ready": True}}
                      for i in ids]}


MOL = {
    "issues": [issue("E"), issue("p1", "phase", phase=1), issue("p2", "phase", phase=2),
               issue("t1", "task"), issue("t2", "task")],
    "dependencies": [child("p1", "E"), child("p2", "E"), child("t1", "p1"), child("t2", "p2"),
                     blocks("p1", "p2")],
}


class NextBead(unittest.TestCase):
    def test_a_later_phase_task_bd_lists_as_ready_is_skipped(self):
        bead, skipped = pick(MOL, ready("t2", "t1"))
        self.assertEqual(bead, "t1")
        self.assertEqual(skipped, ["t2"])

    def test_nothing_of_the_current_phase_ready_means_no_bead_even_if_a_later_one_is(self):
        bead, skipped = pick(MOL, ready("t2"))
        self.assertIsNone(bead)
        self.assertEqual(skipped, ["t2"])

    def test_an_open_bead_blocking_the_current_phase_is_its_work(self):
        mol = {"issues": MOL["issues"] + [issue("f1", "task")],
               "dependencies": MOL["dependencies"] + [child("f1", "E"), blocks("f1", "p1")]}
        bead, _ = pick(mol, ready("f1", "t2"))
        self.assertEqual(bead, "f1")

    def test_tasks_come_in_plan_order_whatever_order_bd_lists_them(self):
        mol = {"issues": MOL["issues"] + [issue("E.1.2", "task"), issue("E.1.10", "task"),
                                          issue("E.1.1", "task")],
               "dependencies": MOL["dependencies"] + [child(t, "p1") for t in ("E.1.2", "E.1.10", "E.1.1")]}
        bead, _ = pick(mol, ready("E.1.10", "E.1.2", "E.1.1"))
        self.assertEqual(bead, "E.1.1")

    def test_a_claimed_bead_is_not_taken_again(self):
        bead, _ = pick(MOL, ready("t1", status="in_progress"))
        self.assertIsNone(bead)

    def test_a_bead_of_the_current_phase_left_in_progress_is_named_for_the_reaper(self):
        mol = {"issues": [issue("E"), issue("p1", "phase", phase=1), issue("t1", "task", "in_progress"),
                          issue("p2", "phase", phase=2), issue("t2", "task", "in_progress")],
               "dependencies": MOL["dependencies"]}
        self.assertEqual(held(mol), ["t1"])

    def test_once_phase_one_closes_phase_two_is_current(self):
        mol = {"issues": [issue("E"), issue("p1", "phase", "closed", 1), issue("p2", "phase", phase=2),
                          issue("t2", "task")], "dependencies": MOL["dependencies"]}
        bead, skipped = pick(mol, ready("t2"))
        self.assertEqual((bead, skipped), ("t2", []))

    def test_the_phase_beads_themselves_are_never_picked(self):
        bead, _ = pick(MOL, ready("p1"))
        self.assertIsNone(bead)

    def test_no_open_phase_means_no_bead(self):
        mol = {"issues": [issue("E"), issue("p1", "phase", "closed", 1)], "dependencies": []}
        self.assertEqual(pick(mol, ready()), (None, []))


if __name__ == "__main__":
    unittest.main()
