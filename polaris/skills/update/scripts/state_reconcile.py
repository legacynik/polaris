#!/usr/bin/env python3
"""polaris-os#538 — a checkpoint removes from the cockpit what is PROVEN done, and nothing else.

`/end` closes by judgment; this runs at every checkpoint of every panel, so it is narrower on
purpose. A line leaves `## Open` or `## Active Priorities` only when ALL of this holds:

  * it is ONE top-level entry with nothing hanging under it (a child, a fenced command, a line
    of prose may carry work the head line does not cite);
  * every number it cites belongs to THIS repository (`org/repo#7` and `guide.md#7` do not) and
    `merge_truth.verdict` — the function `/end` uses — answers PROVEN;
  * that exact line, still alone, is in its section when the write happens, under the lock.

Abandoned work (DEAD), anything unreadable, anything another writer touched meanwhile: it stays
and `/end` decides. Every byte outside a removed line comes back identical; the only edit beside
the removal is the renumbering of an order that was a plain 1..n list.

    state_reconcile.py <current.md> <today's session log>      exit 0, or 3 = nothing was learned
"""
from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent.parent / "end" / "scripts")]

import merge_truth  # noqa: E402
from state_lines import BOM, THREAD, kinds, section  # noqa: E402
from state_lock import locked, still_mine, write_atomic  # noqa: E402
from state_sections import exact, heading  # noqa: E402

OPEN, ORDER = "## Open", "## Active Priorities"
SECTIONS = {OPEN: heading(OPEN), ORDER: exact(ORDER)}
# An ALLOW-list, after a deny-list of glued slugs let `org/repo PR 7`, `org/repo #7` and a markdown
# link through: past the lane's own id, a line that names any slug, URL or link is not ours to
# prove, and every `#` in it must be a bare number (`#77aa00` is a colour).
LEAD = re.compile(r"^(?:[-*+]|\d+[.)])\s+`[^`]*`")
FOREIGN = re.compile(r"[\w.-]+/[\w.-]+|://|\]\(")
BARE = re.compile(r"(?<![\w/.)\]`-])#\d+\b(?![\w-])")
NUMBERED = re.compile(r"^(\d+)([.)]\s+)")

# One tracker call per number per run: a lane and the priority that cites it ask the same thing.
merge_truth._gh = functools.lru_cache(maxsize=None)(merge_truth._gh)


def _clean(raw: list[str]) -> list[str]:
    """The lines as the classifiers want them. `raw` keeps its terminators and its BOM."""
    lines = [ln.rstrip("\r") for ln in raw]
    lines[0] = lines[0].removeprefix(BOM)
    return lines


def _lone(lines: list[str], name: str) -> list[int]:
    """The section's top-level entries whose next non-blank line is another entry, or nothing."""
    tags, span = kinds(lines), section(lines, SECTIONS[name]) or (0, 0)
    entry = [tags[i] == "thread" and bool(THREAD.match(lines[i])) for i in range(len(lines))]
    out = []
    for i in range(*span):
        after = next((j for j in range(i + 1, span[1]) if lines[j].strip()), None)
        if entry[i] and (after is None or entry[after]):
            out.append(i)
    return out


def candidates(lines: list[str]) -> list[tuple[str, str]]:
    """(section, line) for every lone entry that cites numbers, all of them this repository's."""
    out = []
    for name, i in ((name, i) for name in SECTIONS for i in _lone(lines, name)):
        rest = LEAD.sub("", lines[i], count=1)
        ours = not FOREIGN.search(rest) and len(BARE.findall(rest)) == rest.count("#")
        if ours and merge_truth.cites(lines[i]):
            out.append((name, lines[i]))
    return out


def _numbered(raw: list[str]) -> tuple[list[int], bool]:
    """Where the order's top-level numbered items are, and whether they read exactly 1..n."""
    lines = _clean(raw)
    tags, span = kinds(lines), section(lines, SECTIONS[ORDER]) or (0, 0)
    at = [i for i in range(*span) if tags[i] == "thread" and NUMBERED.match(lines[i])]
    return at, [int(NUMBERED.match(lines[i]).group(1)) for i in at] == list(range(1, len(at) + 1))


def _strike(raw: list[str], name: str, line: str) -> bool:
    """Delete `line` from its section only if it is still there, unchanged and still alone."""
    lines = _clean(raw)
    hits = [i for i in _lone(lines, name) if lines[i] == line]
    if not hits:
        return False
    del raw[hits[0]]
    return True


def _record(log: Path, removed: list[tuple[str, str, str]]) -> None:
    lead = "" if log.read_bytes().endswith(b"\n") else "\n"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(lead + "".join(f"- Reconciled out of `{name}` — PROVEN: {why} — was: {line}\n"
                                for name, line, why in removed))


def apply(path: Path, proven: list[tuple[str, str, str]], log: Path | None = None) -> list:
    """Strike the proven lines from the file AS IT IS NOW. The verdicts are a minute old: a line
    that changed or gained a child meanwhile is someone else's, and stays."""
    with locked(path):
        raw = path.read_bytes().decode("utf-8").split("\n")
        was_plain = _numbered(raw)[1]
        removed = [p for p in proven if _strike(raw, p[0], p[1])]
        if not removed:
            return []
        renumber = was_plain and any(p[0] == ORDER for p in removed)
        for n, i in enumerate(_numbered(raw)[0] if renumber else [], 1):
            raw[i] = NUMBERED.sub(lambda m, n=n: f"{n}{m.group(2)}", raw[i], count=1)
        if log:
            _record(log, removed)      # first: a failed append must leave the cockpit untouched
        still_mine(path)
        write_atomic(path, "\n".join(raw))
    return removed


def log_ready(log: Path) -> bool:
    """Today's log has a real `## ` entry, not one inside a fence. Whether it takes a line is
    proven by appending to it BEFORE the cockpit is written: a refusal there removes nothing."""
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return False
    return any(tag == "heading" and ln.startswith("## ") for tag, ln in zip(kinds(lines), lines))


def _say(seen: list[tuple], removed: list[tuple]) -> None:
    """What left, what was proven but belongs to another writer now, and one count."""
    gone = {(name, line) for name, line, _ in removed}
    for name, line, kind, _ in seen:
        if kind == "PROVEN":
            struck = (name, line) in gone   # in full: the model reads it for prose still alive
            print(f"REMOVED={name} {line}" if struck else f"CHANGED_SINCE={name} {line}"[:180])
    count = {k: sum(1 for s in seen if s[2] == k) for k in ("DEAD", "BLOCKED")}
    tail = [f"{count['DEAD']} abandoned left for /end"] * bool(count["DEAD"]) \
        + [f"{count['BLOCKED']} unreadable on the tracker"] * bool(count["BLOCKED"])
    head = f"{len(removed)} removed" if removed else "nothing removed"
    print("checkpoint: reconcile — " + ", ".join([head, *tail]))


def main(argv: list[str]) -> int:
    path, log = Path(argv[1]), Path(argv[2])
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # the report must outlive the locale
    if not log_ready(log):
        print("checkpoint: reconcile — nothing removed: today's log has no entry to carry the verdicts")
        return 3
    found = candidates(_clean(path.read_bytes().decode("utf-8").split("\n")))
    default = merge_truth.default_branch()
    seen = [(name, line, *merge_truth.verdict(line, default)) for name, line in found]
    try:
        removed = apply(path, [(n, ln, why) for n, ln, kind, why in seen if kind == "PROVEN"], log)
    except OSError as exc:      # the log refused the verdicts, or the cockpit refused the write
        print(f"checkpoint: reconcile — nothing removed: {type(exc).__name__} on {Path(exc.filename or '').name}")
        return 3
    _say(seen, removed)
    return 3 if seen and all(s[2] == "BLOCKED" for s in seen) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
