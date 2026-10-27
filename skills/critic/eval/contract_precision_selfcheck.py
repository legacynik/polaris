#!/usr/bin/env python3
"""Regression check: a critic finding must cite a real contract clause."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from critic_rules import validate


def selfcheck() -> int:
    with tempfile.TemporaryDirectory(prefix="critic contract ") as box:
        root = Path(box)
        (root / "a.md").write_text("actual artifact line\n", encoding="utf-8")
        report = {
            "artifact": str(root), "contract": "must preserve the exact artifact line",
            "ledger": {"opened": ["a.md"], "not_opened": [], "accepted_unverified": []},
            "findings": [{"claim": "line was changed", "severity": "important",
                          "evidence": {"path": "a.md", "line": 1,
                                       "quote": "actual artifact line"},
                          "falsification": {"counter": "change may be allowed",
                                            "survived": True, "why": "contract forbids it"}}],
            "halt": None,
        }
        reasons = validate(report)
        assert any("contract_quote" in reason for reason in reasons), reasons
        report["findings"][0]["contract_quote"] = "invented requirement"
        reasons = validate(report)
        assert any("does not match contract" in reason for reason in reasons), reasons
        report["findings"][0]["contract_quote"] = "preserve the exact artifact line"
        assert validate(report) == [], validate(report)
    print("SELFCHECK OK — absent and fabricated contract clauses are rejected")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selfcheck", action="store_true")
    if not parser.parse_args().selfcheck:
        parser.error("--selfcheck")
    return selfcheck()


if __name__ == "__main__":
    raise SystemExit(main())
