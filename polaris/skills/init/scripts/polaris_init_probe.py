#!/usr/bin/env python3
"""polaris_init_probe.py — what `polaris init` READS off a repository before it writes.

Three questions with a provable answer: where the vault is, what this repository is
called, and which code the live documents describe. Nothing here guesses; a question
without a provable answer belongs in the audit, addressed to the founder.

Covered by `polaris_init.py --selfcheck`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as backbone  # noqa: E402

TRIAD = sorted(backbone.LIVE_DOCS)
CODE_DIRS = ("src", "app", "lib", "backend", "frontend", "packages", "api")
# Never seal against a path `apply` itself writes into: the seal would move the moment
# it is written and no number of re-runs would ever settle it.
WRITTEN = frozenset(TRIAD) | {"decisions"}


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def vault_root(start: Path) -> Path:
    """The vault's MAIN checkout, never the worktree the agent happens to run from.

    An agent works in a worktree and deletes it when done. Pinning the host repository
    to the running script's own parent would leave it pointing at a path that is gone.
    """
    common = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent.resolve() if common else start.resolve()


def harness(start: Path) -> Path | None:
    """The vault these scripts run from, or None when they were installed without one.

    A skills-CLI install copies skill folders only: run from there, `vault_root` answers the
    skill folder itself, which is no vault. Pointing a host repository at it would be a lie.
    """
    root = vault_root(start)
    return root if (root / "scripts" / "contextpack.py").is_file() else None


def declared_vault(root: Path) -> dict:
    """What `polaris.vault` says HERE, and whether it still resolves.

    The pointer lives in the shared `.git/config`, so another panel rewrites it under
    you. Reporting it every run is the only way a silent rewrite is visible before the
    pack stops emitting.
    """
    value = _git(root, "config", "--get", "polaris.vault")
    resolves = bool(value) and (Path(value) / "scripts" / "contextpack.py").is_file()
    return {"declared": value or None, "resolves": resolves}


def _holds_an_authority(item: Path) -> bool:
    """A directory holding an authority-shaped file is one `apply` declares INTO.

    `docs/` carrying `docs/architecture/ARCHITECTURE.md` is the triad bug one level
    down: seal against it and the declaration moves the seal that was just written.
    """
    if item.is_file():
        return item.name in backbone.AUTHORITY_BASENAMES
    return any(path.name in backbone.AUTHORITY_BASENAMES for path in item.rglob("*"))


def cockpit(root: Path) -> Path | None:
    """The one cockpit `/start` would read here, by the package's own fallback order."""
    base = root / "_polaris" if (root / "_polaris" / "config.yml").is_file() else root
    for candidate in sorted(base.glob("team/*/current.md")) + [base / "state/current.md"]:
        if candidate.is_file():
            return candidate
    return None


def identity(root: Path) -> dict[str, str]:
    """workspace/repo from the git remote, else the directory. Never invented."""
    remote = _git(root, "remote", "get-url", "origin")
    slug = remote.removesuffix(".git").replace(":", "/").rstrip("/").split("/")
    repo = slug[-1] if remote else root.name
    workspace = slug[-2] if len(slug) > 1 and remote else repo
    return {"workspace": workspace, "repo": repo}


def source_scope(root: Path) -> list[str]:
    """Every source root that exists — and never a path `apply` writes into, so the cited
    scope names the code, not the backbone itself. A repository with no provable source
    root refuses.
    """
    found = [name for name in CODE_DIRS if (root / name).is_dir()]
    if found:
        return found
    loose = [
        item.name for item in sorted(root.iterdir())
        if item.name not in WRITTEN and not item.name.startswith(".")
        and not _holds_an_authority(item)
    ]
    if not loose:
        raise backbone.ContractError(
            "SCOPE_UNPROVABLE", "no path to seal the triad against — name one")
    return loose[:1]
