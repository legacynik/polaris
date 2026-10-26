"""First live use of pr, 2026-10-19 (#336): what the checker misread in a real body, offline.

- an issue with no checkbox had its table rows counted instead of its own points;
- a `\\|` inside a cell (a pytest id like `test_x[pdf\\|xlsx]`) split the row, and nobody said so;
- an image linked to a branch drifts with the branch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import controlla_pr as cp  # noqa: E402

CODA = ("## Cosa cambia\nx\n## Decisioni\nx\n## Prove\ntest verdi\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
TESTA = "## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\n"


def corpo(riga: str, parola: str = "Closes") -> str:
    tabella = "| # | Criterio | Esito | Prova |\n|---|---|---|---|\n" + riga + "\n"
    return TESTA + f"{parola} #1\n## Criteri delle issue\n### #1 t\n" + tabella + CODA


def test_d2_with_no_checkbox_the_points_under_criteria_or_fix_are_the_criteria():
    assert cp.criteri("## Fix\n1. a\n2) b\n3. c\n## Gate\n1. non conta\n") == ["a", "b", "c"]
    assert cp.criteri("## Acceptance criteria\n- x\n  - dentro x\n* y\n") == ["x", "y"]
    assert cp.criteri("## Note\n1. fuori da ogni sezione di criteri\n") == []


def test_d2_a_checkbox_anywhere_still_wins_over_points():
    assert cp.criteri("## Fix\n1. a\n2. b\n## Acceptance\n- [ ] k\n") == ["k"]


def test_d3_an_escaped_pipe_stays_inside_its_cell():
    riga = "| 1 | a | ✅ | `test_x[pdf\\|xlsx\\|csv]` |"
    assert cp.controlla(corpo(riga), {1: ["a"]}, False) == []
    assert cp.righe_issue(corpo(riga), 1)[0][-1] == "`test_x[pdf|xlsx|csv]`"


def test_d3_a_row_with_more_or_fewer_cells_than_the_header_is_an_error():
    for riga in ("| 1 | a | ✅ | log | extra |", "| 1 | a | ✅ |"):
        assert any("celle" in e for e in cp.controlla(corpo(riga), {1: ["a"]}, False)), riga


def test_d3_a_ragged_row_is_an_error_under_refs_too():
    assert any("celle" in e for e in cp.controlla(corpo("| 1 | a | ❌ | x | y |", "Refs"), {1: ["a"]}, False))


def test_d3_a_table_without_header_is_not_judged_on_width():
    senza = TESTA + "Closes #1\n## Criteri delle issue\n### #1 t\n| 1 | a | ✅ | log |\n" + CODA
    assert cp.controlla(senza, {1: ["a"]}, False) == []


def test_d7_an_image_linked_to_a_branch_warns_and_one_linked_to_a_commit_does_not():
    ramo = TESTA + "![a](https://github.com/o/r/blob/main/s.png?raw=true)\n"
    assert any("commit" in n for n in cp.avvisi(ramo, False))
    fisso = ramo.replace("/blob/main/", "/blob/" + "c" * 40 + "/")
    assert not any("commit" in n for n in cp.avvisi(fisso, False))
