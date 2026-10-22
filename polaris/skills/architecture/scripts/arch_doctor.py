#!/usr/bin/env python3
"""arch_doctor.py — measure the architectural backbone, then stop.

Owns no verdict of its own: it resolves each checker the harness already ships, runs it,
and reports `check | verdict | evidence | realignment`. It never repairs what it finds and
never writes inside the repository under test — repairing drift as a side effect is how a
stale document gets resealed while still being false. A checker that is not installed here
is UNKNOWN, never a green zero.

    arch_doctor.py --root <repo> [--quick] [--json] | --selfcheck

Exit: 0 always in --quick · 2 in full mode when a blocking check is RED.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch_doctor_sources import (  # noqa: E402 — one table, not two
    ADOPT, BACKBONE_UNKNOWN, CHECKS, MENU, NOT_ADOPTED, NOT_HERE, QUICK_BUDGET, REPAIR,
    STALE, TIMEOUT, copy_ledger, resolve, vault)

def probe(spec: dict, argv: list[str], budget: tuple) -> tuple[str, str]:
    """Run the checker and read ITS contract. A code it never promised is the checker
    failing — reported as such, never as a verdict about the repository."""
    cwd, limit = budget
    try:
        done = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired:
        cut = "over quick budget" if limit < TIMEOUT else f"timeout after {limit:.0f}s"
        return "UNKNOWN", cut
    except (OSError, subprocess.SubprocessError) as exc:
        return "UNKNOWN", f"checker failed: could not run: {exc}"
    out = (done.stdout + done.stderr).strip()
    line = " ".join(out.split()) or "(no output)"  # a JSON receipt's first line is `{`
    verdict = verdict_of(spec, done.returncode, out)
    mark = "checker failed: " if verdict == "UNKNOWN" else ""
    return verdict, f"exit {done.returncode} · {mark}{line[:150]}"


def verdict_of(spec: dict, code: int, out: str) -> str:
    """GREEN, RED or UNKNOWN — and only the codes the checker declared may mean RED.

    A traceback is read BEFORE the exit code: a crash exits 1, and 1 is what two of these
    checkers declare as their RED, so reading the code first lets a crash borrow a verdict."""
    if "Traceback (most recent call last)" in out:
        return "UNKNOWN"
    clean = spec.get("clean_line")
    if clean is not None:
        if code != 0:
            return "UNKNOWN"
        return "GREEN" if re.search(clean, out, re.M) else "RED"
    if code == 0:
        return "GREEN"
    return "RED" if code in spec.get("red_exits", ()) else "UNKNOWN"


def make_row(spec: dict, verdict: str, parts: tuple[str, str]) -> dict:
    """A thing this repository never adopted is UNKNOWN, and only a RED can block: a row
    nobody could judge is not the row to lead a menu with."""
    final = "UNKNOWN" if any(c in parts[0] for c in NOT_ADOPTED) else verdict
    return {"check": spec["check"], "verdict": final, "evidence": parts[0], "fix": parts[1],
            "blocking": spec.get("blocking", False) and final == "RED"}


def unavailable(spec: dict, ctx: dict) -> dict | None:
    """The four ways a row has no measurement to report, each said out loud."""
    rel = spec["script"]
    if resolve(rel, ctx["root"], ctx["vault"]) is None:
        return make_row(spec, "UNKNOWN", (f"{NOT_HERE}: {rel}",
                                          f"install the Polaris harness, then: {spec['fix']}"))
    if "args" not in spec:
        return make_row(spec, "UNKNOWN", (f"{rel} · {spec['why']}", spec["fix"]))
    if spec.get("adopted_when") and not (ctx["root"] / spec["adopted_when"]).exists():
        return make_row(spec, "UNKNOWN", (
            f"{rel} · nothing to judge: no {spec['adopted_when']}/ in this repository", ADOPT))
    if spec.get("intents") and not (ctx["root"] / spec["intents"]).is_file():
        return make_row(spec, "UNKNOWN", (
            f"{rel} · intents not wired: no {spec['intents']}, so every changed file reads "
            "as unowned and the row would be RED by construction",
            f"record the active intents in {spec['intents']}, then: {spec['fix']}"))
    if spec.get("ledger") and not (ctx["root"] / spec["ledger"]).is_file():
        return make_row(spec, "UNKNOWN",
                        (f"{rel} · nothing recorded at {spec['ledger']}", spec["fix"]))
    return None


def row(spec: dict, ctx: dict) -> dict:
    """One check: resolve it, run it inside the remaining budget, report what it said."""
    absent = unavailable(spec, ctx)
    if absent is not None:
        return absent
    limit = min(TIMEOUT, ctx["deadline"] - time.monotonic()) if ctx["deadline"] else TIMEOUT
    if limit <= 0:
        return make_row(spec, "UNKNOWN", (f"{spec['script']} · over quick budget "
                                          f"({QUICK_BUDGET:.0f}s for the whole quick measure)",
                                          f"run the full doctor: {spec['fix']}"))
    fields = {"root": ctx["root"], "tmp": ctx["tmp"], "home": ctx["home"],
              "intents": ctx["root"] / spec.get("intents", "."),
              "ledger": copy_ledger(spec, ctx)}
    if fields["ledger"].startswith("UNREADABLE: "):
        return make_row(spec, "UNKNOWN", (
            f"{spec['script']} · ledger unreadable at {spec['ledger']}: "
            f"{fields['ledger'][12:]}", f"make {spec['ledger']} readable, then: {spec['fix']}"))
    argv = [sys.executable, "-I", str(resolve(spec["script"], ctx["root"], ctx["vault"]))]
    argv += [a.format(**fields) for a in spec["args"]]
    verdict, seen = probe(spec, argv, (ctx["root"], limit))
    return make_row(spec, verdict, (f"{spec['script']} · {seen}", fix_of(spec, seen, verdict)))


def fix_of(spec: dict, seen: str, verdict: str) -> str:
    """A stale seal is never repaired blind, and a repository that never adopted the
    backbone is not a repository that failed it."""
    if any(cause in seen for cause in NOT_ADOPTED):
        return ADOPT
    if verdict == "UNKNOWN" and "checker failed" in seen:
        return f"the checker itself failed — fix it before reading this row: {spec['fix']}"
    return REPAIR if any(code in seen for code in STALE) else spec["fix"]


def rows(root: Path, quick: bool = False) -> list[dict]:
    """The scratch directory is why nothing lands in the repository: every ledger a checker
    could append to is a copy inside it, thrown away with the run."""
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        ctx = {"root": root, "vault": vault(root), "tmp": Path(tmp), "home": Path.home(),
               "deadline": time.monotonic() + QUICK_BUDGET if quick else None}
        return [row(s, ctx) for s in CHECKS if s.get("quick") or not quick]


def exit_code(result: list[dict], quick: bool = False) -> int:
    """`--quick` reports and never blocks; the full run blocks on a blocking RED."""
    if quick:
        return 0
    return 2 if any(r["verdict"] == "RED" and r["blocking"] for r in result) else 0


def selfcheck() -> int:
    """The ignorance branch: an empty repository with an empty vault knows nothing. The
    backbone checker ships in this skill, so its row runs and reads the repository as never
    adopted; every other row has no checker to run."""
    saved = os.environ.get("POLARIS_VAULT", "")
    with tempfile.TemporaryDirectory() as empty:
        os.environ["POLARIS_VAULT"] = empty
        try:
            result = rows(Path(empty))
        finally:
            os.environ["POLARIS_VAULT"] = saved
    assert result and all(r["verdict"] == "UNKNOWN" for r in result), result
    own = [r for r in result if r["check"] == "backbone"]
    assert own and "LIVE_DOC_MISSING" in own[0]["evidence"] and own[0]["fix"] == ADOPT, own
    assert all(NOT_HERE in r["evidence"] for r in result if r["check"] != "backbone"), result
    assert exit_code(result) == 0 and exit_code(result, quick=True) == 0
    print(f"arch_doctor selfcheck OK — {len(result)} checks, all UNKNOWN, exit 0")
    return 0


def menu(result: list[dict]) -> list[str]:
    """`prossimo:` — the rows hand the work on by themselves (menu.md, not the reader)."""
    lines = []
    for r in result:
        line = MENU.get((r["check"], r["verdict"]))
        if r["check"] == "backbone" and r["verdict"] == "UNKNOWN":
            line = next((v for k, v in BACKBONE_UNKNOWN if k in r["evidence"]), None)
        if line and line not in lines:
            lines.append(line)
    if all(r["verdict"] == "UNKNOWN" for r in result):  # menu.md: audit or design, no seals needed
        lines.append("/architecture design <module> — works on the code itself, needs no seals")
    if any("over quick budget" in r["evidence"] or "timeout" in r["evidence"] for r in result):
        lines.append("/architecture doctor — the quick measure did not finish; the full run says which check")
    return ["prossimo:"] + [f"  {l}" for l in lines] if lines else [
        "prossimo: nessun verbo — ogni riga misurata dice UNKNOWN senza un passo che segua"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="measure the backbone, repair nothing")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--which", metavar="SCRIPT",
                    help="print where a shared checker (e.g. check_context_backbone.py) resolves")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if args.which:
        found = resolve(f"scripts/{args.which}", args.root.resolve(), vault(args.root.resolve()),
                        own_first=True)
        if found is None:
            print(f"{NOT_HERE}: scripts/{args.which}", file=sys.stderr)
            return 2
        print(found)
        return 0
    result = rows(args.root, args.quick)
    if args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return exit_code(result, args.quick)
    print("check | verdict | blocking | evidence | realignment\n" + "-" * 76)
    for entry in result:
        print(" | ".join((entry["check"], entry["verdict"],
                          "blocking" if entry["blocking"] else "context",
                          entry["evidence"], entry["fix"])))
    print("\n".join(menu(result)))
    return exit_code(result, args.quick)


if __name__ == "__main__":
    raise SystemExit(main())
