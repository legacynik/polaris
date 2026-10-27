"""The state of an open PR, read the way an agent must read it before handing it to its owner.

Ported from pr-status.ts of tester-army/e2e (ef977f48), plus what a hand-off to an owner needs there:
a real-test receipt on the current head, a label bound to the head it vouched for, checks the repo
declares as not gating, and the same check run twice (a red draft run, a green ready run) read as its
latest run. The 1942 fixtures are the real GitHub state of a product PR on 2026-10-18.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pr_status as ps  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
VIEWER = "acme-owner"
NOW = "2026-10-18T21:00:00Z"


def carica(nome: str):
    return json.loads((FIX / nome).read_text())


def reale(**extra) -> dict:
    pr = carica("pr-1942.json")
    nodi = carica("threads-1942.json")["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    commenti = [c | {"acknowledged": False} for pagina in carica("comments-1942.json") for c in pagina]
    recensioni = [r for pagina in carica("reviews-1942.json") for r in pagina]
    base = dict(pr=pr, threads=nodi, comments=commenti, reviews=recensioni, viewer=VIEWER,
                now=NOW, ignore={}, label=None, body_errors=[], changed_since={}, inert=[], env="staging")
    return ps.summarize(**(base | extra))


def test_a_check_run_twice_counts_as_its_latest_run():
    s = reale(ignore={"check": "staging carries migrations of other lanes"})
    assert not any(f["name"] == "ci" for f in s["checks"]["failing"])


def test_a_red_check_the_repo_does_not_declare_blocks():
    assert "failing:check" in reale()["blockers"]


def test_a_declared_non_gating_check_is_reported_with_its_reason_never_dropped():
    s = reale(ignore={"check": "staging carries migrations of other lanes"})
    assert not any(b.startswith("failing") for b in s["blockers"])
    assert s["checks"]["ignored"] == [{"name": "check", "reason": "staging carries migrations of other lanes"}]


def test_the_receipt_on_the_head_is_found_on_the_real_pr():
    assert "receipt" not in reale()["blockers"]


def test_a_head_without_a_receipt_blocks():
    pr = carica("pr-1942.json") | {"headRefOid": "f" * 40}
    assert "receipt" in reale(pr=pr)["blockers"]


def test_comments_nobody_acknowledged_block_but_the_agents_own_receipt_does_not():
    s = reale()
    assert any(b.startswith("comments:") for b in s["blockers"])
    assert not any("real-test v1" in (c["body"] or "") for c in s["comments"])


def test_a_label_set_on_an_older_head_is_stale():
    assert "label-stale" in reale(label={"sha": "a" * 40})["blockers"]
    assert "label-stale" not in reale(label={"sha": carica("pr-1942.json")["headRefOid"]})["blockers"]


def letti() -> list[dict]:
    """The real comments, every one read and acknowledged (the receipt stays among them)."""
    return [c | {"acknowledged": True} for pagina in carica("comments-1942.json") for c in pagina]


def test_unknown_mergeability_waits_and_a_closed_pr_is_closed():
    s = reale(ignore={"check": "x"}, comments=letti())
    assert s["verdict"] == "WAITING" and "mergeability" in s["checks"]["pending"]
    assert reale(pr=carica("pr-1942.json") | {"state": "MERGED"})["verdict"] == "CLOSED"


def test_a_thread_whose_last_word_is_the_agents_attributed_reply_is_escalated_not_blocking():
    def filo(autore: str, testo: str) -> dict:
        return {"id": "T", "isResolved": False, "isOutdated": False, "path": "a.py", "line": 1,
                "root": {"nodes": [{"databaseId": 1, "author": {"login": "bot"}, "body": "x", "url": "u"}]},
                "latest": {"nodes": [{"author": {"login": autore}, "body": testo}]}}
    risposta = "_[claude-opus-5-5] responding on behalf of acme-owner_\n\nowner's call <!-- escalated -->"
    assert reale(threads=[filo(VIEWER, risposta)])["escalated"]
    risposto = reale(threads=[filo(VIEWER, risposta.replace(" <!-- escalated -->", ""))])
    assert "threads:1" in risposto["blockers"], "an ordinary reply is not an escalation (critic B1)"
    forgiato = reale(threads=[filo("bot", risposta)])
    assert forgiato["threads"] and "threads:1" in forgiato["blockers"]


def test_empty_checks_wait_instead_of_passing():
    pr = carica("pr-1942.json") | {"statusCheckRollup": []}
    assert "checks not reported yet" in reale(pr=pr, comments=letti())["checks"]["pending"]



# Fresh critic, 2026-10-18.
def test_b2_github_saying_behind_or_blocked_is_not_ready():
    for stato, atteso in (("BEHIND", "behind-base"), ("BLOCKED", "blocked"), ("DIRTY", "conflict")):
        pr = carica("pr-1942.json") | {"mergeStateStatus": stato}
        assert atteso in reale(pr=pr)["blockers"], stato


def test_b3_a_body_the_checker_refuses_blocks_the_label():
    assert "body" in reale(body_errors=["manca la decisione"])["blockers"]


def test_b4_a_receipt_from_another_environment_does_not_sign():
    assert "receipt" in reale(env="production-like")["blockers"]


def test_o1_a_receipt_survives_pushes_that_touch_only_inert_files():
    head = carica("pr-1942.json")["headRefOid"]
    pr = carica("pr-1942.json") | {"headRefOid": "e" * 40}
    inerte = {head: [".real-test/evidence/x.jpg", "docs/a.md"]}
    assert "receipt" not in reale(pr=pr, changed_since=inerte, inert=[".real-test/**", "docs/**"])["blockers"]
    codice = {head: ["src/app.py"]}
    assert "receipt" in reale(pr=pr, changed_since=codice, inert=[".real-test/**", "docs/**"])["blockers"]


# Second fresh critic, 2026-10-18.
def test_r2_a_local_receipt_mentioning_staging_does_not_sign():
    head = carica("pr-1942.json")["headRefOid"]
    for amb in ("locale (backend del branch), NON staging", "locale contro DB di staging"):
        c = {"user": {"login": VIEWER}, "body": f"<!-- real-test v1 sha={head} verdict=MERGEABLE -->\nambiente: {amb}"}
        assert "receipt" in reale(comments=[c])["blockers"], amb


def test_r2_a_review_comment_saying_do_not_merge_blocks_until_answered():
    r = {"id": 9, "state": "COMMENTED", "submitted_at": "2026-10-18T20:00:00Z", "user": {"login": "bob"},
         "body": "Non mergiare: il PDF stampa l'indirizzo sbagliato", "html_url": "u"}
    assert any(b.startswith("comments:") for b in reale(reviews=[r], comments=letti())["blockers"])
    risposta = {"user": {"login": VIEWER}, "created_at": "2026-10-18T21:00:00Z", "acknowledged": True,
                "body": "_[claude-opus-5-5] responding on behalf of acme-owner_\n\nfixed in abc"}
    assert not any(b.startswith("comments:") for b in reale(reviews=[r], comments=letti() + [risposta])["blockers"])
