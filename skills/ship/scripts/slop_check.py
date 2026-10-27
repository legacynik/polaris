#!/usr/bin/env python3
"""Flag slop in Markdown that people read: empty buzzwords, hedges, adjective triads, sentences
over 40 words, empty headings, a first sentence that restates its heading, and
"This document describes..." openers.

Usage: slop_check.py <file.md>... [--json]   |   slop_check.py --selfcheck
Exit: 0 clean · 1 findings · 2 usage or unreadable file.

Skipped: frontmatter, fenced code, inline code, URLs and link targets, HTML comments, quotes.
A deliberate exception: `<!-- slop-ok: reason -->` on the line; without a reason it is a finding.
Rules favour precision: extend the word lists below, keep each entry unambiguous.
Stdlib only, Python >= 3.9.
"""
import json
import re
import sys

# Words that add nothing a reader can check. A regex per entry, matched case-insensitively.
BUZZWORDS = [
    r"comprehensive", r"(?:highly|more|very|truly) robust", r"robust and \w+", r"seamless(?:ly)?", r"cutting[- ]edge", r"state[- ]of[- ]the[- ]art",
    r"game[- ]chang(?:er|ing)", r"delv(?:e|es|ing)", r"it'?s worth noting", r"it is worth noting",
    r"in today'?s (?:fast[- ]paced|digital|modern)", r"leverag(?:es|ed|ing)",
    r"leverage (?:the|a|an|our|your|its|their|this|these|existing)",
    r"unlock(?:s|ing)? (?:the |your |new |its )?(?:full )?(?:potential|value|power|insights?|growth|possibilities)",
    r"elevat(?:e|es|ing) (?:the |your )?(?:experience|game|workflow|productivity)",
    r"best[- ]in[- ]class", r"world[- ]class", r"revolutioni[sz](?:e|es|ing)", r"supercharg(?:e|es|ing)",
    r"harness(?:es|ing)? the power", r"empower(?:s|ing)?", r"synerg(?:y|ies)", r"paradigm shift",
    r"powerful", r"holistic", r"next[- ]generation", r"a testament to", r"plays? a (?:crucial|pivotal|vital) role",
    r"(?:rich|vibrant) tapestry", r"navigat(?:e|ing) the (?:complexities|landscape)",
]
# Hedges standing in for a fact.
HEDGES = [
    r"might potentially", r"could potentially", r"may potentially", r"could possibly", r"might possibly",
    r"may possibly", r"it seems that", r"it appears that", r"arguably", r"to some extent",
]
# Adjectives that marketing stacks in threes.
ADJ = set("""fast quick reliable scalable secure flexible intuitive lightweight extensible robust simple
powerful efficient elegant modern seamless performant maintainable modular stable clean easy
affordable accessible innovative dynamic agile resilient versatile user-friendly cost-effective
lean smart beautiful responsive consistent transparent safe accurate""".split())
OPENER = re.compile(
    r"^(?:(?:this|the) (?:document|doc|section|page|guide|file|readme|chapter|note)"
    r"(?: \w+)? (?:describes|explains|covers|outlines|presents|details|introduces|documents)\b"
    r"|the (?:purpose|goal|aim) of this (?:document|doc|section|page|guide|file|readme)\b"
    r"|in this (?:document|doc|section|page|guide|readme),? (?:we|you)\b)", re.I)
STOP = set("""a an the this that these those is are was were be been it its of to in on for and or
with by as at from here there we you our your about overview section""".split())
MAX_WORDS = 40

# Not inside an identifier such as holistic-local-gate.
BUZZ_RE = re.compile(r"(?<![\w-])(?:" + "|".join(BUZZWORDS) + r")(?![\w-])", re.I)
HEDGE_RE = re.compile(r"\b(?:" + "|".join(HEDGES) + r")\b", re.I)
TRIAD_RE = re.compile(r"\b([\w-]+), ([\w-]+),? (?:and|or) ([\w-]+)\b", re.I)
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
ALLOW_RE = re.compile(r"<!--\s*slop-ok\b:?\s*(.*?)\s*-->", re.I)
SENT_END = re.compile(r"[.!?][*_)\]»\"'’]*(?=\s|$)")


def _mask(s):
    """Blank out spans that are not prose, keeping column positions."""
    blank = lambda m: " " * len(m.group(0))
    s = re.sub(r"<!--.*?-->", blank, s)
    s = re.sub(r"(`+).*?\1", blank, s)
    s = re.sub(r"\]\([^)]*\)", lambda m: "]" + " " * (len(m.group(0)) - 1), s)
    s = re.sub(r"<?(?:https?://|www\.)\S+>?", blank, s)
    s = re.sub(r'"[^"]*"|“[^”]*”|«[^»]*»', blank, s)  # quoted words are someone else's
    return s


def classify(raw):
    """Per line: (kind, prose). kind in fm, code, blank, heading, table, item, text."""
    out, i, n = [], 0, len(raw)
    if raw and raw[0].strip() == "---":
        for j in range(1, n):
            if raw[j].strip() in ("---", "..."):
                out = [("fm", "")] * (j + 1)
                i = j + 1
                break
    fence = None
    for line in raw[i:]:
        m = FENCE_RE.match(line)
        if fence:
            out.append(("code", ""))
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip()[len(m.group(1)):].strip():
                fence = None
            continue
        if m:
            fence = m.group(1)
            out.append(("code", ""))
            continue
        prose = _mask(line)
        if not line.strip():
            out.append(("blank", ""))
        elif HEADING_RE.match(line):
            out.append(("heading", prose))
        elif line.lstrip().startswith("|"):
            out.append(("table", prose))
        elif ITEM_RE.match(line):
            out.append(("item", prose))
        elif line.startswith("    ") and out and out[-1][0] in ("blank", "code") and \
                not any(k in ("item",) for k, _ in out[-3:]):
            out.append(("code", ""))  # indented code block
        elif not prose.strip() or prose.lstrip().startswith("<"):
            out.append(("html", ""))
        else:
            out.append(("text", prose))
    return out


def units(kinds):
    """Prose units: (start_line_index, [(line_index, text)]). Items and table rows stand alone."""
    res, cur = [], None
    for i, (k, p) in enumerate(kinds):
        if k in ("text", "item"):
            if k == "item" or cur is None:
                cur = [(i, ITEM_RE.sub(lambda m: " " * len(m.group(0)), p) if k == "item" else p)]
                res.append(cur)
            else:
                cur.append((i, p))
        else:
            cur = None
            if k == "table":
                res.append([(i, p)])
    return res


def sentences(unit):
    """Yield (line_index, sentence) per sentence; the line is where the sentence starts."""
    buf, start = "", None
    for i, text in unit:
        pos = 0
        for m in SENT_END.finditer(text):
            piece = text[pos:m.end()]
            if start is None and piece.strip():
                start = i
            buf += " " + piece
            if start is not None:
                yield start, buf.strip()
            buf, start, pos = "", None, m.end()
        rest = text[pos:]
        if start is None and rest.strip():
            start = i
        buf += " " + rest
    if buf.strip() and start is not None:
        yield start, buf.strip()


def heading(line):
    """(level, text) of a heading line; (0, "") when the line is not one."""
    m = HEADING_RE.match(line)
    return (len(m.group(1)), m.group(2)) if m else (0, "")


def words(s):
    return [w for w in re.findall(r"[A-Za-z0-9][\w'-]*", s)]


def content(s):
    return {w.lower().rstrip("s") for w in words(s) if w.lower() not in STOP}


def is_adj(w):
    return w.lower() in ADJ


def check_text(text):
    raw = text.splitlines()
    kinds = classify(raw)
    found = []  # (line_index, rule, reason)

    for i, (k, p) in enumerate(kinds):
        if k not in ("text", "item", "table", "heading"):
            continue
        for m in BUZZ_RE.finditer(p):
            found.append((i, "buzzword", f'"{m.group(0)}" says nothing checkable: name the fact'))
        for m in HEDGE_RE.finditer(p):
            found.append((i, "hedge", f'"{m.group(0)}" stands in for a fact: state it or say unknown'))
        for m in TRIAD_RE.finditer(p):
            ws = m.groups()
            if sum(map(is_adj, ws)) >= 2 and all(is_adj(w) or w.lower().endswith(("able", "ive", "ient")) for w in ws):
                found.append((i, "triad", f'"{m.group(0)}": three adjectives, no evidence'))

    for unit in units(kinds):
        for start, s in sentences(unit):
            n = len(words(s))
            if n > MAX_WORDS and kinds[start][0] != "table":
                found.append((start, "long-sentence", f"{n} words (max {MAX_WORDS}): split it"))
        first = unit[0][1].strip()
        if OPENER.match(first):
            found.append((unit[0][0], "opener", "opens by announcing itself: lead with the content"))

    for i, (k, _) in enumerate(kinds):
        if k != "heading":
            continue
        level, title = heading(raw[i])
        if ": " in title or "](" in title:
            continue  # the heading carries its own content: "Verdict: RED", a link
        j = i + 1
        while j < len(kinds) and kinds[j][0] == "blank":
            j += 1
        if j == len(kinds) or (kinds[j][0] == "heading" and heading(raw[j])[0] <= level):
            found.append((i, "empty-heading", "heading with nothing under it"))
            continue
        if kinds[j][0] == "text":
            unit = next(u for u in units(kinds) if u[0][0] == j)
            first = next(sentences(unit), (j, ""))[1]
            sw, hw = content(first), content(heading(raw[i])[1])
            label = re.fullmatch(r"([*_]{1,2}).+\1", first)  # a run-in bold label, not prose
            if len(sw) >= 3 and sw <= hw and not label:  # fewer words: usually code was masked
                found.append((j, "restates-heading", "first sentence only repeats the heading"))

    # Allow comments: a reason silences the line; no reason is itself a finding.
    allowed = set()
    for i, line in enumerate(raw):
        m = ALLOW_RE.search(line)
        if m and kinds[i][0] not in ("code", "fm"):
            if m.group(1).strip():
                allowed.add(i)
            else:
                found.append((i, "slop-ok", "slop-ok needs a reason: <!-- slop-ok: why -->"))
    return sorted({(i + 1, r, why) for i, r, why in found if i not in allowed or r == "slop-ok"})


SAMPLES = {
    "buzzword": "# Cache\n\nA seamless cache.\n",
    "hedge": "# Cache\n\nIt might potentially fail.\n",
    "triad": "# Cache\n\nIt is fast, reliable, and scalable.\n",
    "long-sentence": "# Cache\n\n" + " ".join(["word"] * 45) + ".\n",
    "empty-heading": "# Cache\n\n## Size\n\n## Age\n\nIt holds 512 entries.\n",
    "restates-heading": "# Cache eviction policy\n\nThis is the cache eviction policy.\n",
    "opener": "# Cache\n\nThis document describes the cache.\n",
    "slop-ok": "# Cache\n\nA robust cache. <!-- slop-ok -->\n",
}
CLEAN = ("---\ntitle: robust\n---\n# Cache\n\nThe cache holds 512 entries. <!-- x -->\n"
         "Call `robust()` or see https://x.io/robust.\n\n```\nseamless, robust, powerful\n```\n"
         "\nA robust cache. <!-- slop-ok: quoted claim -->\n\n- red, green, and blue\n")


def selfcheck():
    for rule, text in SAMPLES.items():
        rules = {r for _, r, _ in check_text(text)}
        assert rule in rules, f"{rule} not raised: {rules}"
    assert check_text(CLEAN) == [], check_text(CLEAN)
    print("selfcheck OK")
    return 0


def main(argv):
    if argv == ["--selfcheck"]:
        return selfcheck()
    as_json = "--json" in argv
    files = [a for a in argv if a != "--json"]
    if not files or any(f.startswith("-") for f in files):
        print("usage: slop_check.py <file.md>... [--json] | --selfcheck", file=sys.stderr)
        return 2
    report = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"slop_check: cannot read {f}: {e}", file=sys.stderr)
            return 2
        report += [{"file": f, "line": ln, "rule": r, "reason": why} for ln, r, why in check_text(text)]
    if as_json:
        print(json.dumps(report, indent=1))
    else:
        for x in report:
            print(f"{x['file']}:{x['line']}: {x['rule']}: {x['reason']}")
        if report:
            print(f"{len(report)} finding(s)")
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
