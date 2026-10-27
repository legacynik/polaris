"""`issue:<repo>#N` is the qualified form `/end` asks for, and `<repo>` is THIS repository.

Reading every qualified citation as foreign would stop the prune from ever closing a lane written
the way the skill prescribes. The qualifier is this repository's own name when it matches the
checkout directory or the `origin` remote; a checkout renamed on disk still has its remote.
"""
from __future__ import annotations

import unittest

from host_repo import git, host_repo, written
from prune_fixture import cockpit, prune

COMPLETED = {"issue": {"77": {"state": "CLOSED", "stateReason": "COMPLETED"}}}


def lane_citing(repo, qualified: str) -> str:
    written(cockpit(repo), f"- `feat/y` (acme-api) — chiude issue:{qualified}#77 · since 2026-09-02")
    out = prune(repo, COMPLETED, "--apply")
    assert out.returncode == 0, out.stdout + out.stderr
    return (repo / "_polaris" / "state" / "current.md").read_text()


class OwnNameCitationIsLocal(unittest.TestCase):
    def test_the_checkout_directory_name_is_this_repository(self):
        self.assertNotIn("feat/y", lane_citing(host_repo(), "acme-api"))

    def test_the_origin_remote_name_is_this_repository(self):
        repo = host_repo(name="renamed checkout")
        git(repo, "remote", "add", "origin", "git@example.com:acme/acme-api.git")
        self.assertNotIn("feat/y", lane_citing(repo, "acme/acme-api"))

    def test_another_name_is_still_foreign(self):
        self.assertIn("feat/y", lane_citing(host_repo(), "acme-web"))


if __name__ == "__main__":
    unittest.main()
