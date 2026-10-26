"""#482: every issue is born with a category and a weight, and both reach the labels."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_issue as bi  # noqa: E402

MANIFEST = {"blank_issues_enabled": False, "templates": [{
    "kind": "form", "file": "bug.yml", "name": "Bug", "labels": ["bug"],
    "fields": [{"id": "acceptance-criteria", "label": "Acceptance criteria", "required": True},
               {"id": "category", "label": "Category", "required": True},
               {"id": "impact", "label": "Impact", "required": True},
               {"id": "cost", "label": "Cost", "required": True}]}]}
BASE = dict(repo_path=Path("/tmp/x"), slug="acme/api", title="t", type="bug", scope_out="",
            summary="", field=[], template=None, apply=False, ack_existing=False,
            ac=["`GET /x` returns 201"],
            adv_test=["`pytest tests/test_x.py` (new) red before the fix, green after",
                      "`curl /x` with empty body returns 400, not 500"],
            exec_summary="Sistema l'endpoint che oggi risponde con un errore sbagliato.",
            domain="auth", priority="p1", afk="yes",
            dedup="Searched: gh issue list --search + Serena find_symbol. Found: none.",
            category="bug", impact="3", cost="S")


def build(**over):
    return bi.build(Namespace(**{**BASE, **over}), MANIFEST)


def test_weighted_issue_carries_category_and_weight_labels():
    code, msg = build()
    assert code == 0, msg
    assert "cat:bug" in msg and "peso:3S" in msg


def test_each_missing_or_foreign_value_is_refused():
    for over in ({"category": ""}, {"category": "urgent"}, {"impact": ""}, {"impact": "5"},
                 {"cost": ""}, {"cost": "XL"}):
        code, msg = build(**over)
        assert code == 2, (over, msg)
