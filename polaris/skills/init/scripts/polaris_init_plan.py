#!/usr/bin/env python3
"""polaris_init_plan.py — the alignment plan `propose` prints, and nothing it writes.

Areas are listed as a signature request, never created: #331 (KILL) settled that the
areas are not derived from the domain — the audit proposes them and the founder signs.

Covered by `polaris_init.py --selfcheck`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as backbone  # noqa: E402
from polaris_init_probe import cockpit, declared_vault, source_scope  # noqa: E402

def unsigned_dossiers(root: Path) -> list[dict]:
    """Dossiers this run must not complete: their manifest is a founder signature.

    `audit_authorities` never looks inside `docs/modules/`, so without this the seal is
    the first thing to notice — after `apply` has already written the whole triad.
    """
    modules = root / "docs" / "modules"
    if not modules.is_dir():
        return []
    listed = [
        {"code": "MODULE_CHANGELOG_MISSING" if not (item / "CHANGELOG.md").is_file()
         else "MODULE_MANIFEST_MISSING",
         "source_id": str(item.relative_to(root)),
         "remedy": "founder signature required — apply refuses to invent a manifest"}
        for item in sorted(modules.iterdir())
        if item.is_dir()
        if not ((item / "CHANGELOG.md").is_file()
                and (item / "module-context.json").is_file())
    ]
    return listed or _guide_blocker(root, modules)


def _guide_blocker(root: Path, modules: Path) -> list[dict]:
    """The one dossier fault that is not per-directory: the guide itself is absent."""
    if (modules / "README.md").is_file():
        return []
    return [{"code": "MODULE_GUIDE_MISSING", "source_id": "docs/modules/README.md",
             "remedy": "founder signature required — apply writes no module guide"}]


def vault_row(root: Path, vault: Path | None) -> list[dict]:
    """Absent or pointing nowhere is a row WITH its remedy; declared is just reported.

    Without a vault there is no pointer `apply` could set, so its absence blocks nothing.
    """
    pointer = declared_vault(root)
    if pointer["resolves"] or vault is None:
        return []
    return [{
        "code": "VAULT_UNDECLARED",
        "source_id": pointer["declared"] or "git config polaris.vault",
        "remedy": "apply (re)sets polaris.vault to the vault's main checkout, every run",
    }]


def scope_question(root: Path) -> list[str]:
    """No provable source root is a question for the founder, never a traceback."""
    try:
        source_scope(root)
    except backbone.ContractError:
        return ["snapshot_scope: no provable source root here, so there is nothing to "
                "seal the live documents against. Name the path that holds this "
                "repository's code."]
    return []


def cockpit_question(root: Path) -> list[str]:
    """A cockpit with no `## Active Priorities` is asked about, never written."""
    path = cockpit(root)
    if path is None:
        return ["_polaris/state/current.md: no cockpit in THIS checkout — it is "
                "gitignored and per-checkout, so a fresh worktree has none by design. "
                "Read the main checkout's cockpit, or say where this repo is driven from."]
    if re.search(r"(?m)^## Active Priorities\s*$", path.read_text(errors="replace")):
        return []
    return [f"{path.relative_to(root)}: the cockpit has no `## Active Priorities` "
            "heading, so the brief reads `no priority 1`. What are the priorities, and "
            "in what order? apply does not write them — they are yours to state."]


AREA_ROOTS = ("docs", "_project_specs")


def area_candidates(root: Path) -> list[str]:
    """Never from the domain (#331 KILL): a declared map, else the folders that exist."""
    declared = root / ".github" / "DOMAINS.yml"
    if declared.is_file():
        return [
            line.split(":")[0].strip("- ").strip()
            for line in declared.read_text(errors="replace").splitlines()
            if line.strip().startswith("- ")
        ]
    return [
        f"{parent}/{child.name}"
        for parent in AREA_ROOTS
        if (root / parent).is_dir()
        for child in sorted((root / parent).iterdir())
        if child.is_dir()
    ]


def propose(report: dict, root: Path) -> str:
    """The alignment plan. It writes nothing: the areas table is a signature request."""
    lines = [
        f"# Piano di allineamento — {report['root']}", "",
        f"Verdetto audit: **{report['verdict']}** · "
        f"{len(report['blocking'])} finding bloccanti · "
        f"{report['records']['prose_adr']} ADR in prosa, "
        f"{report['records']['decisions_md_entries']} voci in `decisions.md`.", "",
        "## Cosa farebbe `apply --mode minimal`", "",
        "| finding | sorgente | rimedio |", "|---|---|---|",
    ]
    lines += [
        f"| {item['code']} | `{item['source_id']}` | {item['remedy']} |"
        for item in report["blocking"]
    ] or ["| — | — | nessun blocco: il backbone regge già |"]
    return "\n".join(lines + _areas_block(root) + _questions_block(report))


def _areas_block(root: Path) -> list[str]:
    """Proposed, never created: `apply` does not write a dossier without a signature."""
    candidates = area_candidates(root) or ["(nessuna cartella candidata)"]
    return [
        "",
        "## Aree proposte — richiedono la firma del founder",
        "",
        "Nessuna di queste viene creata da `apply --mode minimal`. #331 (KILL): le aree non si",
        "derivano dal dominio, le propone l'audit e le firma il founder.",
        "",
        "| Area | evidenza | firma |",
        "|---|---|---|",
        *[f"| `{name}` | la cartella esiste nel repo | ☐ |" for name in candidates],
    ]


def _questions_block(report: dict) -> list[str]:
    return ["", "## Domande (una per scelta non provabile)", ""] + [
        f"{index}. {text}" for index, text in enumerate(report["questions"], 1)
    ]
