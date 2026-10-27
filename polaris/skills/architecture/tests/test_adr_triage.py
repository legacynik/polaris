"""adr_triage.py reports the signals of every ADR in a folder and writes nothing.

2026-10-26: a product repo held 97 ADRs, one of them grown 13 appended update sections into a
diary. `doctor` on an ADR folder must surface that from the boundary — the printed table — and
leave the folder byte-for-byte as it found it.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

TRIAGE = Path(__file__).resolve().parents[1] / "scripts" / "adr_triage.py"

DIARY = """---
kind: spec
status: accepted
governed:
  - app/ingest.py
  - app/rows.py
---
# Rows enter the catalogue by class
## 1. Context
## 2. Decision
## 2bis. Aggiornamento 2026-09-25: totals decide
## 2ter. Update 2026-09-30: spreadsheets too
"""
SHORT = "---\nkind: architecture\nstatus: accepted\n---\n# Pricing runs as its own service\n## Context\n"


def snapshot(d: Path) -> dict:
    return {p.name: p.read_bytes() for p in d.iterdir()}


def test_a_diary_and_a_long_adr_are_flagged_and_the_folder_is_untouched():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "diary.md").write_text(DIARY)
        (d / "short.md").write_text(SHORT)
        (d / "long.md").write_text("# 3. A long one\n" + "line\n" * 450)
        (d / "README.md").write_text("# index\n")
        before = snapshot(d)
        done = subprocess.run([sys.executable, str(TRIAGE), str(d), "--json"],
                              capture_output=True, text=True)
        after = snapshot(d)
    assert done.returncode == 0, done.stderr
    rows = {r["file"]: r for r in json.loads(done.stdout)["rows"]}
    assert set(rows) == {"diary.md", "short.md", "long.md"}
    assert (rows["diary.md"]["appended"], rows["diary.md"]["governed"], rows["diary.md"]["kind"]) == (2, 2, "spec")
    assert [rows[f]["flags"] for f in ("diary.md", "long.md", "short.md")] == ["appended", "long", ""]
    assert before == after


def test_a_missing_folder_exits_2():
    done = subprocess.run([sys.executable, str(TRIAGE), "/nonexistent-adr-dir"], capture_output=True, text=True)
    assert done.returncode == 2
