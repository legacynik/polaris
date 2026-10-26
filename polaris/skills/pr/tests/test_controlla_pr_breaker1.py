"""Fresh breaker on pr 1.1.0, 2026-10-19 (#336): what still passed or crashed.

- a `#` line inside a fenced block under «Fix» (a comment, a shell prompt) or `#1700 broke it` ended the
  section, so an issue with three points counted one; checkboxes had the same flaw;
- an empty or partial `gh pr view` reply crashed with a traceback (exit 1) instead of «cannot check»;
- a stale receipt SHA written bare, as a link, in uppercase, or under `Real test`, was not read;
- `raw.githubusercontent.com` and `/raw/` image links got neither the check nor the branch warning;
- `--no-visuale` silently beat a PR that touches the interface;
- a network error on an image read as «not found».
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import controlla_pr as cp  # noqa: E402

SHA = "c" * 40
SHOT = f"https://github.com/o/r/blob/{SHA}/shots/a.png?raw=true"
CODA = (f"## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a]({SHOT})\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
TESTA = "## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\n"
TABELLA = "## Criteri delle issue\n### #1 t\n| # | Criterio | Esito | Prova |\n|---|---|---|---|\n| 1 | a | ✅ | log |\n"
BUONO = TESTA + "Closes #1\n" + TABELLA + CODA
RECINTO = "## Fix\n1. Change X:\n   ```python\n   # new guard\n   ```\n2. Add test\n3. Gate\n"
GH = "gh"


def risposta(stato: dict, args: tuple) -> str:
    if args[:2] == ("issue", "view"):
        return json.dumps({"body": stato.get("issue", "## Acceptance criteria\n- [ ] a\n"), "comments": [],
                           "url": f"https://github.com/o/r/issues/{args[2]}"})
    if args[:2] == ("pr", "view"):
        return stato.get("pr_raw") or json.dumps({"files": [{"path": p} for p in stato.get("files", ["api/app.py"])],
                                                  "headRefOid": "a" * 40})
    if stato.get("rete_giu") or any(m in " ".join(args) for m in stato.get("mancanti", ())):
        raise subprocess.CalledProcessError(1, list(args))
    return ""


def runner(monkeypatch, stato: dict) -> None:
    """Every gh call answered from `stato`, never the real tracker."""
    vero = subprocess.run

    def finto(cmd, *a, **k):
        if not isinstance(cmd, list) or cmd[0] != GH:
            return vero(cmd, *a, **k)
        try:
            return subprocess.CompletedProcess(cmd, 0, risposta(stato, tuple(cmd[1:])), "")
        except subprocess.CalledProcessError:
            if k.get("check"):
                raise
            return subprocess.CompletedProcess(cmd, 1, "", "error")
    monkeypatch.setattr(subprocess, "run", finto)


@pytest.fixture
def esegui(tmp_path, monkeypatch):
    def lancia(corpo: str | None, *argv: str) -> int:
        f = tmp_path / "body.md"
        f.write_text(corpo or "", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["controlla_pr.py", *(["--body", str(f)] if corpo else []), *argv])
        return cp.main()
    return lancia


def test_b1_a_comment_inside_a_fence_does_not_end_the_fix_section():
    assert cp.criteri(RECINTO) == ["Change X:", "Add test", "Gate"]
    assert cp.criteri("## Fix\n1. a\n~~~sh\n# run\n## in codice\n- c\n~~~\n2. b\n") == ["a", "b"]
    assert cp.criteri("## Fix\n1. a\n#1700 broke it\n2. b\n") == ["a", "b"]


def test_b1_checkboxes_ignore_fences_and_hash_lines_too():
    issue = "## Acceptance\n- [ ] a\n```\n# x\n- [ ] in codice\n```\n#12 note\n- [ ] b\n## Altro\n- [ ] c\n"
    assert cp.caselle(issue) == ["a", "b"]


def test_b1_one_row_cannot_close_an_issue_with_three_fenced_points(esegui, monkeypatch):
    runner(monkeypatch, {"issue": RECINTO})
    dichiarato = BUONO.replace("### #1 t\n", "### #1 t\n\nIssue senza caselle: righe = «Fix» 1-3\n\n")
    assert esegui(dichiarato, "--no-visuale") == 1
    tre = dichiarato.replace("| 1 | a | ✅ | log |\n", "| 1 | a | ✅ | log |\n| 2 | b | ✅ | t |\n| 3 | c | ✅ | t |\n")
    assert esegui(tre, "--no-visuale") == 0


@pytest.mark.parametrize("pr_raw", ["{}", "null", '{"files": []}', '{"headRefOid": "aaaaaaa"}'])
def test_c1_an_empty_or_partial_pr_reply_cannot_be_judged(esegui, monkeypatch, pr_raw):
    runner(monkeypatch, {"pr_raw": pr_raw})
    assert esegui(BUONO, "--pr", "9") == 2


@pytest.mark.parametrize("pr_raw", ['{"body": null, "closingIssuesReferences": []}', "{}", "null",
                                    '{"body": "Closes #1", "closingIssuesReferences": [{}]}'])
def test_c1_a_published_pr_that_cannot_be_read_back_is_not_a_verdict(esegui, monkeypatch, pr_raw):
    runner(monkeypatch, {"pr_raw": pr_raw})
    assert esegui(None, "--verifica-pubblicato", "9") == 2


@pytest.mark.parametrize("riga", ["verde · staging bbbbbbb · breaker", "verde · [bbbbbbb](https://x/o/r/commit/bbbbbbb)",
                                  "verde · `BBBBBBB`"])
@pytest.mark.parametrize("titolo", ["Real-test", "Real test"])
def test_c3_a_stale_receipt_is_read_however_it_is_written(esegui, monkeypatch, capsys, riga, titolo):
    runner(monkeypatch, {})
    tabella = f"| Controllo | Esito |\n|---|---|\n| {titolo} | {riga} |\n\n"
    assert esegui(BUONO.replace("Closes #1\n", tabella + "Closes #1\n"), "--pr", "9", "--no-visuale") == 3
    assert "Real-test" in capsys.readouterr().out
    allineato = tabella.replace(" |\n\n", ", head AAAAAAA |\n\n")
    assert esegui(BUONO.replace("Closes #1\n", allineato + "Closes #1\n"), "--pr", "9", "--no-visuale") == 0


@pytest.mark.parametrize("link", [f"https://raw.githubusercontent.com/o/r/{SHA}/shots/a.png",
                                  f"https://github.com/o/r/raw/{SHA}/shots/a.png"])
def test_c4_raw_image_links_are_opened_like_blob_links(esegui, monkeypatch, capsys, link):
    runner(monkeypatch, {"mancanti": ["shots/a.png"]})
    assert esegui(BUONO.replace(SHOT, link), "--no-visuale") == 3
    assert "shots/a.png" in capsys.readouterr().out


@pytest.mark.parametrize("link", ["https://raw.githubusercontent.com/o/r/main/s.png", "https://github.com/o/r/raw/main/s.png"])
def test_c4_raw_image_links_on_a_branch_warn(link):
    assert any("commit" in n for n in cp.avvisi(TESTA + f"![a]({link})\n", False))


def test_c5_no_visuale_on_a_pr_that_touches_the_interface_warns_with_the_files(esegui, monkeypatch, capsys):
    runner(monkeypatch, {"files": ["web/Panel.tsx", "api/app.py"]})
    assert esegui(BUONO, "--pr", "9", "--no-visuale") == 3
    assert "web/Panel.tsx" in capsys.readouterr().out


def test_c6_a_network_error_on_an_image_cannot_be_judged(esegui, monkeypatch):
    runner(monkeypatch, {"rete_giu": True})
    assert esegui(BUONO, "--no-visuale") == 2
