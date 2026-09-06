#!/usr/bin/env python3
"""branches.py — rileva rami condizionali NUOVI in un diff unificato (euristica).

Risponde a G1.6 (il real-test copre solo il ramo appena fixato): scandisce le
righe aggiunte di un `git diff` e riconosce `if/elif/else/except/case/switch/
match/catch` — usato da perimeter.py per popolare `new_branches`, che
verdict.py poi pretende in `branches_exercised`.

ponytail: regex sulle righe aggiunte, non un parser AST per linguaggio — falsi
positivi su stringhe/commenti che assomigliano a `if ` sono il tetto noto.
Il prefisso opzionale di parentesi graffe copre lo stile brace su una riga (`} else if (...) {`,
`} catch (e) {` — Java/JS/TS/Go/C/Rust, trovato scoperto in
EVAL-real-test-bypass.md via D). Resta un falso negativo noto: `}` e la
keyword su due righe AGGIUNTE separate non consecutive nel diff (raro, lo
stile Allman mette gia' `else`/`catch` a inizio riga e matcha da solo).
Upgrade path: coverage tool nativi per stack quando flow-cli (job 7) li espone.

Uso: branches.py --selfcheck
"""
from __future__ import annotations

import re
import sys

BRANCH_RE = re.compile(
    r"^\s*\}*\s*(if\b|elif\b|elsif\b|elseif\b|else\b|except\b|case\b|switch\b|match\b|catch\b)"
)
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _file_from_plus_marker(line: str, current: str | None) -> str | None:
    if line.startswith("+++ b/"):
        return line[len("+++ b/") :]
    return current


def _process_diff_line(
    line: str, current_file: str | None, newline: int
) -> tuple[str | None, int, dict | None]:
    """Un passo dello state machine di parsing diff. Ritorna (file, newline, hit)."""
    if line.startswith("+++ "):
        return _file_from_plus_marker(line, current_file), newline, None
    m = HUNK_RE.match(line)
    if m:
        return current_file, int(m.group(1)), None
    if line.startswith("+") and not line.startswith("+++"):
        content = line[1:]
        hit = None
        if BRANCH_RE.match(content):
            hit = {"file": current_file, "line": newline, "snippet": content.strip()[:80]}
        return current_file, newline + 1, hit
    if line.startswith(" "):
        return current_file, newline + 1, None
    return current_file, newline, None


def detect_new_branches(diff_text: str) -> list[dict]:
    """Righe aggiunte che introducono un ramo condizionale nuovo (euristica)."""
    found: list[dict] = []
    current_file: str | None = None
    newline = 0
    for line in diff_text.splitlines():
        current_file, newline, hit = _process_diff_line(line, current_file, newline)
        if hit:
            found.append(hit)
    return found


def _selfcheck() -> int:
    diff = (
        "diff --git a/a.py b/a.py\n"
        "+++ b/a.py\n"
        "@@ -1,4 +1,6 @@\n"
        " def f(x):\n"
        "     if x:\n"
        "         return 1\n"
        "+    elif x < 0:\n"
        "+        return -1\n"
        "     return 0\n"
    )
    found = detect_new_branches(diff)
    assert len(found) == 1, f"atteso 1 ramo nuovo, trovati {len(found)}: {found}"
    assert found[0] == {"file": "a.py", "line": 4, "snippet": "elif x < 0:"}, found

    no_branch_diff = "diff --git a/b.py b/b.py\n+++ b/b.py\n@@ -1,1 +1,2 @@\n x = 1\n+y = 2\n"
    assert detect_new_branches(no_branch_diff) == [], "riga aggiunta senza ramo non deve matchare"

    context_only = "diff --git a/c.py b/c.py\n+++ b/c.py\n@@ -1,2 +1,2 @@\n if x:\n     return 1\n"
    assert detect_new_branches(context_only) == [], "righe di contesto (non aggiunte) non contano"

    brace_diff = (
        "diff --git a/a.js b/a.js\n"
        "+++ b/a.js\n"
        "@@ -1,4 +1,6 @@\n"
        " function f(x) {\n"
        "   if (x) { return 1; }\n"
        "+  else if (x < 0) { throw new Error(); }\n"
        "+  } catch (e) { return -1; }\n"
        "   return 0;\n"
        " }\n"
    )
    brace_found = detect_new_branches(brace_diff)
    assert len(brace_found) == 2, f"stile brace (D, EVAL-bypass): atteso 2 rami, trovati {brace_found}"
    assert brace_found[0]["snippet"].startswith("else if"), brace_found
    assert brace_found[1]["snippet"].startswith("} catch"), brace_found

    print("SELFCHECK OK — 5 asserzioni (ramo nuovo/nessun ramo/contesto ignorato/brace-style x2)")
    return 0


if __name__ == "__main__":
    sys.exit(_selfcheck() if "--selfcheck" in sys.argv else 1)
