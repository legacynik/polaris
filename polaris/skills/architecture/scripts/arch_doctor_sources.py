#!/usr/bin/env python3
"""arch_doctor_sources — which checker, where it lives, and what its exit codes promise.

The running half lives in `arch_doctor.py`; this half owns the claims, so a change to how
the doctor REPORTS can never quietly change what it MEASURES. Nothing here runs a checker.

    arch_doctor_sources.py --selfcheck
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

TIMEOUT = 60
QUICK_BUDGET = 5.0  # the naked invocation's whole measure, shared across its checks
NOT_HERE = "harness not installed here"
NOT_ADOPTED = ("LIVE_DOC_MISSING", "FRONTMATTER_MISSING")
ADOPT = ("this repository has not adopted the backbone: "
         "`python3 -I scripts/check_context_backbone.py --init .` is the adoption, not `doc`")
REPAIR = ("restore the cited path, or fix the citation: "
          "`/architecture doc` (re-true the document) or `/architecture land <DEC-id>`")
STALE = ("CITED_PATH_MISSING", "COMPONENT_PATH_MISSING", "DECISION_CALL_SITE_MISSING")

# Every key but `check`/`script` is optional. `adopted_when`: the path whose absence means
# this repository never adopted the thing the checker judges — judging it then measures the
# absence of a register, not the health of one. No `args`: the checker cannot answer a
# repository-wide question. `ledger`: a recording without which its answer would be a
# fabricated zero — it is COPIED into the scratch dir, so the checker cannot write the
# original. `clean_line`: the exact line it prints when clean, anchored, because these exit 0
# either way and a substring match let a file called `cleanup.py` read as «clean».
# `red_exits`: the exit codes that mean RED. Any other code is the CHECKER failing, not a
# verdict about the repository.
CHECKS = (
    {"check": "backbone", "script": "scripts/check_context_backbone.py", "quick": True,
     "args": ("--check", "{root}"), "blocking": True, "red_exits": (2,),
     "fix": "python3 -I scripts/check_context_backbone.py --check . and read the cause"},
    {"check": "decisions", "script": "scripts/decisions_health.py", "quick": True,
     "args": ("--check", "{root}"), "blocking": True, "red_exits": (1,),
     "adopted_when": "decisions",
     "fix": "/architecture land <DEC-id> for each predicate the report names red"},
    {"check": "scope-drift", "script": "scripts/polaris_drift_check.py", "quick": True,
     "args": ("--intents", "{intents}", "--ledger", "{tmp}/scope-drift.jsonl"),
     "intents": "state/intents.json", "clean_line": r"^iCPG scope-drift: clean\b",
     "fix": "declare a plan `scope:` covering the unowned files, or record the intent"},
    {"check": "symbol-drift", "script": "scripts/polaris_symbol_drift.py",
     "ledger": "state/symbol-drift-ledger.jsonl",
     "why": "asks about named files, not about a repository — not a doctor-wide question",
     "fix": "python3 scripts/polaris_symbol_drift.py check <file>... on the files you touched"},
    {"check": "decision-drift", "script": "scripts/polaris_decision_drift.py",
     "args": ("--ledger", "{ledger}", "--scope", "{root}"),
     "ledger": "decision-drift.jsonl", "clean_line": r"^decision-drift: clean\b",
     "fix": "/architecture land <DEC-id> on each decision whose code moved"},
    {"check": "dependency-drift", "script": "scripts/polaris_dependency_drift.py",
     "args": ("--ledger", "{ledger}", "--scope", "{root}"),
     "ledger": "dependency-drift.jsonl", "clean_line": r"^dependency-drift: clean\b",
     "fix": "/architecture decide on the new coupling, or record the dependency set"},
    {"check": "test-drift", "script": "scripts/polaris_test_drift.py",
     "args": ("--ledger", "{ledger}", "--scope", "{root}"),
     "ledger": "test-drift.jsonl", "clean_line": r"^test-drift: clean\b",
     "fix": "write the test the changed symbol no longer has, through `tdd-dev`"},
    {"check": "install-hygiene", "script": "_standard/check_install_hygiene.py",
     "args": ("--lockfile", "{home}/.agents/.skill-lock.json", "--roots",
              "{home}/.claude/skills", "{home}/.agents/skills", "{home}/.codex/skills"),
     "red_exits": (1,),
     "fix": "read the fault lines; a dangling link or a lockfile ghost is an install repair"},
)


def vault(root: Path) -> Path | None:
    """`$POLARIS_VAULT` wins over the repository's declared vault; neither is invented."""
    declared = ""
    try:
        done = subprocess.run(["git", "config", "--get", "polaris.vault"], cwd=str(root),
                              capture_output=True, text=True, timeout=10)
        declared = done.stdout.strip() if done.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        pass
    for candidate in (os.environ.get("POLARIS_VAULT", ""), declared):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return None


def package_root(script: Path) -> Path | None:
    """The package root when this skill sits in the package layout `<pkg>/skills/<door>/scripts/`,
    which ships the shared checkers under `<pkg>/scripts/`; None in any other layout."""
    door_parent = script.resolve().parents[2]
    return door_parent.parent if door_parent.name == "skills" else None


def resolve(rel: str, root: Path, vault_dir: Path | None, own_first: bool = False) -> Path | None:
    """The host repository owns its checkers; then the package this skill shipped in, then the
    declared vault, then the copy this skill ships beside this file (`scripts/<name>`).
    `own_first` puts the skill's copy ahead of the others (`--which`). Nothing else is looked at,
    and nothing is invented."""
    own = Path(__file__).resolve().parents[1]
    bases = [root, package_root(Path(__file__)), vault_dir]
    bases = [own, *bases] if own_first else [*bases, own]
    for base in bases:
        if base is not None and (base / rel).is_file():
            return base / rel
    return None



def copy_ledger(spec: dict, ctx: dict) -> str:
    """The repository's recording, copied: the checker may append to the copy, and nothing
    it does reaches the tree under test. Copying is the DOCTOR's own step, so its failure is
    the doctor's own row — never a traceback out of the run."""
    if not spec.get("ledger"):
        return ""
    target = ctx["tmp"] / Path(spec["ledger"]).name
    try:
        shutil.copyfile(ctx["root"] / spec["ledger"], target)
    except OSError as exc:
        return f"UNREADABLE: {exc.strerror or exc}"
    return str(target)


def selfcheck() -> int:
    """The table's own invariants — the ones a wrong row would pass silently."""
    names = [s["check"] for s in CHECKS]
    assert len(names) == len(set(names)), names
    for spec in CHECKS:
        assert spec.get("fix"), spec
        assert "args" in spec or spec.get("why"), spec
        if spec.get("clean_line"):
            re.compile(spec["clean_line"])
            assert "red_exits" not in spec, f"{spec['check']}: two contracts at once"
        if spec.get("quick"):
            assert "{home}" not in "".join(spec.get("args", ())), \
                f"{spec['check']}: the quick measure may not read the user home directory"
    assert vault(Path(tempfile.gettempdir()) / "arch-doctor-nowhere-at-all") is None
    assert package_root(Path("/x/polaris/skills/architecture/scripts/a.py")) == Path("/x/polaris")
    assert package_root(Path("/x/vault/suite/architecture/scripts/a.py")) is None
    print(f"arch_doctor_sources selfcheck OK — {len(CHECKS)} checks, every contract well-formed")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else 2)


# menu.md, emitted by the machine: (check, verdict) -> the verb line the naked invocation
# hands on. A missing key is "no verb", and menu.md says why for each of them.
MENU = {
    ("backbone", "RED"): "/architecture doc — the document cites a path that is gone; on a "
                         "DECISION_CALL_SITE_MISSING cause: /architecture land <DEC-id>",
    ("decisions", "RED"): "/architecture land <DEC-id> — accepted, and its old call path still runs",
    ("scope-drift", "RED"): "/architecture decide — changed files no active intent claims",
    ("symbol-drift", "RED"): "/bugfix on the symbol named — its checksum moved from the spec",
    ("decision-drift", "RED"): "/architecture land <DEC-id> — the code a Decision referenced moved",
    ("dependency-drift", "RED"): "/architecture decide — a module's import set moved; coupling is a commitment",
    ("test-drift", "RED"): "/tdd-dev on the changed symbol — its test stayed frozen",
}
BACKBONE_UNKNOWN = (  # evidence marker -> line, first match wins; none -> checker failed, no verb
    (NOT_HERE, "/architecture audit <import-root> — the harness is absent, nothing is declared"),
    ("FRONTMATTER_MISSING", "/architecture init — this repository has not adopted the backbone"),
    ("LIVE_DOC_MISSING", "/architecture init — this repository has not adopted the backbone"),
    ("nothing to judge", "/architecture audit <import-root> — nothing is declared here yet"),
)
