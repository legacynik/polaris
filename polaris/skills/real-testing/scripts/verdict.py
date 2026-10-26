#!/usr/bin/env python3
"""verdict.py — validates (or scaffolds) a real-test verdict against the real perimeter.

Orchestrates `verdict_checks.py` (pure rules) against `perimeter.py` (the real
perimeter, recomputed now from git) — see `verdict_checks.py` for the detail
of the rules and which registry entry each one closes.

Usage:
    verdict.py new      --repo R [--base REF] [--head REF|STAGED] [--out FILE]
    verdict.py validate <file> --repo R [--base REF] [--head REF|STAGED]
    verdict.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perimeter  # noqa: E402
import verdict_checks as vc  # noqa: E402
from verdict_attack import check as check_attack  # noqa: E402

def validate(verdict_path: Path, repo: Path, perim: dict) -> tuple[bool, list[str]]:
    """Validates an ALREADY-written verdict against an ALREADY-computed perimeter (3 params, not 4:
    the caller decides base/head once, then can validate several verdicts on the same
    perimeter without calling git every time)."""
    try:
        v = vc.load_verdict(verdict_path)
    except ValueError as e:
        return False, [str(e)]
    errs = (
        vc.validate_verdetto_value(v)
        + vc.validate_hash(v, perim["content_hash"])
        + vc.validate_files_covered(v, perim["files"])
        + vc.validate_branches_covered(v, perim["new_branches"])
        + vc.validate_evidence(v, repo)
        + vc.validate_raccolto(v)
        + check_attack(v)
    )
    return (not errs), errs

def _guess_class(path: str) -> str:
    p = path.lower()
    if any(k in p for k in ("migrat", ".sql", "/schema")):
        return "db-migration"
    if any(k in p for k in ("test_", "_test.", ".spec.", ".test.")):
        return "test-only"
    if p.endswith((".md", ".mdx")) or "/docs/" in p:
        return "docs"
    if any(k in p for k in ("package.json", "requirements.txt", "go.mod", "cargo.toml", "poetry.lock")):
        return "dependency"
    if ".github/workflows" in p or p.endswith((".yml", ".yaml")) or "dockerfile" in p:
        return "config-ci"
    if any(k in p for k in ("prompt", "/llm", "/agent")):
        return "llm-agent"
    if p.endswith((".tsx", ".jsx", ".vue", ".svelte", ".css")):
        return "frontend"
    return "symbol"

def new_template(repo: Path, base_ref: str | None, head_ref: str) -> dict:
    perim = perimeter.build_perimeter(repo, base_ref, head_ref)
    matrix = [{"file": f, "class": _guess_class(f), "evidence": "assumed",
               "evidence_artifact": None, "exception_ticket": None, "branches_exercised": [], "attack": []}
              for f in perim["files"]]
    return {
        "verdetto": "NOT-MERGEABLE",
        "base": perim["base"],
        "content_hash": perim["content_hash"],
        "matrix": matrix,
        "raccolto": [],
        "new_branches_da_coprire": perim["new_branches"],
    }

def _fixture(repo: Path) -> str:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    perimeter.git(repo, "config", "user.email", "t@t")
    perimeter.git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    (repo / "migrations").mkdir()
    (repo / "migrations" / "001.sql").write_text("-- noop\n")
    perimeter.git(repo, "add", ".")
    perimeter.git(repo, "commit", "-q", "-m", "base")
    base = perimeter.git(repo, "rev-parse", "HEAD")
    (repo / "a.py").write_text(
        "def f(x):\n    if x:\n        return 1\n    else:\n        return -1\n"
    )
    (repo / "migrations" / "001.sql").write_text("alter table t add column c int;\n")
    perimeter.git(repo, "add", ".")
    return base

def _live_row(tpl: dict) -> dict:
    return next(r for r in tpl["matrix"] if r["file"] == "migrations/001.sql")

def _selfcheck() -> int:  # noqa: C901 — end-to-end fixture walk, sequential by nature
    import os
    import time

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        base = _fixture(repo)
        vpath = repo / "v.json"
        perim = perimeter.build_perimeter(repo, base, "STAGED")  # constant: the tree does not change beyond this

        def check(expect_ok: bool, needle: str, msg: str) -> None:
            ok, errs = validate(vpath, repo, perim)
            assert ok == expect_ok and (expect_ok or any(needle in e for e in errs)), f"{msg}: {errs}"

        tpl = new_template(repo, base, "STAGED")
        assert _live_row(tpl)["class"] == "db-migration", "db-migration class not recognised"
        vpath.write_text(json.dumps(tpl))
        check(False, "new branches", "uncovered else must block")

        for row in tpl["matrix"]:
            row["exception_ticket"] = "ISSUE-1"
        next(r for r in tpl["matrix"] if r["file"] == "a.py")["branches_exercised"] = ["a.py:4"]
        tpl["verdetto"] = "MERGEABLE"
        vpath.write_text(json.dumps(tpl))
        check(False, "raccolto", "empty raccolto must block")

        tpl["raccolto"] = [{"tipo": "difetto", "artifact": "tests/test_migration.py::test_add_col"}]
        vpath.write_text(json.dumps(tpl))
        check(True, "", "assumed+ticket must suffice even on live-required")

        _live_row(tpl)["evidence"] = "not-applicable"
        vpath.write_text(json.dumps(tpl))
        check(False, "not-applicable", "not-applicable on db-migration must block")

        _live_row(tpl)["evidence"] = "live"
        vpath.write_text(json.dumps(tpl))
        check(False, "without evidence_artifact", "live without artifact must block")

        artifact = repo / "trace.json"
        artifact.write_text('{"call_id": "req-selfcheck-1", "query": "alter table t add column c int"}')
        os.utime(artifact, (time.time() - 3600, time.time() - 3600))
        _live_row(tpl)["evidence_artifact"] = "trace.json"
        vpath.write_text(json.dumps(tpl))
        check(False, "stale", "artifact older than the file must block")

        os.utime(artifact, None)
        artifact.write_text('{"note": "handmade, no real call - MagicMock in test"}')
        os.utime(artifact, None)
        vpath.write_text(json.dumps(tpl))
        check(False, "call_id", "fresh+non-empty but without call_id (EVAL-copertura row 3) must block")

        artifact.write_text('{"call_id": "req-selfcheck-1", "query": "alter table t add column c int"}')
        os.utime(artifact, None)
        vpath.write_text(json.dumps(tpl))
        check(True, "", "complete verdict with fresh live proof and call_id must pass")

        stale = dict(tpl, content_hash="deadbeef")
        vpath.write_text(json.dumps(stale))
        check(False, "stale", "stale hash must block")
    print("SELFCHECK OK — 9 end-to-end stages (uncovered-branch/empty-raccolto/assumed-ok/"
          "not-applicable-forbidden/no-artifact/stale-artifact/fresh-without-call_id/pass/stale-hash)")
    return 0

def _cmd_validate(a: argparse.Namespace) -> int:
    repo = Path(a.repo)
    perim = perimeter.build_perimeter(repo, a.base, a.head)
    ok, errs = validate(Path(a.verdict), repo, perim)
    for e in errs:
        print(f"FAIL: {e}", file=sys.stderr)
    print("VALIDATE: OK" if ok else "VALIDATE: REJECTED")
    return 0 if ok else 1

def _cmd_new(a: argparse.Namespace) -> int:
    tpl = new_template(Path(a.repo), a.base, a.head)
    text = json.dumps(tpl, indent=2)
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    else:
        print(text)
    return 0

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    p_new = sub.add_parser("new")
    p_new.add_argument("--repo", required=True)
    p_new.add_argument("--base")
    p_new.add_argument("--head", default="STAGED")
    p_new.add_argument("--out")

    p_val = sub.add_parser("validate")
    p_val.add_argument("verdict")
    p_val.add_argument("--repo", required=True)
    p_val.add_argument("--base")
    p_val.add_argument("--head", default="STAGED")

    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    commands = {"new": _cmd_new, "validate": _cmd_validate}
    if a.cmd not in commands:
        ap.print_help()
        return 1
    try:
        return commands[a.cmd](a)
    except subprocess.CalledProcessError as exc:
        # A reference the history does not hold (HEAD~1 on one commit, HEAD on none): a usage
        # error the caller fixes with --base, never a traceback.
        print(f"verdict: git {' '.join(map(str, exc.cmd[3:]))} failed: "
              f"{(exc.stderr or '').strip() or 'unknown reference'} — pass an existing --base",
              file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
