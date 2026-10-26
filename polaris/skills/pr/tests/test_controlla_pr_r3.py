"""Third fresh critic, 2026-10-18: bodies that passed `Closes` without proving every criterion.

- a verdict cell `❌ (✅ dopo deploy)` read as ✅ because it contained one;
- three identical rows counted as three criteria covered;
- a proof cell of `—` or `n/d` counted as proof;
- `Closes other/repo#7` read issue 7 from the PR's own repository.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import controlla_pr as cp  # noqa: E402

CODA = ("## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a](https://x/b/c.png?raw=true)\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
TESTA = "## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\nCloses #1\n## Criteri delle issue\n### #1 t\n"


def corpo(*righe: str) -> str:
    return TESTA + "| # | Criterio | Esito | Prova |\n|---|---|---|---|\n" + "".join(r + "\n" for r in righe) + CODA


def test_r3_a_verdict_cell_holding_a_cross_and_a_tick_is_not_a_tick():
    errori = cp.controlla(corpo("| 1 | a | ❌ (✅ dopo deploy) | log |"), {1: ["a"]}, True)
    assert any("Refs" in e for e in errori), errori


def test_r3_identical_rows_count_as_one_criterion():
    errori = cp.controlla(corpo(*["| 1 | a | ✅ | log |"] * 3), {1: ["a", "b", "c"]}, True)
    assert any("l'issue ne ha 3" in e for e in errori), errori


def test_r3_a_dash_or_not_available_is_no_proof():
    for prova in ("—", "-", "n/d", "N/D", " "):
        errori = cp.controlla(corpo(f"| 1 | a | ✅ | {prova} |"), {1: ["a"]}, True)
        assert any("prova" in e for e in errori), prova


def test_r3_a_well_formed_body_still_passes():
    assert cp.controlla(corpo("| 1 | a | ✅ | log |", "| 2 | b | ✅ | test t |"), {1: ["a", "b"]}, True) == []


def test_r3_the_repo_of_a_cross_repo_issue_is_read_from_the_body():
    for riga, atteso in (("Closes other/repo#7", "other/repo"), ("Refs o-1/r.x#7", "o-1/r.x"),
                         ("Fixes https://github.com/o/r/issues/7", "o/r"), ("Closes #7", None)):
        assert cp.repo_di(riga + "\n", 7) == atteso, riga
