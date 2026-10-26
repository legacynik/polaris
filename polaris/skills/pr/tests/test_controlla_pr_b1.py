"""Fresh breaker, 2026-10-19: criteria coverage counted rows, not the issue's numbered criteria.

- Rows `a ✅ c ✅ zzz ✅` passed an issue with three criteria; `a`, `a.`, `a!` passed as three.
  Contract: the `#` column covers exactly 1..k once each (k = the issue's criteria, or the rows when
  the issue lists none), every row ✅.
- A row whose verdict is not one of the four marks (🔴, FAIL) was dropped, not failed.
- `tbd`, `...` and `…` passed as proof.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import controlla_pr as cp  # noqa: E402

CODA = ("## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a](https://x/b/c.png?raw=true)\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
TESTA = "## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\nCloses #1\n## Criteri delle issue\n### #1 t\n"


def corpo(*righe: str) -> str:
    return TESTA + "| # | Criterio | Esito | Prova |\n|---|---|---|---|\n" + "".join(r + "\n" for r in righe) + CODA


@pytest.mark.parametrize("righe", [
    ("| 1 | a | ✅ | log |", "| 3 | c | ✅ | log |", "| 4 | zzz | ✅ | log |"),
    ("| 1 | a | ✅ | log |", "| 1 | a. | ✅ | log |", "| 1 | a! | ✅ | log |"),
    ("| 1 | a | ✅ | log |", "| 2 | b | ✅ | log |"),
    ("| 1 | a | ✅ | log |", "| 2 | b | ✅ | log |", "| 2 | c | ✅ | log |"),
])
def test_b5_the_number_column_covers_each_criterion_exactly_once(righe):
    errori = cp.controlla(corpo(*righe), {1: ["a", "b", "c"]}, True)
    assert any("l'issue ne ha 3" in e for e in errori), (righe, errori)


@pytest.mark.parametrize("esito", ["🔴", "FAIL", "ok", ""])
def test_b5_a_row_with_an_unknown_mark_fails_and_is_not_dropped(esito):
    errori = cp.controlla(corpo("| 1 | a | ✅ | log |", f"| 2 | b | {esito} | log |"), {1: ["a", "b"]}, True)
    assert any("Refs" in e for e in errori), (esito, errori)


def test_b5_an_issue_without_checkboxes_still_needs_rows_numbered_from_one():
    assert cp.controlla(corpo("| 1 | a | ✅ | log |", "| 2 | b | ✅ | log |"), {1: []}, True) == []
    errori = cp.controlla(corpo("| 1 | a | ✅ | log |", "| 3 | b | ✅ | log |"), {1: []}, True)
    assert errori, errori


def test_b5_a_complete_numbered_table_passes():
    righe = ("| 1 | a | ✅ | log |", "| 2 | b | ✅ | test t |", "| 3 | c | ✅ | ricevuta |")
    assert cp.controlla(corpo(*righe), {1: ["a", "b", "c"]}, True) == []


@pytest.mark.parametrize("prova", ["tbd", "TBD", "...", "…", "todo"])
def test_b4_a_placeholder_is_no_proof(prova):
    errori = cp.controlla(corpo(f"| 1 | a | ✅ | {prova} |"), {1: ["a"]}, True)
    assert any("prova" in e for e in errori), (prova, errori)
