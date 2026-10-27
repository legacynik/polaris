#!/usr/bin/env python3
"""Read-only signals for every ADR in a folder, so `doctor` can triage it.

    adr_triage.py <adr-dir> [--json]
    adr_triage.py --selfcheck

One row per `*.md` (README, index and template skipped): lines, appended update sections, the
frontmatter's `kind`, `status`, `superseded_by` and `governed` count, and two mechanical flags —
`appended` (dated update sections, never allowed) and `long` (past the two-page budget by far).
Keep, amend, supersede, compact, demote to the ledger or move to the area README is the agent's
call, written in the `call` column of the report; this script never makes it. It opens files for reading only and
always exits 0 on a readable folder, 2 on a missing one.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

LONG = 200  # one to two pages is the budget (references/writing.md); a healthy set's median is ~100
SKIP = {"readme.md", "index.md", "template.md", "_template.md"}
APPENDED = re.compile(
    r"^#{1,6}\s+(?:.*\b(?:aggiornamento|update|addendum|amendment|emendamento)\b"
    r"|\d+(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies|undecies|duodecies"
    r"|tredecies|quaterdecies|quindecies)\b)", re.I | re.M)


def field(front: str, key: str) -> str:
    m = re.search(rf'^\s*"?{key}"?\s*:\s*"?([^"#\n,]*)', front, re.M)
    return m.group(1).strip() if m else ""


def signals(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    front = text[3:text.find("\n---", 3)] if text.startswith("---") and "\n---" in text[3:] else ""
    # ponytail: YAML block lists only; a JSON `governs` array reads as 0 — parse JSON when a register uses it.
    gov = re.search(r"^governed:\s*\n((?:[ \t]+-.*\n?)+)", front, re.M)
    appended = len(APPENDED.findall(text))
    lines = text.count("\n") + (not text.endswith("\n"))
    return {"file": path.name, "lines": lines, "appended": appended,
            "kind": field(front, "kind"), "status": field(front, "status"),
            "superseded_by": field(front, "superseded_by"),
            "governed": len((gov.group(1) or "").strip().splitlines()) if gov else 0,
            "flags": " ".join(f for f, on in (("appended", appended), ("long", lines > LONG)) if on)}


def selfcheck() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.md"
        p.write_text("---\nkind: spec\ngoverned:\n  - a.py\n---\n# T\n## 2bis. Update 2026-01-01\n")
        r = signals(p)
        assert (r["appended"], r["governed"], r["kind"], r["flags"]) == (1, 1, "spec", "appended"), r
        p.write_text("# 2. Short\n## Context\n## Decision\n" + "x\n" * LONG)
        assert (signals(p)["appended"], signals(p)["flags"]) == (0, "long"), signals(p)
    print("adr_triage selfcheck: ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only signals for every ADR in a folder.")
    ap.add_argument("adr_dir", type=Path, nargs="?", default=Path("docs/adr"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="prove the signals on a temp fixture")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return selfcheck()
    if not a.adr_dir.is_dir():
        print(f"adr_triage: not a directory: {a.adr_dir}", file=sys.stderr)
        return 2
    rows = [signals(p) for p in sorted(a.adr_dir.glob("*.md")) if p.name.lower() not in SKIP]
    n = len(rows)
    summary = {"files": n, "lines": sum(r["lines"] for r in rows),
               "max": max((r["lines"] for r in rows), default=0),
               "median": sorted(r["lines"] for r in rows)[n // 2] if n else 0,
               "long": sum(r["lines"] > LONG for r in rows),
               "with_appended": sum(r["appended"] > 0 for r in rows)}
    if a.json:
        print(json.dumps({"summary": summary, "rows": rows}, indent=1))
        return 0
    print(f"{n} ADRs · {summary['lines']} lines · avg {summary['lines'] // n if n else 0} · "
          f"median {summary['median']} · max {summary['max']} · {summary['long']} over {LONG} lines · "
          f"{summary['with_appended']} with appended sections")
    print("\n| file | lines | appended | kind | status | governed | flags | call |\n|---|---|---|---|---|---|---|---|")
    for r in rows:
        status = r["status"] + (f" → {r['superseded_by']}" if r["superseded_by"] not in ("", "null", "none") else "")
        print(f"| {r['file']} | {r['lines']} | {r['appended']} | {r['kind']} | {status} | "
              f"{r['governed']} | {r['flags']} | |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
