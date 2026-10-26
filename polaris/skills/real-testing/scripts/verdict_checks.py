#!/usr/bin/env python3
"""verdict_checks.py — the pure validation rules for a real-test verdict.

No dependency on git: takes already-loaded dicts + a `repo: Path` only to
check `evidence_artifact` files on the filesystem. `verdict.py` orchestrates
these functions against the real perimeter computed by `perimeter.py`.

  G2.6/F6/F7 -> validate_hash            (the verdict must match the hash NOW)
  G1.6       -> validate_branches_covered (every new branch must be cited)
  G2.1       -> validate_evidence         (mock/empty is not proof; live must be fresh)

Usage: verdict_checks.py --selfcheck
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

VERDETTI = {"MERGEABLE", "MERGEABLE-CON-GAP", "NOT-MERGEABLE"}
CLASSES = {
    "symbol": "application symbol (callers/fallbacks/types)",
    "api-cli": "API/CLI/tool/event/schema",
    "config-ci": "config/permission/hook/CI",
    "dependency": "dependency/lock/build",
    "db-migration": "DB/migration/storage",
    "frontend": "frontend (browser)",
    "llm-agent": "LLM/agent/prompt/toolset",
    "deletion": "deletion/rename",
    "docs": "docs/guidance/history",
    "test-only": "test-only",
}
LIVE_REQUIRED = {"db-migration", "llm-agent", "frontend", "api-cli", "dependency"}
RACCOLTO_NEEDS_ARTIFACT = {"difetto", "combinazione", "invariante"}
RACCOLTO_NEEDS_NOTA = {"falso-allarme", "tetto"}


def load_verdict(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"verdict unreadable ({path}): {e}") from e


def validate_verdetto_value(v: dict) -> list[str]:
    val = v.get("verdetto")
    return [] if val in VERDETTI else [f"verdict '{val}' is not one of the three states: {VERDETTI}"]


def validate_hash(v: dict, expected: str) -> list[str]:
    got = v.get("content_hash")
    if got != expected:
        return [f"content_hash stale: verdict has '{got}', real perimeter is now '{expected}'"]
    return []


def validate_files_covered(v: dict, files: list[str]) -> list[str]:
    matrix_files = {row.get("file") for row in v.get("matrix", [])}
    missing = [f for f in files if f not in matrix_files]
    return [f"files outside the matrix: {missing}"] if missing else []


def validate_branches_covered(v: dict, new_branches: list[dict]) -> list[str]:
    exercised: set[str] = set()
    for row in v.get("matrix", []):
        exercised.update(row.get("branches_exercised", []))
    missing = [
        f"{b['file']}:{b['line']} ({b['snippet']})"
        for b in new_branches
        if f"{b['file']}:{b['line']}" not in exercised
    ]
    return [f"new branches not exercised in the verdict: {missing}"] if missing else []


def _schema_errors(row: dict, art: str, p: Path) -> list[str]:
    """EVAL-real-test-copertura.md row 3 (G2.1): existence+freshness is not proof —
    a prose file declaring 'no real call, MagicMock in test' used to pass.
    Requires JSON with a non-empty 'call_id': an identifier traceable to ONE
    call (request id, hash, trace id) — it does not intercept IO (attestation, not
    interception, stated in matrix-classes.md), but loose text/a note is no
    longer a valid schema."""
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return [f"{row.get('file')}: evidence_artifact '{art}' is not JSON — not a verifiable schema"]
    if not isinstance(data, dict) or not str(data.get("call_id") or "").strip():
        return [f"{row.get('file')}: evidence_artifact '{art}' without 'call_id' — an attestation without a schema is not proof"]
    return []


def _artifact_errors(row: dict, repo: Path) -> list[str]:
    art = row.get("evidence_artifact")
    if not art:
        return [f"{row.get('file')}: evidence=live without evidence_artifact"]
    p = repo / art if not Path(art).is_absolute() else Path(art)
    if not p.exists() or p.stat().st_size == 0:
        return [f"{row.get('file')}: evidence_artifact '{art}' missing or empty"]
    src = repo / row["file"]
    if src.exists() and p.stat().st_mtime < src.stat().st_mtime:
        return [f"{row.get('file')}: evidence_artifact '{art}' older than the file — stale proof"]
    return _schema_errors(row, art, p)


def validate_evidence(v: dict, repo: Path) -> list[str]:
    errs: list[str] = []
    for row in v.get("matrix", []):
        cls, ev = row.get("class"), row.get("evidence")
        if ev not in {"live", "assumed", "not-applicable"}:
            errs.append(f"{row.get('file')}: evidence '{ev}' is invalid")
        elif cls in LIVE_REQUIRED and ev == "not-applicable":
            errs.append(f"{row.get('file')}: class '{cls}' cannot be not-applicable")
        elif ev == "live":
            errs += _artifact_errors(row, repo)
        elif ev == "assumed" and not row.get("exception_ticket"):
            errs.append(f"{row.get('file')}: evidence=assumed without exception_ticket")
    return errs


def validate_raccolto(v: dict) -> list[str]:
    if v.get("verdetto") == "NOT-MERGEABLE":
        return []
    raccolto = v.get("raccolto") or []
    if not raccolto:
        return ["raccolto empty: no classified finding, no test left in CI"]
    errs = []
    for e in raccolto:
        if e.get("tipo") in RACCOLTO_NEEDS_ARTIFACT and not e.get("artifact"):
            errs.append(f"raccolto '{e.get('tipo')}' without artifact (test left in CI)")
        if e.get("tipo") in RACCOLTO_NEEDS_NOTA and not e.get("nota"):
            errs.append(f"raccolto '{e.get('tipo')}' without nota")
    return errs


def _selfcheck() -> int:
    """Unit-level, no git: exercises each pure function on hand-built dicts."""
    assert validate_verdetto_value({"verdetto": "MERGEABLE"}) == []
    assert validate_verdetto_value({"verdetto": "BOH"}) != []

    assert validate_hash({"content_hash": "a"}, "a") == []
    assert validate_hash({"content_hash": "a"}, "b") != []

    assert validate_files_covered({"matrix": [{"file": "x.py"}]}, ["x.py"]) == []
    assert validate_files_covered({"matrix": []}, ["x.py"]) != []

    nb = [{"file": "x.py", "line": 1, "snippet": "if y:"}]
    assert validate_branches_covered({"matrix": [{"branches_exercised": ["x.py:1"]}]}, nb) == []
    assert validate_branches_covered({"matrix": []}, nb) != []

    assert validate_raccolto({"verdetto": "NOT-MERGEABLE"}) == []
    assert validate_raccolto({"verdetto": "MERGEABLE", "raccolto": []}) != []
    ok_raccolto = {"verdetto": "MERGEABLE", "raccolto": [{"tipo": "falso-allarme", "nota": "x"}]}
    assert validate_raccolto(ok_raccolto) == []

    row_live_required = {"file": "m.sql", "class": "db-migration", "evidence": "not-applicable"}
    assert validate_evidence({"matrix": [row_live_required]}, Path(".")) != []
    row_assumed_ok = {"file": "m.sql", "class": "db-migration", "evidence": "assumed",
                       "exception_ticket": "T-1"}
    assert validate_evidence({"matrix": [row_assumed_ok]}, Path(".")) == []

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        art = repo / "trace.json"
        row_live = {"file": "a.py", "class": "llm-agent", "evidence": "live",
                    "evidence_artifact": "trace.json"}
        art.write_text('{"note": "handmade, no real call - MagicMock in test"}')
        assert validate_evidence({"matrix": [row_live]}, repo) != [], \
            "prose without call_id (the EVAL-copertura row 3 reproducer) must fail"
        art.write_text("plain text, not json")
        assert validate_evidence({"matrix": [row_live]}, repo) != [], "non-JSON must fail"
        art.write_text('{"call_id": "req-abc123", "note": "real call"}')
        assert validate_evidence({"matrix": [row_live]}, repo) == [], "JSON with call_id must pass"
    print("SELFCHECK OK — 15 assertions on the pure functions (call_id schema included)")
    return 0


if __name__ == "__main__":
    sys.exit(_selfcheck() if "--selfcheck" in sys.argv else 1)
