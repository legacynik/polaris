"""/start Step 2 — the contributor's own path, and the gate on whose it is.

Both blocks are read out of `start/SKILL.md` and run on a host repo built from the shipped
templates. A profile copied and never edited keeps the template's `github: octocat`; every
tracker query after that asks about the wrong person, and nothing fails. The gate is what stops
it, so the gate is what runs here.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from host_repo import LOGIN, host_repo, run_block

PROVISION = 'mkdir -p "$ROOT/team/$LOGIN/weeks"'
GATE = 'grep -q "^github: $LOGIN$"'


def profile(repo: Path, login: str = LOGIN) -> Path:
    return repo / "_polaris" / "team" / login / "profile.yml"


def with_profile(github: str) -> Path:
    repo = host_repo()
    profile(repo).write_text(f"github: {github}\nlanguage: en\n")
    return repo


class ProvisioningWritesOnlyYourOwnPath(unittest.TestCase):

    def test_the_profile_lands_under_the_login_and_carries_it(self):
        repo = host_repo()
        done = run_block("start", PROVISION, repo)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(f"github: {LOGIN}\n", profile(repo).read_text())

    def test_no_folder_is_created_for_anybody_else(self):
        repo = host_repo()
        run_block("start", PROVISION, repo)
        self.assertEqual([p.name for p in (repo / "_polaris" / "team").iterdir()], [LOGIN])

    def test_a_freshly_provisioned_profile_passes_the_gate(self):
        repo = host_repo()
        run_block("start", PROVISION, repo)
        self.assertEqual(run_block("start", GATE, repo).returncode, 0)


class TheGateStopsAProfileThatIsNotYours(unittest.TestCase):

    def test_the_template_left_unedited_stops_the_session(self):
        self.assertEqual(run_block("start", GATE, with_profile("octocat")).returncode, 1)

    def test_a_login_that_only_starts_like_yours_stops_it_too(self):
        self.assertEqual(run_block("start", GATE, with_profile(f"{LOGIN}-2")).returncode, 1)

    def test_your_own_login_goes_through(self):
        self.assertEqual(run_block("start", GATE, with_profile(LOGIN)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
