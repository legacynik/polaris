"""The PR body the owner merges from, checked like the owner would read it.

2026-10-18: a PR declared `Closes` on an issue whose criteria were five-sevenths unproven; nothing in
the body said so. Fixtures are real: issues and PR bodies of the product repository, and bodies written
by five writers per arm in the eval of this skill (no skill 0/20 criteria, v2 20/20).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import controlla_pr as cp  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def issue(n: int) -> str:
    data = json.loads((FIX / f"issue-{n}.json").read_text())
    return "\n".join([data["body"], *(c["body"] for c in data["comments"])])


ISSUES = {n: cp.criteri(issue(n)) for n in (1719, 1207, 792)}


def body(name: str) -> str:
    return (FIX / name).read_text()


def test_an_issue_counts_each_criterion_once_even_when_its_section_is_repeated():
    assert len(ISSUES[1719]) == 7
    assert len(ISSUES[1207]) == 9
    assert len(ISSUES[792]) == 3  # no checkbox: the three points under «Fix» (first live use, 2026-10-19)


def test_the_v2_body_passes():
    assert cp.controlla(body("buona-v2.md"), ISSUES, visuale=True) == []


def test_a_body_written_without_the_skill_fails_on_the_criteria():
    errori = cp.controlla(body("no-skill.md"), ISSUES, visuale=True)
    assert any("criteri" in e for e in errori)


def test_the_upstream_format_fails_on_the_verdict_and_the_criteria():
    errori = " ".join(cp.controlla(body("pocock.md"), ISSUES, visuale=True))
    assert "In breve" in errori and "criteri" in errori


def test_the_old_format_of_a_real_pr_fails_on_closes_in_one_line():
    errori = cp.controlla(body("pr-1834-vecchio-formato.md"), {}, visuale=True)
    assert any("Closes" in e for e in errori)


def test_closes_on_an_issue_with_an_open_criterion_is_refused():
    testo = body("buona-v2.md").replace("Refs #1719", "Closes #1719")
    assert any("#1719" in e and "Refs" in e for e in cp.controlla(testo, ISSUES, visuale=True))


def test_two_issues_after_one_keyword_are_refused():
    testo = body("buona-v2.md").replace("Closes #792", "Closes #792, #1207")
    assert any("una riga per issue" in e for e in cp.controlla(testo, ISSUES, visuale=True))


def test_a_visible_change_without_a_screenshot_fails():
    senza = "\n".join(l for l in body("buona-v2.md").splitlines() if "<img" not in l and "![" not in l)
    assert any("foto" in e for e in cp.controlla(senza, ISSUES, visuale=True))
    assert not any("foto" in e for e in cp.controlla(senza, ISSUES, visuale=False))


def test_an_empty_body_fails_and_never_passes_by_saying_nothing():
    assert cp.controlla("", ISSUES, visuale=False)


def test_an_unquoted_mermaid_label_with_parentheses_fails():
    testo = body("buona-v2.md") + '\n```mermaid\nflowchart LR\n  A[Impresa (lista)] --> B["ok"]\n```\n'
    assert any("Mermaid" in e for e in cp.avvisi(testo))
    assert not any("Mermaid" in e for e in cp.controlla(testo, ISSUES, visuale=True))


def test_an_em_dash_fails():
    testo = body("buona-v2.md") + "\nuno — due\n"
    assert any("trattino" in e for e in cp.avvisi(testo)) and not cp.controlla(testo, ISSUES, True)


# Fresh critic, 2026-10-18: every body below passed and an owner could not judge any of them.
CODA = ("## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a](https://x/b/c.png?raw=true)\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
TESTA = "## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\n"


def test_c1_the_unfilled_template_fails():
    sk = (Path(__file__).parents[1] / "references" / "template.md").read_text()
    modello = sk.split("```markdown\n")[1].split("\n```")[0].replace("Closes #<n>\nRefs #<m>", "Nessuna issue.")
    assert any("segnaposto" in e for e in cp.controlla(modello, {}, True))


def test_c2_no_decision_on_top_fails():
    assert any("Decisione" in e for e in cp.controlla("## In breve\n\nNessuna issue\n" + CODA, {}, True))


def test_c3_criteria_under_other_headings_still_count():
    issue_testo = "## Requisiti\n- [ ] a\n- [ ] b\n- [ ] c\n## Done when\n- [ ] d\n"
    assert len(cp.criteri(issue_testo)) == 4
    assert len(cp.criteri("## Note\n- [ ] solo una casella\n")) == 1


def test_c4_partial_rows_cannot_close():
    corpo = TESTA + "Closes #1\n## Criteri delle issue\n### #1 t\n| 1 | a | 🟡 parziale | log |\n" + CODA
    assert any("Refs" in e for e in cp.controlla(corpo, {1: ["a"]}, True))


def test_c6_one_issue_under_two_keywords_fails():
    corpo = TESTA + "Closes #1\nRefs #1\n## Criteri delle issue\n### #1 t\n| 1 | a | ✅ | log |\n" + CODA
    assert any("#1" in e and "due" in e for e in cp.controlla(corpo, {1: ["a"]}, True))


def test_c7_close_words_anywhere_in_a_line_are_read():
    corpo = TESTA + "Nessuna issue.\nQuesta PR fixed #7 per caso.\n" + CODA
    assert any("#7" in e for e in cp.controlla(corpo, {7: ["a"]}, True))


def test_c8_a_tick_without_proof_does_not_count():
    corpo = TESTA + "Closes #1\n## Criteri delle issue\n### #1 t\n| | | ✅ | |\n" + CODA
    assert any("prova" in e for e in cp.controlla(corpo, {1: ["a"]}, True))


def test_c9_headings_inside_a_code_fence_do_not_count_and_only_warn():
    corpo = TESTA + "Nessuna issue.\n```\n## Cosa cambia\n## Decisioni\n## Prove\n## Cosa resta aperto\n## Rischio del merge\n```\n"
    assert any("Cosa cambia" in e for e in cp.avvisi(corpo, False)) and cp.controlla(corpo, {}, False) == []


def test_c5_an_unreadable_diff_is_not_read_as_no_ui(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import subprocess
    subprocess.run(["git", "init", "-q"], check=True)
    try:
        cp.tocca_ui()
    except cp.NonSo:
        return
    raise AssertionError("tocca_ui answered without a readable base")


def test_c5_unknown_visibility_warns_instead_of_blocking():
    corpo = TESTA + "Nessuna issue.\n" + CODA.replace("![a](https://x/b/c.png?raw=true)", "test verdi")
    assert cp.controlla(corpo, {}, None) == [] and any("foto" in e for e in cp.avvisi(corpo, None))


# Second fresh critic, 2026-10-18.
def test_r2_the_verdict_is_read_from_its_own_cell():
    corpo = TESTA + "Closes #1\n## Criteri delle issue\n### #1 t\n| 1 | b (✅ lato backend) | ❌ | manca |\n" + CODA
    assert any("Refs" in e for e in cp.controlla(corpo, {1: ["b"]}, True))


def test_r2_closes_by_url_or_owner_repo_is_read():
    for forma in ("Closes https://github.com/o/r/issues/7", "Closes o/r#7"):
        assert 7 in cp.riferimenti(TESTA + forma + "\n" + CODA)[0], forma


def test_r2_well_written_bodies_with_tags_or_inline_code_are_not_placeholders():
    extra = ("Il componente `<QuotePanel>` e `list<str>`, latenza <200 ms.\n"
             "<table><tr><td><img src=\"u\"></td></tr></table>\n<video src=\"v\"></video>\n<https://x.y/z>\n")
    corpo = TESTA + "Nessuna issue.\n" + extra + CODA
    assert cp.controlla(corpo, {}, True) == []


def test_r2_a_parenthetical_issue_is_not_a_second_closed_issue():
    corpo = TESTA + "Closes #1 (era la #331 regredita)\n## Criteri delle issue\n### #1 t\n| 1 | a | ✅ | log |\n" + CODA
    assert cp.controlla(corpo, {1: ["a"]}, True) == []


def test_r2_refs_does_not_demand_a_table_and_the_colon_may_sit_outside_the_bold():
    corpo = TESTA.replace("**Decisione richiesta:**", "**Decisione richiesta**:") + "Refs #500\n" + CODA
    assert cp.controlla(corpo, {500: ["c"] * 30}, True) == []


def test_r2_the_visible_decision_can_come_from_the_prs_own_files():
    assert cp.ui_da_file(["frontend/src/Panel.tsx", "README.md"]) is True
    assert cp.ui_da_file(["backend/app.py"]) is False
