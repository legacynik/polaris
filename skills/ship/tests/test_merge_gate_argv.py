"""The one merge call must be a plain merge, never GitHub's native auto-merge.

`gh pr merge --auto` arms auto-merge, which GitHub completes later on whatever head is there
then, without re-running any gate this skill checked. The argv is what the external tracker
receives, so it is asserted at that boundary.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_gate.py"
spec = importlib.util.spec_from_file_location("merge_gate_argv", SCRIPT)
mg = importlib.util.module_from_spec(spec)
sys.modules["merge_gate_argv"] = mg
spec.loader.exec_module(mg)

READY = {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
         "statusCheckRollup": [{"name": "ci", "conclusion": "SUCCESS", "isRequired": True}]}


class TheMergeCall(unittest.TestCase):
    def test_a_ready_pr_is_merged_with_a_plain_squash_never_auto_merge(self):
        sent = []
        mg.gh_merge("7", "o/r", lambda argv: sent.append(argv) or 0, view_fn=lambda p, r: READY)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][:4], ["gh", "pr", "merge", "7"])
        self.assertIn("--squash", sent[0])
        self.assertNotIn("--auto", sent[0])


if __name__ == "__main__":
    unittest.main()
