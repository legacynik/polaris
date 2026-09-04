"""apex_gate CLI — git integration for the deterministic apex gate.

Modes: --staged (pre-commit hook) · --base <ref> (CI) · --file X --against Y
(proposal check for pol-apex-curate).
Exit codes: 0 OK/WARN-only, 1 BLOCK (and no FORCE), 2 gate error — git state
could not be compared (unresolvable ref, git show hard failure) — fail closed.
Stdlib-only, vendorable. Checks live in apex_gate.py (pure).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import apex_gate as ag


class GateError(RuntimeError):
    """Raised when git state cannot be compared — caller must fail closed."""


_ABSENT_PATTERNS = re.compile(
    r"does not exist|exists on disk, but not in|bad revision|unknown revision"
    r"|invalid object name|path .* does not exist|fatal: path",
    re.IGNORECASE,
)

# Pin git's own output to English/C so _ABSENT_PATTERNS (and any other
# stderr matching) doesn't silently misfire under a localized LANG/LC_ALL.
_GIT_ENV = {**os.environ, "LC_ALL": "C", "LANG": "C"}


def _git_show(spec: str) -> str:
    r = subprocess.run(["git", "show", spec], capture_output=True,
                        encoding="utf-8", errors="replace", env=_GIT_ENV)
    if r.returncode == 0:
        return r.stdout
    if _ABSENT_PATTERNS.search(r.stderr or ""):
        return ""
    first_line = (r.stderr or "").splitlines()[0] if r.stderr else "unknown error"
    raise GateError(f"git show failed: {first_line}")


def _staged_paths() -> list[str]:
    r = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--cached",
                        "--no-renames", "--name-only"], capture_output=True,
                        encoding="utf-8", errors="replace", env=_GIT_ENV)
    if r.returncode != 0:
        first_line = (r.stderr or "unknown error").splitlines()[0]
        raise GateError(f"git diff failed: {first_line}")
    return [p for p in r.stdout.splitlines() if p.strip()]


def _verify_base_ref(base: str) -> None:
    r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                        capture_output=True, encoding="utf-8", errors="replace", env=_GIT_ENV)
    if r.returncode != 0:
        raise GateError(f"cannot resolve base ref '{base}'")


def _base_changed_paths(base: str) -> list[str]:
    _verify_base_ref(base)
    r = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--no-renames",
                        "--name-only", base], capture_output=True,
                        encoding="utf-8", errors="replace", env=_GIT_ENV)
    if r.returncode != 0:
        first_line = (r.stderr or "unknown error").splitlines()[0]
        raise GateError(f"git diff failed: {first_line}")
    return [p for p in r.stdout.splitlines() if p.strip()]


def _claude_verdicts(p, old_of, new_of):
    new = new_of(p)
    checks = (ag.check_cap(new), ag.check_locked(old_of(p), new), ag.check_structure(new))
    return [(lvl, p, msg) for lvl, msg in checks]


def gate_paths(paths, old_of, new_of) -> list[tuple[str, str, str]]:
    out = []
    for p in paths:
        if p == "CLAUDE.md":
            out.extend(_claude_verdicts(p, old_of, new_of))
        elif p.startswith(".claude/rules/") and p.endswith(".md"):
            v = ag.check_rules_paths(new_of(p))
            out.append((v[0], p, v[1]))
    return out


def _working_tree_text(p: str) -> str:
    path = Path(p)
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _verdicts(argv: list[str]) -> list[tuple[str, str, str]]:
    if "--file" in argv:
        new = Path(argv[argv.index("--file") + 1]).read_text(
            encoding="utf-8", errors="replace")
        old = Path(argv[argv.index("--against") + 1]).read_text(
            encoding="utf-8", errors="replace")
        return gate_paths(["CLAUDE.md"], lambda p: old, lambda p: new)
    if "--base" in argv:
        base = argv[argv.index("--base") + 1]
        return gate_paths(_base_changed_paths(base),
                          lambda p: _git_show(f"{base}:{p}"), _working_tree_text)
    return gate_paths(_staged_paths(),
                      lambda p: _git_show(f"HEAD:{p}"), lambda p: _git_show(f":{p}"))


def main(argv: list[str]) -> int:
    try:
        results = _verdicts(argv)
    except GateError as e:
        print(f"apex-gate: ERROR {e} — failing closed")
        return 2
    force = os.environ.get("POLARIS_APEX_FORCE") == "1"
    for level, path, msg in results:
        if level != "OK":
            print(f"apex-gate: {level} {path} — {msg}")
    blocked = any(level == "BLOCK" for level, _, _ in results)
    if blocked and force:
        print("apex-gate: FORCED past BLOCK (POLARIS_APEX_FORCE=1) — logged, deliberate act")
    return 1 if blocked and not force else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
