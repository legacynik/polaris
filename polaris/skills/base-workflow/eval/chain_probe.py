#!/usr/bin/env python3
"""chain_probe.py — does a real agent take the chain `references/chains.md` draws?

Runs Claude Code headless on each case of `chain_cases.json` in a throwaway git repo, with the
skills installed on this machine, no Bash/Edit/Write (nothing can change), and reads which skills
it actually invoked from the stream (`tool_use` of the Skill tool). A case passes when every skill
in `expect` was invoked and none in `forbid` was. Costs model calls: run it on purpose, not in CI.

  python3 chain_probe.py [--case ID] [--model sonnet] [--timeout 240] [--repo <real checkout>]
  python3 chain_probe.py --selfcheck      # parser only, no model call
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "chain_cases.json"


def final_text(stream: str) -> str:
    """The agent's last message to the person (the stream's `result`)."""
    out = ""
    for line in stream.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            out = str(ev.get("result") or "")
    return out


def skills_called(stream: str) -> list[str]:
    """Skill names from Skill tool calls in a stream-json transcript, in call order."""
    out = []
    for line in stream.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        for part in (ev.get("message") or {}).get("content") or []:
            if isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "Skill":
                name = (part.get("input") or {}).get("skill", "")
                out.append(name.split(":")[-1])
    return out


def verdict(case: dict, called: list[str], text: str = "") -> list[str]:
    errs = [f"expected `{s}` to be invoked" for s in case.get("expect", []) if s not in called]
    errs += [f"`{s}` must not be invoked here" for s in case.get("forbid", []) if s in called]
    nxt = case.get("next_any", [])
    asks = "?" in text[-600:]  # a STOP: the skill asks the person, with options, before going on
    if nxt and not asks and not any(n.lower() in text.lower() for n in nxt):
        errs.append(f"the last message neither asks nor proposes a next step (any of {nxt})")
    return errs


def run_case(case: dict, model: str, timeout: int, repo: str | None) -> tuple[list[str], list[str]]:
    with tempfile.TemporaryDirectory() as tmp:
        d = repo or tmp
        if not repo:  # an empty repo makes the agent stop at "no code here": prefer --repo
            subprocess.run(["git", "init", "-q", d], check=True)
            (Path(d) / "README.md").write_text("# demo-shop\nA small quoting app: quotes, VAT, CSV export.\n")
        cmd = ["claude", "-p", case["prompt"], "--output-format", "stream-json", "--verbose",
               "--model", model, "--disallowedTools", "Bash", "Edit", "Write", "NotebookEdit"]
        try:
            r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout,
                               stdin=subprocess.DEVNULL)
            stream = r.stdout
        except subprocess.TimeoutExpired as e:
            stream = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    called = skills_called(stream)
    return called, verdict(case, called, final_text(stream))


def selfcheck() -> int:
    stream = "\n".join([
        json.dumps({"message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "grill"}}]}}),
        "not json",
        json.dumps({"message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]}}),
        json.dumps({"message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "x:plan-area"}}]}}),
    ])
    assert skills_called(stream) == ["grill", "plan-area"]
    assert verdict({"expect": ["grill"], "forbid": ["implement"]}, ["grill"]) == []
    assert verdict({"expect": ["bugfix"], "forbid": ["grill"]}, ["grill"]) == [
        "expected `bugfix` to be invoked", "`grill` must not be invoked here"]
    case = {"expect": ["grill"], "next_any": ["plan-area", "prototype"]}
    assert verdict(case, ["grill"], "Taglia Media: prossimo passo `plan-area`.") == []
    assert verdict(case, ["grill"], "Fatto.") != []
    assert verdict(case, ["grill"], "A o B?") == []
    assert final_text(json.dumps({"type": "result", "result": "ok next"})) == "ok next"
    json.loads(CASES.read_text())
    print("SELFCHECK OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--repo", help="a real checkout to run in (read-only: Bash/Edit/Write are denied)")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    cases = [c for c in json.loads(CASES.read_text()) if not a.case or c["id"] == a.case]
    failed = 0
    for c in cases:
        called, errs = run_case(c, a.model, a.timeout, a.repo)
        failed += bool(errs)
        print(f"{'PASS' if not errs else 'FAIL'} {c['id']}: called {called or 'nothing'}"
              + ("" if not errs else " — " + "; ".join(errs)))
    print(f"{len(cases) - failed}/{len(cases)} cases take the expected chain")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
