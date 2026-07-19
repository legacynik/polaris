"""apex_gate — deterministic checks for the always-loaded apex (CLAUDE.md).

Spec: docs/superpowers/specs/2026-07-07-polaris-lifecycle-method-design.md §2.
Pure functions only (no git, no I/O) — stdlib, vendorable like code_refs.py.
Verdict = (level, message), level in {"OK", "WARN", "BLOCK"}.
"""
from __future__ import annotations

import re

APEX_CAP = 200
LOCKED_RE = re.compile(r"<!--\s*LOCKED\s*-->")
POINTER_MAP_HEADING = "## Where to find things (map)"


def norm_rule(line: str) -> str:
    return " ".join(LOCKED_RE.sub("", line).split())


def locked_set(text: str) -> set[str]:
    return {norm_rule(ln) for ln in text.splitlines() if LOCKED_RE.search(ln)}


def check_cap(text: str) -> tuple[str, str]:
    n = len(text.splitlines())
    if n > APEX_CAP:
        return "WARN", f"over cap: {n} lines > {APEX_CAP} — run pol-apex-curate"
    return "OK", f"{n}/{APEX_CAP} lines"


def check_locked(old: str, new: str) -> tuple[str, str]:
    gone = locked_set(old) - locked_set(new)
    if gone:
        sample = "; ".join(sorted(gone)[:3])
        return "BLOCK", (f"{len(gone)} LOCKED rule(s) removed/modified: {sample} "
                         "(bypass: POLARIS_APEX_FORCE=1)")
    return "OK", "all LOCKED rules preserved"


FM_RE = re.compile(r"\A---\s*\n(.*?)^---\s*\n", re.S | re.M)


def check_structure(text: str) -> tuple[str, str]:
    if POINTER_MAP_HEADING not in text:
        return "WARN", f'pointer-map missing ("{POINTER_MAP_HEADING}")'
    return "OK", "pointer-map present"


def _is_nonempty_inline_list(inline: str) -> bool:
    if not (inline.startswith("[") and inline.endswith("]")):
        return False
    return bool(inline[1:-1].strip())


def _has_paths(frontmatter: str) -> bool:
    lines = frontmatter.splitlines()
    for i, ln in enumerate(lines):
        if not ln.startswith("paths:"):
            continue
        inline = ln.split(":", 1)[1].strip()
        if inline:
            return _is_nonempty_inline_list(inline)
        return any(nxt.strip().startswith("- ") for nxt in lines[i + 1:i + 2])
    return False


def check_rules_paths(text: str) -> tuple[str, str]:
    m = FM_RE.match(text)
    if m and _has_paths(m.group(1)):
        return "OK", "path-scoped"
    return "WARN", ("no paths: frontmatter — this rule loads EVERY session, "
                    "same priority as CLAUDE.md (F1). Add paths: globs.")
