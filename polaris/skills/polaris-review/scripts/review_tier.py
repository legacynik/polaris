#!/usr/bin/env python3
"""review_tier — how strong a reviewer this diff needs, decided from the diff, not from mood.

    review_tier.py [--base REF | --staged] [--cwd DIR] [--config _polaris/config.yml]
    review_tier.py --selfcheck

Prints one `TIER n — ...` line, the reason, the diff size and whether the Codex CLI is on PATH.

  tier 3  any changed path matches a risk class (auth/permissions, money/pricing, data/schema/
          migrations, security, concurrency, or the repository's own `review.risk_paths` regex),
          or the diff is very large (> LARGE_LINES lines or > LARGE_FILES files)
  tier 1  no risk path, at most SMALL_FILES files and SMALL_LINES changed lines
  tier 2  everything else

The rule reads paths and counts only, never content: a risky change in a file whose path says
nothing (a pricing rule inside `utils.py`) is tier 2 unless the repository names that path in
`review.risk_paths` of its `_polaris/config.yml`.
Exit 0 with a tier · 2 unusable input (not a repository, unknown base). Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

SMALL_LINES, SMALL_FILES = 40, 3
LARGE_LINES, LARGE_FILES = 800, 25
# Path words per risk class; a path is risky when one of its words (split on anything that is not
# a letter or digit, camelCase split too, a trailing s/es ignored) is in a list, or it ends in .sql.
# ponytail: a word list misses synonyms; the repository's `review.risk_paths` regex covers its own.
RISK = {
    "auth/permissions": "auth authn authz authentication authorization login logout session "
                        "permission rbac acl oauth jwt password credential role sso",
    "money/pricing": "pay payment billing price pricing invoice charge refund wallet money "
                     "checkout subscription stripe quote quotation tax discount ledger",
    "data/schema": "migration migrate schema alembic prisma ddl seed model database db",
    "security": "security crypto secret sanitize sanitizer csrf cors encrypt encryption "
                "signature webhook",
    "concurrency": "lock mutex semaphore queue worker concurrency thread scheduler cron async",
}
TIERS = {1: "light reviewer (fast model)", 2: "strong reviewer (strong model)",
         3: "strong reviewer plus an independent cross-model pass"}


def config_risk(path: Path) -> str:
    """`review.risk_paths` (one regex) from the product config. Line-based: one flat key."""
    inside = False
    if not path.is_file():
        return ""
    for line in path.read_text(errors="replace").splitlines():
        if re.match(r"^\S", line):
            inside = line.split("#")[0].strip() == "review:"
            continue
        m = re.match(r"^\s+risk_paths:\s*(.*)$", line) if inside else None
        if m:
            return re.sub(r"\s+#.*$", "", m.group(1)).strip().strip("\"'")
    return ""


def numstat(cwd: Path, base: str, staged: bool) -> list[tuple[str, int]]:
    args = ["diff", "--numstat", "--staged"] if staged else ["diff", "--numstat", f"{base}...HEAD"]
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if done.returncode:
        raise ValueError(done.stderr.strip() or "git diff failed")
    out = []
    for line in done.stdout.splitlines():
        added, deleted, name = line.split("\t", 2)
        # binary files print "-": count them as one line so they still count as a change
        out.append((name, (int(added) if added.isdigit() else 1) + (int(deleted) if deleted.isdigit() else 0)))
    return out


def words(path: str) -> set[str]:
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", path)
    out = set()
    for w in re.split(r"[^a-z0-9]+", split.lower()):
        out |= {w, w[:-1] if w.endswith("s") else w, w[:-2] if w.endswith("es") else w}
    return out - {""}


def decide(files: list[tuple[str, int]], extra_risk: str = "") -> tuple[int, str]:
    for name, _ in files:
        if extra_risk and re.search(extra_risk, name):
            return 3, f"risk path {name} (repository risk path)"
        if name.lower().endswith(".sql"):
            return 3, f"risk path {name} (data/schema)"
        for label, vocabulary in RISK.items():
            if words(name) & set(vocabulary.split()):
                return 3, f"risk path {name} ({label})"
    lines = sum(n for _, n in files)
    if lines > LARGE_LINES or len(files) > LARGE_FILES:
        return 3, f"large diff ({len(files)} files, {lines} lines)"
    if len(files) <= SMALL_FILES and lines <= SMALL_LINES:
        return 1, f"small diff, no risk path ({len(files)} files, {lines} lines)"
    return 2, f"normal diff, no risk path ({len(files)} files, {lines} lines)"


def selfcheck() -> int:
    assert decide([("docs/a.md", 10)])[0] == 1
    assert decide([("app/a.py", 200)])[0] == 2
    assert decide([("app/billing/x.py", 1)]) == (3, "risk path app/billing/x.py (money/pricing)")
    assert decide([("db/migrations/1.sql", 1)])[0] == 3
    assert decide([(f"m{i}.py", 1) for i in range(26)])[0] == 3
    assert decide([("infra/main.tf", 1)], "^infra/")[0] == 3
    assert decide([("app/oracle.py", 1), ("app/payload.py", 1), ("app/syntax.py", 1)])[0] == 1, \
        "substrings are not words: oracle is not acl, payload is not pay"
    assert decide([("src/userSession.ts", 1)])[0] == 3, "camelCase splits"
    print("SELFCHECK OK — small, normal, risk path, migration, large, repository risk path")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--cwd", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    try:
        files = numstat(args.cwd, args.base, args.staged)
    except ValueError as exc:
        print(f"unusable input: {exc} — no tier without a diff", file=sys.stderr)
        return 2
    tier, reason = decide(files, config_risk(args.config or args.cwd / "_polaris" / "config.yml"))
    print(f"TIER {tier} — {TIERS[tier]}")
    print(f"reason: {reason}")
    print(f"codex: {'available' if shutil.which('codex') else 'missing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
