#!/usr/bin/env python3
"""T2b economico — rank-1 proxy: one cheap first-turn call per query.

The protocol's real T2b runs the whole harness three times per case
(references/eval-protocol.md): minutes and dollars per skill, so nobody re-ran it
and eleven descriptions sat over budget with the debt declared in
`_standard/nonconforming.allow` instead of paid. The cheap stand-in: the whole
catalogue goes into ONE prompt, a small model names the skill it would reach for
first, and the rank-1 rate is counted from those answers.

    rank1_cheap.py --catalog CAT.json --queries eval/split/test.json --slug SLUG
    rank1_cheap.py --build-catalog DIR [DIR ...] --out CAT.json
    rank1_cheap.py --selfcheck

It is a PROXY and must be calibrated before it is believed (eval-protocol.md,
"Calibrating the cheap proxy"). Transport is `claude -p --safe-mode --tools ""`
with a router system prompt: one call, no hooks, no skills injected, so the
catalogue ranked is the one passed in — and stdlib only, nothing installed.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import frontmatter, load_eval_cases  # noqa: E402 — one implementation each

EXCLUDED = "<excluded>"
INPUT_FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
SYSTEM = (
    "You are the skill router of an agent harness. You are given the catalogue of "
    "installed skills and one user message. Name the SINGLE skill whose description "
    "makes it fire first on that message, or NONE if no skill should fire. "
    "Answer with the slug alone, nothing else."
)


def build_catalog(roots: list[Path]) -> dict[str, str]:
    """slug -> description, first root wins. A later copy of the same slug must not
    rewrite the trigger text: the harness loads one, and which one is not this
    script's guess to make."""
    catalog: dict[str, str] = {}
    for root in roots:
        for md in sorted(Path(root).glob("*/SKILL.md")):
            fm = frontmatter(md.read_text())
            slug = fm.get("name") or md.parent.name
            if slug not in catalog and fm.get("description"):
                catalog[slug] = fm["description"]
    return catalog


def render(catalog: dict[str, str], query: str) -> str:
    lines = [f"- {slug}: {desc}" for slug, desc in sorted(catalog.items())]
    return ("CATALOGUE\n" + "\n".join(lines)
            + f"\n\nUSER MESSAGE\n{query}\n\nWhich skill fires first? Slug or NONE.")


def pick(answer: str, slugs) -> str | None:
    """The reply parsed into one slug. NONE, an unparseable answer and an ambiguous
    one all read as no pick — a miss, never an exclusion: the model DID answer."""
    words = set(re.findall(r"[A-Za-z0-9_-]+", answer or ""))
    named = sorted(words & set(slugs))
    return named[0] if len(named) == 1 else None


def tally(cases: list[dict], picks: dict, slug: str) -> dict:
    """rank-1 on the positives, negatives reported apart, excluded runs out of both.

    Folding a negative that wrongly fired into the rate would hide trigger theft
    behind a good-looking number; counting a transport failure as a miss would let a
    flaky network lower a floor that only ever rises."""
    pos = [c for c in cases if c.get("should_trigger") is True]
    neg = [c for c in cases if c.get("should_trigger") is False]
    scored = [c for c in pos if picks.get(c["id"]) != EXCLUDED]
    hits = [c for c in scored if picks.get(c["id"]) == slug]
    return {
        "rank1": len(hits) / len(scored) if scored else None,
        "positives": len(scored),
        "hits": len(hits),
        "negatives": len(neg),
        "negatives_fired": sum(1 for c in neg if picks.get(c["id"]) == slug),
        "excluded": sum(1 for c in cases if picks.get(c["id"]) == EXCLUDED),
        "missed": [c["id"] for c in scored if c not in hits],
    }


def measure(cases: list[dict], catalog: dict[str, str], runner) -> tuple[dict, dict]:
    """One call per case, first turn only. `runner` is injected so the aggregation
    above is testable without a key, a network or a dollar."""
    picks, cost = {}, {"input_tokens": 0, "output_tokens": 0, "wall_ms": 0}
    for case in cases:
        answer, usage = runner(render(catalog, case["prompt"]))
        picks[case["id"]] = EXCLUDED if answer is None else pick(answer, catalog)
        for key in cost:
            cost[key] += int(usage.get(key, 0))
    return picks, cost


def cli_cmd(model: str, prompt: str) -> list[str]:
    """`claude -p` with skills, hooks and tools off and the router system prompt in
    place: the model ranks the catalogue we pass, not the one the harness would
    inject behind our back, and it answers as a router rather than as the agent."""
    return ["claude", "-p", "--model", model, "--safe-mode", "--tools", "",
            "--system-prompt", SYSTEM, "--output-format", "json", prompt]


def cli_runner(model: str):
    def run(prompt: str) -> tuple[str | None, dict]:
        started = time.monotonic()
        proc = subprocess.run(cli_cmd(model, prompt), capture_output=True,
                              text=True, timeout=300)
        return _parse_cli(proc, int((time.monotonic() - started) * 1000))
    return run


def _parse_cli(proc, wall_ms: int) -> tuple[str | None, dict]:
    """A non-answer is (None, cost) — excluded as unmeasured, never a silent miss.
    A cache read is billed input: leaving it out under-reports the receipt tenfold."""
    cost = {"input_tokens": 0, "output_tokens": 0, "wall_ms": wall_ms}
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, cost
    usage = out.get("usage") or {}
    cost["input_tokens"] = sum(int(usage.get(f, 0)) for f in INPUT_FIELDS)
    cost["output_tokens"] = int(usage.get("output_tokens", 0))
    if proc.returncode or out.get("is_error") or out.get("subtype") != "success":
        return None, cost
    return out.get("result"), cost


def _report(args, cases: list[dict], catalog: dict[str, str]) -> int:
    started = time.monotonic()
    picks, cost = measure(cases, catalog, cli_runner(args.model))
    result = tally(cases, picks, args.slug)
    result |= {"skill": args.slug, "model": args.model, "measured_on": str(args.queries),
               "catalog_size": len(catalog), "wall_ms": int((time.monotonic() - started) * 1000),
               "input_tokens": cost["input_tokens"], "output_tokens": cost["output_tokens"],
               "picks": picks}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["rank1"] is not None else 1


def selfcheck() -> int:
    cat = {"review": "read the diff", "ship": "release it"}
    assert "review" in render(cat, "q") and "q" in render(cat, "q")
    assert pick("`review`.", cat) == "review" and pick("NONE", cat) is None
    assert pick("review or ship", cat) is None, "two slugs named is no pick"
    assert pick("reviewer", cat) is None, "a slug inside a longer word is not a slug"
    cases = [{"id": "p1", "should_trigger": True, "prompt": "a"},
             {"id": "p2", "should_trigger": True, "prompt": "b"},
             {"id": "n1", "should_trigger": False, "prompt": "c"}]
    t = tally(cases, {"p1": "review", "p2": EXCLUDED, "n1": "review"}, "review")
    assert t["rank1"] == 1.0 and t["positives"] == 1 and t["excluded"] == 1, t
    assert t["negatives_fired"] == 1, "a negative that fires stays visible"
    assert tally(cases, {c["id"]: EXCLUDED for c in cases}, "review")["rank1"] is None
    picks, cost = measure(cases, cat, lambda _: ("ship", {"input_tokens": 3, "wall_ms": 1}))
    assert picks["p1"] == "ship" and cost["input_tokens"] == 9, (picks, cost)
    picks, _ = measure(cases[:1], cat, lambda _: (None, {}))
    assert picks["p1"] == EXCLUDED, "a transport failure is excluded, not a miss"
    print("SELFCHECK OK — 5 gruppi: render, pick (slug/NONE/ambiguo/sottostringa), "
          "tally (rate, esclusi, negativi, tutto escluso), measure, fallimento trasporto")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", type=Path)
    p.add_argument("--queries", type=Path)
    p.add_argument("--slug")
    p.add_argument("--model", default="claude-haiku-4-5-20251001")
    p.add_argument("--build-catalog", nargs="+", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--selfcheck", action="store_true")
    a = p.parse_args()
    if a.selfcheck:
        return selfcheck()
    if a.build_catalog:
        if not a.out:
            p.error("--build-catalog serve con --out CAT.json")
        catalog = build_catalog(a.build_catalog)
        a.out.write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n")
        print(f"catalogo: {len(catalog)} skill -> {a.out}")
        return 0
    if not (a.catalog and a.queries and a.slug):
        p.error("servono --catalog --queries --slug (o --build-catalog / --selfcheck)")
    cases, _, err = load_eval_cases(a.queries)
    if err:
        print(f"rifiutato: {err}")
        return 2
    return _report(a, cases, json.loads(a.catalog.read_text()))


if __name__ == "__main__":
    sys.exit(main())
