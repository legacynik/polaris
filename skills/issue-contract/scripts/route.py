#!/usr/bin/env python3
"""GitHub issue or bead? The filter of the operating model (§4), on facts the agent holds.

A GitHub issue only if ALL hold: a human must schedule or approve it; it will not be done inside
the current PR or phase; it has a "Come si prova" section and an `area:`; it duplicates no open
issue. Otherwise it is a bead, and the reason names every condition that failed. With `--bead`
the same door promotes an existing bead, which then points at its issue through `external_ref`.
Never calls `bd` or `gh`: it prints the decision and the next command, as JSON on one line.

    python3 route.py --human yes --in-current-work no --test-section yes --area pricing --dup none
    python3 route.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys


def twin(value: str) -> str:
    """The duplicate search answered: `none`, or the number of the open twin. Blank is not an answer."""
    v = value.strip().lstrip("#")
    if v != "none" and not v.isdigit():
        raise argparse.ArgumentTypeError(f"{value!r}: give the open twin's number, or none after searching")
    return v


def decide(a) -> dict:
    failed = [why for broken, why in (
        (a.human == "no", "no human must schedule or approve it"),
        (a.in_current_work == "yes", "it closes inside the current PR or phase"),
        (a.test_section == "no", "no 'Come si prova' section"),
        (not a.area.strip(), "no area:"),
        (a.dup != "none", f"duplicates open #{a.dup}"),
    ) if broken]
    if not failed:
        nxt = f"bd update {shlex.quote(a.bead)} --external-ref 'gh#<N>'" if a.bead else ""
        return {"route": "github", "reason": "all four conditions hold", "next": nxt}
    reason = "; ".join(failed)
    if a.bead:
        return {"route": "beads", "reason": f"stays bead {a.bead}: {reason}", "next": ""}
    if not (a.src.strip() and a.kind.strip()):
        raise ValueError("a bead needs --src and --kind (its area: label too, when it has one)")
    labels = ",".join(f"{k}:{v}" for k, v in (("src", a.src), ("kind", a.kind), ("area", a.area.strip())) if v)
    nxt = f"bd create '<title>' -t {shlex.quote(a.type)} -l {shlex.quote(labels)}"
    if a.source:
        nxt += f" --deps discovered-from:{shlex.quote(a.source)}"
    return {"route": "beads", "reason": reason, "next": nxt}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="route.py", description=__doc__.splitlines()[0])
    for flag in ("--human", "--in-current-work", "--test-section"):
        ap.add_argument(flag, choices=("yes", "no"), required=True)
    ap.add_argument("--area", required=True, help="the area: label, empty when there is none")
    ap.add_argument("--dup", required=True, type=twin, help="number of the open twin, or none")
    ap.add_argument("--bead", default="", help="promote this existing bead instead of creating one")
    ap.add_argument("--from", dest="source", default="", help="bead of the work that found it")
    ap.add_argument("--type", default="task", help="bd issue type")
    ap.add_argument("--src", default="", help="who found it: loop, real-test, review, human…")
    ap.add_argument("--kind", default="", help="finding, follow-up, spike, idea…")
    return ap


def selfcheck() -> int:
    ok = "--human yes --in-current-work no --test-section yes --area pricing --dup none".split()
    ok += ["--src", "loop", "--kind", "finding"]
    run = lambda *extra: decide(parser().parse_args(ok + list(extra)))  # noqa: E731
    assert run()["route"] == "github"
    assert run("--human", "no")["route"] == "beads"
    assert run("--dup", "#12")["reason"] == "duplicates open #12"
    assert run("--bead", "pol-1")["next"] == "bd update pol-1 --external-ref 'gh#<N>'"
    assert run("--area", " ", "--from", "pol-2")["next"].endswith("--deps discovered-from:pol-2")
    try:
        decide(parser().parse_args(ok[:-4] + ["--human", "no"]))
        raise AssertionError("a bead without src/kind must be refused")
    except ValueError:
        pass
    for blank in ("", "#", "None"):
        try:
            twin(blank)
            raise AssertionError(f"blank duplicate search {blank!r} must be refused")
        except argparse.ArgumentTypeError:
            pass
    print("SELFCHECK OK — four conditions, duplicate, promotion, discovered-from, refusals")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--selfcheck"]:
        return selfcheck()
    try:
        print(json.dumps(decide(parser().parse_args(argv))))
    except ValueError as exc:
        print(f"route.py: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
