#!/usr/bin/env python3
"""verdict_checks.py — le regole pure di validazione di un verdetto real-test.

Nessuna dipendenza da git: prende dict gia' caricati + un `repo: Path` solo per
controllare gli `evidence_artifact` sul filesystem. `verdict.py` orchestra
queste funzioni contro il perimetro reale calcolato da `perimeter.py`.

  G2.6/F6/F7 -> validate_hash            (il verdetto deve combaciare con l'hash ORA)
  G1.6       -> validate_branches_covered (ogni ramo nuovo va citato)
  G2.1       -> validate_evidence         (mock/vuoto non e' prova; live va fresco)

Uso: verdict_checks.py --selfcheck
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

VERDETTI = {"MERGEABLE", "MERGEABLE-CON-GAP", "NOT-MERGEABLE"}
CLASSES = {
    "symbol": "simbolo applicativo (chiamanti/fallback/tipi)",
    "api-cli": "API/CLI/tool/event/schema",
    "config-ci": "config/permission/hook/CI",
    "dependency": "dipendenza/lock/build",
    "db-migration": "DB/migrazione/storage",
    "frontend": "frontend (browser)",
    "llm-agent": "LLM/agent/prompt/toolset",
    "deletion": "delezione/rename",
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
        raise ValueError(f"verdetto illeggibile ({path}): {e}") from e


def validate_verdetto_value(v: dict) -> list[str]:
    val = v.get("verdetto")
    return [] if val in VERDETTI else [f"verdetto '{val}' non e' uno dei tre stati: {VERDETTI}"]


def validate_hash(v: dict, expected: str) -> list[str]:
    got = v.get("content_hash")
    if got != expected:
        return [f"content_hash stale: verdetto ha '{got}', perimetro reale ora e' '{expected}'"]
    return []


def validate_files_covered(v: dict, files: list[str]) -> list[str]:
    matrix_files = {row.get("file") for row in v.get("matrix", [])}
    missing = [f for f in files if f not in matrix_files]
    return [f"file fuori dalla matrice: {missing}"] if missing else []


def validate_branches_covered(v: dict, new_branches: list[dict]) -> list[str]:
    exercised: set[str] = set()
    for row in v.get("matrix", []):
        exercised.update(row.get("branches_exercised", []))
    missing = [
        f"{b['file']}:{b['line']} ({b['snippet']})"
        for b in new_branches
        if f"{b['file']}:{b['line']}" not in exercised
    ]
    return [f"rami nuovi non esercitati nel verdetto: {missing}"] if missing else []


def _schema_errors(row: dict, art: str, p: Path) -> list[str]:
    """EVAL-real-test-copertura.md riga 3 (G2.1): esistenza+freschezza non e' prova —
    un file di prosa che dichiara 'nessuna chiamata reale, MagicMock in test' passava.
    Richiede JSON con 'call_id' non vuoto: un identificatore riconducibile a UNA
    chiamata (request id, hash, trace id) — non intercetta IO (attestazione, non
    interception, dichiarato in matrix-classes.md), ma un testo/nota sciolta non e'
    piu' uno schema valido."""
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return [f"{row.get('file')}: evidence_artifact '{art}' non e' JSON — non e' uno schema verificabile"]
    if not isinstance(data, dict) or not str(data.get("call_id") or "").strip():
        return [f"{row.get('file')}: evidence_artifact '{art}' senza 'call_id' — attestazione senza schema non e' prova"]
    return []


def _artifact_errors(row: dict, repo: Path) -> list[str]:
    art = row.get("evidence_artifact")
    if not art:
        return [f"{row.get('file')}: evidence=live senza evidence_artifact"]
    p = repo / art if not Path(art).is_absolute() else Path(art)
    if not p.exists() or p.stat().st_size == 0:
        return [f"{row.get('file')}: evidence_artifact '{art}' assente o vuoto"]
    src = repo / row["file"]
    if src.exists() and p.stat().st_mtime < src.stat().st_mtime:
        return [f"{row.get('file')}: evidence_artifact '{art}' piu' vecchio del file — prova stale"]
    return _schema_errors(row, art, p)


def validate_evidence(v: dict, repo: Path) -> list[str]:
    errs: list[str] = []
    for row in v.get("matrix", []):
        cls, ev = row.get("class"), row.get("evidence")
        if ev not in {"live", "assumed", "not-applicable"}:
            errs.append(f"{row.get('file')}: evidence '{ev}' non valida")
        elif cls in LIVE_REQUIRED and ev == "not-applicable":
            errs.append(f"{row.get('file')}: classe '{cls}' non puo' essere not-applicable")
        elif ev == "live":
            errs += _artifact_errors(row, repo)
        elif ev == "assumed" and not row.get("exception_ticket"):
            errs.append(f"{row.get('file')}: evidence=assumed senza exception_ticket")
    return errs


def validate_raccolto(v: dict) -> list[str]:
    if v.get("verdetto") == "NOT-MERGEABLE":
        return []
    raccolto = v.get("raccolto") or []
    if not raccolto:
        return ["raccolto vuoto: nessuna scoperta classificata, nessun test lasciato in CI"]
    errs = []
    for e in raccolto:
        if e.get("tipo") in RACCOLTO_NEEDS_ARTIFACT and not e.get("artifact"):
            errs.append(f"raccolto '{e.get('tipo')}' senza artifact (test lasciato in CI)")
        if e.get("tipo") in RACCOLTO_NEEDS_NOTA and not e.get("nota"):
            errs.append(f"raccolto '{e.get('tipo')}' senza nota")
    return errs


def _selfcheck() -> int:
    """Unit-level, senza git: prova ogni funzione pura su dict costruiti a mano."""
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
        art.write_text('{"note": "fabbricato a mano, nessuna chiamata reale - MagicMock in test"}')
        assert validate_evidence({"matrix": [row_live]}, repo) != [], \
            "prosa senza call_id (il reproducer di EVAL-copertura riga 3) deve fallire"
        art.write_text("solo testo, non json")
        assert validate_evidence({"matrix": [row_live]}, repo) != [], "non-JSON deve fallire"
        art.write_text('{"call_id": "req-abc123", "note": "chiamata reale"}')
        assert validate_evidence({"matrix": [row_live]}, repo) == [], "JSON con call_id deve passare"
    print("SELFCHECK OK — 15 asserzioni sulle funzioni pure (call_id schema incluso)")
    return 0


if __name__ == "__main__":
    sys.exit(_selfcheck() if "--selfcheck" in sys.argv else 1)
