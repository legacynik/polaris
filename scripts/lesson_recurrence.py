#!/usr/bin/env python3
"""lesson_recurrence.py — recurrence detector for the Layer-3 lessons ledger.

Reads `_polaris/lessons.md` by parsing its `## ` blocks. The ledger grew four
metadata shapes over time; the parser used to know one of them and dropped the
other three in silence (74 of 125 blocks seen on 2026-09-01). A biased sample of
past mistakes is worse than no sample, so every block is now either parsed or
NAMED with its line number.

Recognised shapes:
  list     `- rule:` / `- tier:` / `- recurrence:` / `- last_triggered:`
  inline   `recurrence: N · tier: X · DATE`      (entries from 2026-08-28 on)
  bold     `- **recurrence:** N · **tier:** X · **origine:** …`
  enforce  `- **Enforcement:** X · recurrence: N · owner: @…`

Modes:
  --coverage                census of the ledger: seen / parsed / skipped, with
                            every skipped block listed by line number.
  --match "<signal text>"   lexical-overlap match (terms >2 chars) against each
                            lesson's rule; prints tier + recurrence. The coverage
                            line goes to stderr so `distill_enqueue.sh` keeps
                            seeing "No matching…" as the first stdout line.
  --bump  "<lesson title>"  increments recurrence in place and prints the
                            proposed promotion. Fails loud (exit 1, no write) if
                            the block's shape cannot be rewritten.
  --ledger PATH             operate on a fixture instead of the live ledger.

Stdlib only. Promotion is propose-only — it prints, the human applies at /end.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "lessons.md"
TIERS = ["note", "context", "gate"]
_STOP = {"the", "and", "for", "any", "all", "you", "your", "not", "but"}
NO_META = "no recurrence/tier metadata"

# Metadata shapes other than the original `- tier:` / `- recurrence:` list form.
# A fifth shape would have to be added in three coupled places: here (or the
# `list` special case in _meta), _BUMP_SUBS, and the _selfcheck fixture set.
_META_PATTERNS = (
    ("inline", r"(?m)^recurrence:\s*(?P<rec>\d+)\s*·\s*tier:\s*(?P<tier>\w+)"),
    ("bold", r"(?m)^- \*\*recurrence:\*\*\s*(?P<rec>\d+)\s*·\s*\*\*tier:\*\*\s*(?P<tier>\w+)"),
    ("enforce", r"(?m)^- \*\*Enforcement:\*\*\s*(?P<tier>\w+)\s*·\s*recurrence:\s*(?P<rec>\d+)"),
)
# The rule statement, whichever label the entry used. Stops at the next field.
_RULE_RE = re.compile(
    r"(?ms)^(?:- )?(?:rule:|\*\*(?:Rule|La regola):\*\*)\s*(.+?)(?=\n- |\n\*\*|\n\n|\Z)"
)
# Metadata/provenance lines, stripped when a block carries no explicit rule label.
_META_LINE = re.compile(
    r"(?mi)^(?:- )?(?:\*\*)?(?:recurrence|tier|enforcement|source|origine|last_triggered)\b.*$"
)
# form -> (pattern matching the recurrence counter, replacement template with {n})
_BUMP_SUBS = {
    "list": (r"(?m)^- recurrence:\s*\d+", "- recurrence: {n}"),
    "inline": (r"(?m)^recurrence:\s*\d+", "recurrence: {n}"),
    "bold": (r"(?m)^- \*\*recurrence:\*\*\s*\d+", "- **recurrence:** {n}"),
    "enforce": (r"(?m)^(- \*\*Enforcement:\*\*.*?recurrence:\s*)\d+", r"\g<1>{n}"),
}


def _terms(text: str) -> set[str]:
    """Lowercased word terms >2 chars, minus trivial stopwords."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


def _split_blocks(raw: str) -> list[dict]:
    """Every `## ` block with its 1-based heading line number and full text."""
    lines = raw.split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    return [
        {"line": s + 1, "title": lines[s][3:].strip(), "text": "\n".join(lines[s:e])}
        for s, e in zip(starts, starts[1:] + [len(lines)])
    ]


def _meta(text: str) -> tuple[str, str, int]:
    """(form, tier, recurrence) for the first metadata shape that matches."""
    rec = re.search(r"(?m)^- recurrence:\s*(\d+)", text)
    tier = re.search(r"(?m)^- tier:\s*(\w+)", text)
    if rec and tier:
        return "list", tier.group(1), int(rec.group(1))
    for form, pattern in _META_PATTERNS:
        m = re.search(pattern, text)
        if m:
            return form, m.group("tier"), int(m.group("rec"))
    return "", "", 0


def _rule_text(text: str) -> str:
    """The rule statement; falls back to the body minus its metadata lines."""
    body = "\n".join(text.split("\n")[1:])
    m = _RULE_RE.search(body)
    return " ".join((m.group(1) if m else _META_LINE.sub("", body)).split())


def parse_ledger(raw: str) -> tuple[list[dict], list[dict]]:
    """(lessons, skipped). A block is never dropped in silence: it is named."""
    lessons: list[dict] = []
    skipped: list[dict] = []
    for block in _split_blocks(raw):
        form, tier, rec = _meta(block["text"])
        if not form:
            skipped.append({"line": block["line"], "title": block["title"],
                            "reason": NO_META})
            continue
        lessons.append({**block, "form": form, "tier": tier, "recurrence": rec,
                        "rule": _rule_text(block["text"])})
    return lessons, skipped


def coverage(raw: str) -> dict:
    """Census of the ledger. parsed + skipped == seen, by construction."""
    lessons, skipped = parse_ledger(raw)
    return {"seen": len(lessons) + len(skipped), "parsed": len(lessons),
            "skipped": len(skipped), "skipped_blocks": skipped, "lessons": lessons}


def _next_tier(tier: str) -> str:
    i = TIERS.index(tier) if tier in TIERS else 0
    return TIERS[min(i + 1, len(TIERS) - 1)]


def _coverage_line(cov: dict) -> str:
    return (f"coverage: {cov['parsed']} of {cov['seen']} blocks parsed, "
            f"skipped: {cov['skipped']}")


def _report_coverage(path: Path) -> int:
    """Print the census; every unparsed block is named by line number."""
    cov = coverage(path.read_text(encoding="utf-8"))
    print(_coverage_line(cov))
    for entry in cov["skipped_blocks"]:
        print(f"  line {entry['line']}: {entry['reason']} — {entry['title']}")
    return 0


def _match(signal: str, path: Path) -> int:
    sig = _terms(signal)
    cov = coverage(path.read_text(encoding="utf-8"))
    print(_coverage_line(cov), file=sys.stderr)
    hits = [(le, len(sig & _terms(le["rule"]))) for le in cov["lessons"]]
    hits = sorted([h for h in hits if h[1] > 0], key=lambda h: -h[1])
    if not hits:
        print(f"No matching lesson for: {signal!r}")
        return 0
    for le, overlap in hits:
        print(f"[{le['tier']}] recurrence={le['recurrence']} "
              f"(overlap={overlap}) — {le['title']}")
    return 0


def _rewrite_block(text: str, lesson: dict, today: str) -> str:
    """The block with its recurrence bumped, or '' when the shape resists."""
    pattern, template = _BUMP_SUBS[lesson["form"]]
    out, n = re.subn(pattern, template.replace("{n}", str(lesson["recurrence"] + 1)),
                     text, count=1)
    if not n:
        return ""
    if lesson["form"] == "list":
        out = re.sub(r"(?m)^- last_triggered:.*$", f"- last_triggered: {today}",
                     out, count=1)
    return out


def _bump(title: str, path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    lessons, skipped = parse_ledger(raw)
    lesson = next((le for le in lessons if le["title"] == title), None)
    if lesson is None:
        bad = next((s for s in skipped if s["title"] == title), None)
        why = f"unparseable block at line {bad['line']} ({bad['reason']})" if bad \
            else "no lesson with that title"
        print(f"Cannot bump {title!r} — {why}", file=sys.stderr)
        return 1
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new = _rewrite_block(lesson["text"], lesson, today)
    if not new:
        print(f"Cannot bump {title!r} — {lesson['form']} block at line "
              f"{lesson['line']} has no writable counter", file=sys.stderr)
        return 1
    lines = raw.split("\n")
    start = lesson["line"] - 1
    lines[start:start + len(lesson["text"].split("\n"))] = new.split("\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    _propose(lesson, lesson["recurrence"] + 1)
    return 0


def _propose(lesson: dict, new_rec: int) -> None:
    print(f"Bumped {lesson['title']!r}: recurrence {lesson['recurrence']} -> {new_rec}")
    if new_rec >= 1 and lesson["tier"] != "gate":
        nxt = _next_tier(lesson["tier"])
        print(f"PROMOTION PROPOSED: {lesson['tier']} -> {nxt} "
              f"(recurrence>=1 → current tier too weak)")
    elif lesson["tier"] == "gate":
        print("Already at GATE — if it still recurs, the gate is bypassable. Fix the gate.")


def _selfcheck_refusal(block: str, title: str) -> None:
    """A block the parser cannot read must refuse the bump AND leave the file alone."""
    ledger = Path(tempfile.mkdtemp(prefix="lessons-selfcheck-")) / "lessons.md"
    ledger.write_text(block, encoding="utf-8")
    assert _bump(title, ledger) == 1, "unparseable block must refuse the bump"
    assert ledger.read_text(encoding="utf-8") == block, "a refused bump must not write"


def _selfcheck() -> int:
    """Exercise every parse branch, the census arithmetic and the bump refusal."""
    forms = {
        "list": "## L\n\n- rule: keep fixtures out of live state.\n- tier: gate\n"
                "- recurrence: 3\n- last_triggered: 2026-07-19\n",
        "inline": "## I\n\nrecurrence: 2 · tier: context · 2026-08-31\n\nVerify the claim.\n",
        "bold": "## B\n\n- **recurrence:** 4 · **tier:** gate · **origine:** x\n"
                "- **La regola:** prove the test is collected.\n",
        "enforce": "## E\n\n- **Rule:** print the finding.\n"
                   "- **Enforcement:** note · recurrence: 1 · owner: @x\n",
    }
    expect = {"list": ("gate", 3), "inline": ("context", 2),
              "bold": ("gate", 4), "enforce": ("note", 1)}
    for form, text in forms.items():
        (le,), skipped = parse_ledger(text)
        assert not skipped, f"{form} skipped"
        assert le["form"] == form, (form, le["form"])
        assert (le["tier"], le["recurrence"]) == expect[form], (form, le)
        assert le["rule"], f"{form} lost its rule text"
        assert _rewrite_block(le["text"], le, "2026-01-01"), f"{form} not writable"
    broken = "## ` block is one lesson, orphaned prose.\n"
    cov = coverage("".join(forms.values()) + broken)
    assert cov["seen"] == 5 and cov["parsed"] == 4 and cov["skipped"] == 1, cov
    assert cov["parsed"] + cov["skipped"] == cov["seen"], cov
    assert cov["skipped_blocks"][0]["reason"] == NO_META, cov
    assert cov["skipped_blocks"][0]["line"] > 0, cov
    _selfcheck_refusal(broken, "` block is one lesson, orphaned prose.")
    empty = coverage("")
    assert (empty["seen"], empty["parsed"], empty["skipped"]) == (0, 0, 0), empty
    print(f"selfcheck OK — 4 forms parsed, 1 named skip, {_coverage_line(cov)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lessons ledger recurrence detector.")
    ap.add_argument("--ledger", metavar="PATH", help="operate on a fixture ledger")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--match", metavar="SIGNAL")
    g.add_argument("--bump", metavar="TITLE")
    g.add_argument("--coverage", action="store_true")
    g.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return _selfcheck()
    path = Path(args.ledger) if args.ledger else LEDGER
    if not path.exists():
        print(f"Ledger not found: {path}", file=sys.stderr)
        return 1
    if args.coverage:
        return _report_coverage(path)
    return _match(args.match, path) if args.match is not None else _bump(args.bump, path)


if __name__ == "__main__":
    sys.exit(main())
