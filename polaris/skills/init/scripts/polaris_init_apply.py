#!/usr/bin/env python3
"""polaris_init_apply.py — the writing half of `polaris init`, minimal mode only.

Additive by construction: existing prose is kept, existing frontmatter is merged into and
never replaced, and every line this module writes that no path proves says UNKNOWN. It
creates no area dossier: #331 (KILL) puts areas behind a founder signature.

Covered by `polaris_init.py --selfcheck`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as backbone  # noqa: E402
from polaris_init_plan import unsigned_dossiers  # noqa: E402
from polaris_init_probe import _git, identity, source_scope  # noqa: E402
from polaris_init_tx import restore, touchable  # noqa: E402
from polaris_init_docs import (  # noqa: E402
    REVIEW, UNPROVEN, annotate, architecture_body, context_body,
    declare_derived, domain_body, header, split, write)

TRIAD = sorted(backbone.LIVE_DOCS)
# The gate lives outside the host repository — in the vault, or in the architecture skill a
# skills-CLI install put under $HOME — so the probe RESOLVES it the way the shim does and holds
# no absolute path of its own: one would read past the shadow tree the probe is falsified in.
PROBE = ('V="${POLARIS_VAULT:-$(git config --get polaris.vault)}"; C=; '
         'for D in ${V:+"$V/scripts"} "$HOME/.agents/skills/architecture/scripts" '
         '"$HOME/.claude/skills/architecture/scripts" "$HOME/.codex/skills/architecture/scripts"; '
         'do [ -f "$D/check_context_backbone.py" ] && C="$D/check_context_backbone.py" && break; '
         'done; [ -n "$C" ] && python3 -I "$C" --check .')
CODE_DIRS = ("src", "app", "lib", "backend", "frontend", "packages", "api")


def components(root: Path, who: dict[str, str]) -> list[dict]:
    """One component per path that EXISTS. Existence is the proof; the naming is not."""
    slug = who["repo"]
    listed = [
        {"component_id": f"{slug}.{name}", "name": f"{name}/ ({UNPROVEN})",
         "domains": [f"{slug}.unclassified"], "paths": [name]}
        for name in CODE_DIRS
        if (root / name).is_dir()
    ]
    return [
        {"component_id": f"{slug}.polaris-backbone", "name": "Live documents of this repo",
         "domains": [f"{slug}.unclassified"], "paths": TRIAD},
        *listed,
    ]


def _write_triad(root: Path, who: dict, scope: list[str]) -> list[dict]:
    """The prose is kept; the frontmatter is added around it."""
    listed = components(root, who)
    _type(root / "CONTEXT.md", header(who, "context", scope), context_body(who))
    _type(root / "ARCHITECTURE.md", header(who, "architecture", scope),
          architecture_body(who, listed[1:]))
    _type(root / "DOMAIN.md", header(who, "domain", scope) | {
        "domains": [{"domain_id": f"{who['repo']}.unclassified", "name": UNPROVEN}],
        "components": listed,
    }, domain_body(who))
    return listed


def _type(path: Path, typed: dict, fallback: str) -> None:
    """Add the contract's fields; never re-dump foreign YAML, never replace a declared key.

    A re-run on a typed triad once narrowed `snapshot_scope` and dropped every declared
    `review_trigger` (#480): whatever the repository already answered is its answer.
    """
    existing, _ = split(path)
    annotate(path, {key: value for key, value in typed.items() if key not in existing})
    if not path.is_file() or not split(path)[1].strip():
        record, _ = split(path)
        write(path, record, fallback)


def _decision(root: Path, who: dict, component_id: str) -> dict:
    return {
        "schema_version": 1,
        "decision_id": f"DEC-{who['repo']}-polaris-backbone-001",
        "decision_key": "polaris-documentary-backbone",
        "title": "Adopt the Polaris documentary backbone in this repository",
        "kind": "architecture", "status": "accepted", "owner": "role:founder",
        "decided_at": date.today().isoformat(), "workspace": who["workspace"],
        "repos": [who["repo"]], "supersedes": [], "superseded_by": "",
        "governs": {"domains": [f"{who['repo']}.unclassified"],
                    "components": [component_id], "concerns": ["documentary-backbone"]},
        "source_ref": f"git:{_git(root, 'rev-parse', 'HEAD')}",
        "evidence": ["issue:polaris-os#333", "issue:polaris-os#332"],
        "enforcement": ["gate:check_context_backbone"], "call_sites": ["CONTEXT.md"],
        "prerequisites": [], "probe": PROBE, "probe_kills": "CONTEXT.md",
        "closure_check": PROBE,
        "review_trigger": REVIEW, "legacy_review": _legacy_review(component_id),
    }


def _legacy_review(component_id: str) -> dict:
    """What this Decision replaces: nothing typed existed, and it says so."""
    return {
        "reviewed_at": date.today().isoformat(), "scope": [component_id], "sources": [],
        "verdict": "No earlier Decision recorded this repository's documentary "
                   "authorities; this one does, and claims nothing about the code it "
                   "has not measured.",
        "conflicts": [],
    }


def _refuse_unsigned(root: Path) -> None:
    """Refuse whole rather than half: a validation that raises mid-write leaves a false triad."""
    blockers = unsigned_dossiers(root)
    if blockers:
        raise backbone.ContractError(
            blockers[0]["code"],
            "unsigned dossiers, nothing written: "
            + ", ".join(item["source_id"] for item in blockers),
        )


def apply_minimal(root: Path, vault: Path | None) -> dict:
    """All-or-nothing: on any failure the tree is byte-identical to before the call.

    Validation comes LAST and can raise for reasons no precheck sees — a Decision from
    another workspace, an unwritable path. Leaving a half-written backbone behind was
    worse than refusing, and the scope variant of it never recovered on a re-run.
    """
    _refuse_unsigned(root)
    before = {path: path.read_bytes() if path.is_file() else None
              for path in touchable(root)}
    try:
        return _write_everything(root, vault)
    except BaseException:
        restore(before)
        raise


def _write_everything(root: Path, vault: Path | None) -> dict:
    who = identity(root)
    scope = source_scope(root)
    listed = _write_triad(root, who, scope)
    shadows = declare_derived(root, listed[0]["component_id"])
    record = _decision(root, who, listed[0]["component_id"])
    write(root / "decisions" / f"{record['decision_id']}.md", record,
           f"# {record['title']}\n\nWritten by `polaris init --mode minimal`.\n")
    ready = backbone.init_backbone(root)
    if vault is not None:  # installed without a vault: there is nothing to point at
        subprocess.run(["git", "config", "polaris.vault", str(vault)], cwd=root, check=False)
    return {"mode": "minimal", "identity": who, "snapshot_scope": scope,
            "components": [item["component_id"] for item in listed],
            "declared_derived": shadows, "decision": record["decision_id"],
            "vault": vault and str(vault), "backbone": ready}
