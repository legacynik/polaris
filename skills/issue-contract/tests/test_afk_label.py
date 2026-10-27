"""The afk:human label must land when the work is left to a person.

Observed: an issue the owner asked to keep for a person was filed with no human label. The
skill only said "infer the AFK label from repository conventions", the product config named
none, and a repository can hold several look-alike labels (afk:human, ready-for-human,
afk:eligible, agent-ready). These tests drive the public CLI with the label list the tracker
returns (`gh label list --json name`) and the issue the tracker returns (`gh issue view --json
labels`), so no network is needed and nothing is mocked.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "afk_label.py"
PRODUCT_LABELS = ["bug", "afk:eligible", "afk:human", "ready-for-human", "agent-ready"]


class Repo:
    """A throwaway working directory holding what the tracker and the config would hold."""

    def __init__(self, labels, config=None):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "labels.json").write_text(json.dumps([{"name": n} for n in labels]))
        if config is not None:
            (self.dir / "_polaris").mkdir()
            (self.dir / "_polaris" / "config.yml").write_text(config)

    def run(self, mode, human, issue_labels=None):
        argv = [sys.executable, str(SCRIPT), mode, "--human", human, "--labels", "labels.json"]
        if issue_labels is not None:
            (self.dir / "issue.json").write_text(json.dumps({"labels": [{"name": n} for n in issue_labels]}))
            argv += ["--issue", "issue.json"]
        return subprocess.run(argv, cwd=self.dir, capture_output=True, text=True, timeout=30)


CONFIG = """tracker:
  github_repo: owner/repo
  afk_human: "needs-a-person"   # the label for work a person must do
  afk_agent: auto-ok
bugfix:
  tests: "pytest"
"""


class PickTheLabel(unittest.TestCase):
    def test_work_left_to_a_person_gets_the_repository_human_label(self):
        done = Repo(PRODUCT_LABELS).run("pick", "yes")
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "afk:human"), done.stderr)

    def test_the_config_names_the_label_and_wins_over_look_alikes(self):
        done = Repo(PRODUCT_LABELS + ["needs-a-person", "auto-ok"], CONFIG).run("pick", "yes")
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "needs-a-person"), done.stderr)

    def test_a_configured_label_the_repository_lacks_refuses_instead_of_substituting(self):
        done = Repo(PRODUCT_LABELS, CONFIG).run("pick", "yes")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(done.stdout.strip(), "")
        self.assertIn("needs-a-person", done.stderr)

    def test_a_repository_without_any_human_label_refuses_and_names_the_label_to_create(self):
        done = Repo(["bug", "afk:eligible"]).run("pick", "yes")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("afk:human", done.stderr)

    def test_agent_claimable_work_gets_the_agent_label(self):
        done = Repo(PRODUCT_LABELS).run("pick", "no")
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "afk:eligible"), done.stderr)

    def test_a_repository_with_no_afk_labels_gets_no_agent_label(self):
        done = Repo(["bug", "enhancement"]).run("pick", "no")
        self.assertEqual((done.returncode, done.stdout.strip()), (0, ""), done.stderr)


class VerifyTheCreatedIssue(unittest.TestCase):
    def test_an_issue_carrying_the_human_label_passes(self):
        done = Repo(PRODUCT_LABELS).run("verify", "yes", ["bug", "afk:human"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_an_issue_filed_without_the_human_label_fails_and_names_it(self):
        done = Repo(PRODUCT_LABELS).run("verify", "yes", ["bug"])
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("afk:human", done.stdout + done.stderr)

    def test_an_issue_that_is_both_human_and_agent_claimable_fails(self):
        done = Repo(PRODUCT_LABELS).run("verify", "yes", ["afk:human", "afk:eligible"])
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("afk:eligible", done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
