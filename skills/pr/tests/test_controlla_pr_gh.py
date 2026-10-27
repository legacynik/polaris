"""First live use of pr, 2026-10-19 (#336): the CLI judged a real PR from the wrong tree and head.

- the screenshot rule came from the branch checked out in the working directory, not the PR's files;
- a superseded pull request written after Refs was read as if it were an issue;
- a receipt signed on an older SHA, an image link that does not open, a head that moved between draft
  and publish, and GitHub's closing links after publishing: none of them was read.
Every gh call is answered by a runner that replaces `subprocess.run` and reads a dict.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import controlla_pr as cp  # noqa: E402

HEAD = "a" * 40
SHOT = "https://github.com/o/r/blob/" + "c" * 40 + "/shots/a.png?raw=true"
CODA = (f"## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a]({SHOT})\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
TESTA = "## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\n"
TABELLA = "## Criteri delle issue\n### #1 t\n| # | Criterio | Esito | Prova |\n|---|---|---|---|\n| 1 | a | ✅ | log |\n"
BUONO = TESTA + "Closes #1\n" + TABELLA + CODA
CASELLE = "## Acceptance criteria\n- [ ] a\n"


GH = "gh"


def risposta(stato: dict, args: tuple) -> str:
    """What GitHub would print for `args`, from `stato`; a missing contents path raises like a 404."""
    if args[:2] == ("issue", "view"):
        tipo = "pull" if int(args[2]) in stato.get("pr", ()) else "issues"
        return json.dumps({"body": stato.get("issues", {}).get(int(args[2]), CASELLE), "comments": [],
                           "url": f"https://github.com/o/r/{tipo}/{args[2]}"})
    if args[:2] == ("pr", "view"):
        return json.dumps({"files": [{"path": p} for p in stato.get("files", ["api/app.py"])],
                           "headRefOid": HEAD, "body": stato.get("body", BUONO),
                           "closingIssuesReferences": [{"number": n} for n in stato.get("chiuse", [1])]})
    if any(m in " ".join(args) for m in stato.get("mancanti", ())):
        raise subprocess.CalledProcessError(1, list(args))
    return ""


def runner(monkeypatch, stato: dict) -> list:
    """Every gh call answered from `stato`, never the real tracker; the calls are kept to be read."""
    visti, vero = [], subprocess.run

    def finto(cmd, *a, **k):
        if not isinstance(cmd, list) or cmd[0] != GH:
            return vero(cmd, *a, **k)
        visti.append(tuple(cmd[1:]))
        try:
            return subprocess.CompletedProcess(cmd, 0, risposta(stato, tuple(cmd[1:])), "")
        except subprocess.CalledProcessError:
            if k.get("check"):
                raise
            return subprocess.CompletedProcess(cmd, 1, "", "HTTP 404")
    monkeypatch.setattr(subprocess, "run", finto)
    return visti


@pytest.fixture
def esegui(tmp_path, monkeypatch):
    """Runs the CLI as the skill does, on `corpo` written to a file (None: no --body)."""
    def lancia(corpo: str | None, *argv: str) -> int:
        f = tmp_path / "body.md"
        f.write_text(corpo or "", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["controlla_pr.py", *(["--body", str(f)] if corpo else []), *argv])
        return cp.main()
    return lancia


def test_d1_without_the_pr_or_an_explicit_flag_it_refuses_instead_of_reading_the_cwd(esegui, monkeypatch, capsys):
    runner(monkeypatch, {})
    monkeypatch.chdir(Path(__file__).parent)  # some checked-out branch, never the PR's
    assert esegui(BUONO) == 2
    assert "--pr" in capsys.readouterr().err


def test_d1_the_prs_own_files_decide_the_screenshot(esegui, monkeypatch, capsys):
    senza_foto = BUONO.replace(f"![a]({SHOT})", "test verdi")
    visti = runner(monkeypatch, {"files": ["web/Panel.tsx"]})
    assert esegui(senza_foto, "--pr", "9", "-R", "o/r") == 1
    assert "foto" in capsys.readouterr().out
    assert any(v[:3] == ("pr", "view", "9") and "o/r" in v for v in visti)
    runner(monkeypatch, {"files": ["api/app.py"]})
    assert esegui(senza_foto, "--pr", "9", "-R", "o/r") == 0


def test_d2_an_issue_without_checkboxes_is_judged_on_its_fix_points(esegui, monkeypatch, capsys):
    runner(monkeypatch, {"issues": {1: "## Fix\n1. a\n2. b\n## Gate\nprosa\n"}})
    tre = BUONO.replace("| 1 | a | ✅ | log |\n", "| 1 | a | ✅ | log |\n| 2 | b | ✅ | log |\n| 3 | c | ✅ | log |\n")
    assert esegui(tre, "--no-visuale") == 1
    capsys.readouterr()
    due = tre.replace("| 3 | c | ✅ | log |\n", "")
    assert esegui(due, "--no-visuale") == 3
    assert "senza caselle" in capsys.readouterr().out
    dichiarato = due.replace("### #1 t\n", "### #1 t\n\nIssue senza caselle: righe = «Fix» 1-2\n\n")
    assert esegui(dichiarato, "--no-visuale") == 0


def test_d2_an_issue_with_nothing_to_count_warns_and_names_it(esegui, monkeypatch, capsys):
    runner(monkeypatch, {"issues": {1: "Solo prosa, nessun elenco.\n"}})
    assert esegui(BUONO, "--no-visuale") == 3
    assert "#1" in capsys.readouterr().out


def test_d2_the_hook_and_babysit_read_the_same_points(monkeypatch):
    runner(monkeypatch, {"issues": {1: "## Fix\n1. a\n2. b\n"}})
    assert cp.leggi_issue(1, "o/r") == ["a", "b"]


def test_d4_closes_on_a_pull_request_is_refused_with_the_word_to_use(esegui, monkeypatch, capsys):
    runner(monkeypatch, {"pr": {1}})
    assert esegui(BUONO, "--no-visuale") == 1
    assert "Sostituisce #1" in capsys.readouterr().out


def test_d4_refs_on_a_pull_request_warns(esegui, monkeypatch, capsys):
    runner(monkeypatch, {"pr": {5}})
    assert esegui(BUONO.replace("Closes #1\n", "Closes #1\nRefs #5\n"), "--no-visuale") == 3
    assert "#5" in capsys.readouterr().out


def test_d6_a_receipt_signed_before_the_head_warns_until_the_row_names_the_head(esegui, monkeypatch, capsys):
    runner(monkeypatch, {})
    riga = "| Controllo | Esito |\n|---|---|\n| Real-test | verde · staging `bbbbbbb` · breaker |\n\n"
    corpo = BUONO.replace("Closes #1\n", riga + "Closes #1\n")
    assert esegui(corpo, "--pr", "9", "--no-visuale") == 3
    assert "Real-test" in capsys.readouterr().out
    allineato = corpo.replace("`bbbbbbb`", "`bbbbbbb`, head `aaaaaaa` (2 commit dopo)")
    assert esegui(allineato, "--pr", "9", "--no-visuale") == 0


def test_d7_an_image_pinned_to_a_commit_must_open(esegui, monkeypatch, capsys):
    visti = runner(monkeypatch, {"mancanti": ["shots/a.png"]})
    assert esegui(BUONO, "--no-visuale") == 3
    assert "shots/a.png" in capsys.readouterr().out
    assert any("repos/o/r/contents/shots/a.png?ref=" + "c" * 40 in " ".join(v) for v in visti)


def test_d7_after_publishing_githubs_closing_links_are_read_back(esegui, monkeypatch, capsys):
    runner(monkeypatch, {"body": BUONO.replace("Closes #1\n", "Closes #1\nCloses #2\n"), "chiuse": [1]})
    assert esegui(None, "--verifica-pubblicato", "9", "-R", "o/r") == 1
    assert "#2" in capsys.readouterr().out
    runner(monkeypatch, {"chiuse": [1]})
    assert esegui(None, "--verifica-pubblicato", "9", "-R", "o/r") == 0


def test_d8_a_head_that_moved_since_the_draft_blocks(esegui, monkeypatch, capsys):
    runner(monkeypatch, {})
    assert esegui(BUONO, "--pr", "9", "--head", "bbbbbbb", "--no-visuale") == 1
    assert "head" in capsys.readouterr().out
    assert esegui(BUONO, "--pr", "9", "--head", "aaaaaaa", "--no-visuale") == 0
    assert esegui(BUONO, "--head", "aaaaaaa", "--no-visuale") == 2
