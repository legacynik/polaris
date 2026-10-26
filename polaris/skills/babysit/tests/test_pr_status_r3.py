"""Third fresh critic, 2026-10-18.

- A repo whose CI runs on the machine (`signing_env: local`) has no GitHub check at all: its PRs sat
  in WAITING forever. Zero checks still wait where the repo signs on staging (CI may not have started).
- `ambiente: non-staging` and `ambiente: local-staging-db` signed as staging (the hyphen read as a word
  boundary); the real receipt's first word is a host, `api-staging.<host>`, and that must sign.
- `Closes other/repo#7` in a published body read issue 7 from the PR's own repository.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
sys.path.insert(0, str(HERE.parents[2] / "pr" / "scripts"))
import controlla_pr  # noqa: E402
import pr_fetch  # noqa: E402
import pr_status as ps  # noqa: E402

HEAD = "a" * 40
PR = {"state": "OPEN", "headRefOid": HEAD, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
      "statusCheckRollup": []}


def run(ambiente: str, env: str) -> dict:
    me = {"user": {"login": "me"}, "body": f"<!-- real-test v1 sha={HEAD} verdict=MERGEABLE -->\nambiente: {ambiente}"}
    return ps.summarize(pr=PR, threads=[], comments=[me], reviews=[], viewer="me", now="2026-02-01T00:00:00Z",
                        ignore={}, label=None, body_errors=[], changed_since={}, inert=[], env=env)


def test_r3_zero_checks_on_a_locally_signed_repo_is_ready_and_says_why():
    s = run("local vault run", "local")
    assert s["verdict"] == "READY", s
    assert any("local" in i["reason"] for i in s["checks"]["ignored"]), s["checks"]


def test_r3_zero_checks_still_wait_where_the_repo_signs_on_staging():
    assert run("api-staging.example.com serving the branch", "staging")["verdict"] == "WAITING"


def test_r3_hyphen_qualified_words_do_not_sign_staging():
    for amb in ("non-staging", "local-staging-db", "staging-like locale"):
        assert "receipt" in run(amb, "staging")["blockers"], amb


def test_r3_a_staging_host_or_the_bare_word_signs():
    for amb in ("api-staging.example.com serving the branch", "staging", "Staging, branch x", "staging.example.com"):
        assert "receipt" not in run(amb, "staging")["blockers"], amb


def test_r3_a_cross_repo_issue_is_read_from_its_repo(monkeypatch):
    reads = []
    monkeypatch.setattr(controlla_pr, "leggi_issue", lambda n, r: reads.append((n, r)) or [])
    for body, atteso in (("Closes other/repo#7", "other/repo"), ("Closes #7", "o/r")):
        reads.clear()
        pr_fetch.body_errors(body + "\n", "o/r", [])
        assert reads == [(7, atteso)], body
