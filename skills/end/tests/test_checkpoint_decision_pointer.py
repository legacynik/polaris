"""checkpoint.sh verify — a `- Decision:` pointer may name a DEC record that `/architecture decide`
wrote (`decisions/<DEC-id>.md`, committed and clean), not only a heading of `decisions.md`.

    python3 -m pytest skills-suite/end/tests/test_checkpoint_decision_pointer.py
"""
from __future__ import annotations

from test_checkpoint_lesson_pointer import _checkout, _commit, _verify

DEC_ID = "DEC-demo-pricing-service-001"


def _dec(root):
    path = root / "decisions" / f"{DEC_ID}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nid: DEC-demo-pricing-service-001\n---\nbody\n")
    ledger = root / "decisions.md"  # decide writes the ledger row beside the record
    ledger.write_text(f"## 2026-10-26 — pricing as a service ({DEC_ID})\n")
    return path, ledger


def test_a_committed_dec_record_passes(tmp_path):
    root = _checkout(tmp_path, f"- Decision: {DEC_ID}\n")
    _commit(tmp_path, *_dec(root))
    code, out = _verify(tmp_path)
    assert code == 0 and "checkpoint: verified" in out, out


def test_an_uncommitted_dec_record_fails_naming_it(tmp_path):
    root = _checkout(tmp_path, f"- Decision: {DEC_ID}\n")
    record, ledger = _dec(root)
    _commit(tmp_path, ledger)
    code, out = _verify(tmp_path)
    assert code == 1 and DEC_ID in out, out
