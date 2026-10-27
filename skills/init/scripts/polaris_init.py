#!/usr/bin/env python3
"""polaris_init.py — bring a product repository into the harness, in three verbs.

    polaris_init.py audit   --root <repo>   # JSON: what is there, what blocks, what to ask
    polaris_init.py propose --root <repo>   # Markdown: the alignment plan, areas to sign
    polaris_init.py apply --mode minimal --root <repo>

`audit` and `propose` write nothing — the first pass never does work (repo-adoption spec).
`apply --mode minimal` is additive: the prose stays, every unproven line is UNKNOWN, and no
area dossier is created without a founder signature (#331 KILL: areas are not derived).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_context_backbone as backbone  # noqa: E402
from polaris_init_apply import apply_minimal  # noqa: E402
from polaris_init_probe import (  # noqa: E402
    declared_vault, harness, identity, source_scope)
from polaris_init_plan import (  # noqa: E402
    cockpit_question, propose, scope_question, unsigned_dossiers, vault_row)

REMEDY = {
    "LIVE_DOC_MISSING": "apply writes the typed document, every unproven line UNKNOWN",
    "FRESHNESS_UNKNOWN": "apply adds snapshot_scope over the kept prose",
    "AUTHORITY_SHADOW": "apply declares the copy derived (projection_of / superseded_by)",
    "AUTHORITY_DECLARATION_INVALID": "apply rewrites the declaration the contract expects",
    "CITED_PATH_MISSING": "fix snapshot_scope: it cites a path that is not there",
}
ASK = {
    "UNCLASSIFIED_SOURCE": "what is this document — a projection, history, or an authority?",
    "SOURCE_UNREADABLE": "this source cannot be read: keep it, or drop it from the tree?",
    "TYPE_MISPLACED": "this heading claims a type the document does not own: move or retype?",
    "SOURCE_ID_DUPLICATE": "two sources claim one id: which one keeps it?",
}


def doc_state(root: Path, name: str) -> str:
    """absent, prose, or typed — typed means the live-document contract is declared."""
    path = root / name
    if not path.is_file():
        return "absent"
    record = backbone._frontmatter_optional(path)
    return "typed" if backbone.DOC_REQUIRED <= record.keys() else "prose"


def prose_records(root: Path) -> dict[str, int]:
    """What a human already wrote as decisions, before any of it was typed."""
    loose = [
        path
        for folder in ("adr", "docs/architecture")
        for path in sorted((root / folder).rglob("*.md"))
        if (root / folder).is_dir()
        and not backbone._frontmatter_optional(path).get("decision_id")
    ]
    ledger = root / "decisions.md"
    entries = ledger.read_text(errors="replace").count("\n## ") if ledger.is_file() else 0
    return {"prose_adr": len(loose), "decisions_md_entries": entries}


def _scope_line(root: Path) -> list[str]:
    """What would be sealed, and — when some source roots are left out — which ones."""
    try:
        scope = source_scope(root)
    except backbone.ContractError:
        return []
    return [f"snapshot_scope: apply would seal the triad against {scope} — is that the "
            "code these documents describe? Anything not listed is NOT sealed."]


def questions(root: Path, findings: list[dict]) -> list[str]:
    """One question per choice this run cannot prove. Never a guess written as a fact."""
    who = identity(root)
    asked = [
        f"workspace/repo: apply would declare `{who['workspace']}/{who['repo']}` "
        "from the git remote — is that the workspace name you want?",
        *_scope_line(root),
        "owner: apply would declare `role:founder` on all three documents — who owns them?",
        "areas: `propose` lists the candidates; none is created without your signature.",
    ]
    seen: set[str] = set()
    for finding in findings:
        prompt = ASK.get(finding["code"])
        if prompt and finding["source_id"] not in seen:
            seen.add(finding["source_id"])
            asked.append(f"{finding['source_id']}: {prompt}")
    return asked


def _blocking(report: dict) -> list[dict]:
    """A blocker either has a remedy `apply` owns, or it is a question for the founder."""
    return [
        {"code": item["code"], "source_id": item["source_id"],
         "remedy": REMEDY.get(item["code"], "founder answer required — see questions")}
        for item in report["findings"]
        if item["blocking"]
    ]


def _dossier_questions(root: Path) -> list[str]:
    """A dossier's manifest is a signature, so it is asked for and never written."""
    return [
        f"{item['source_id']}: a dossier with no Polaris manifest — a capability module "
        "(then its manifest needs your signature), or does it move out of docs/modules/?"
        for item in unsigned_dossiers(root)
    ]


def audit(root: Path, vault: Path | None) -> dict:
    """Read-only: this verb writes nothing, which is the first-pass contract."""
    report = backbone.audit_authorities(root)
    return {
        "root": str(root),
        "verdict": report["verdict"],
        "live_documents": {name: doc_state(root, name) for name in backbone.LIVE_DOCS},
        "blocking": _blocking(report) + vault_row(root, vault) + unsigned_dossiers(root),
        "coverage": report["coverage"]["status"],
        "records": prose_records(root),
        "vault": declared_vault(root),
        "questions": (questions(root, report["findings"])
                      + scope_question(root) + cockpit_question(root)
                      + _dossier_questions(root)),
    }


def selfcheck() -> int:
    """The fixture battery as one command: a repo-shaped tree taken to a sealed pack."""
    here = Path(__file__).resolve().parent / "test"
    if not here.is_dir():
        return _installed_selfcheck()
    sys.path[:0] = [str(here), str(here.parents[1])]  # `scripts.test.…` imports too
    suite = unittest.TestSuite()
    for name in sorted(path.stem for path in here.glob("test_polaris_init*.py")):
        spec = spec_from_file_location(name, here / f"{name}.py")
        module = module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    return 0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1


def _installed_selfcheck() -> int:
    """Installed without the battery: one fixture repo, audit writes nothing, apply is READY.

    An empty battery would pass by construction, so a skills-CLI copy proves the one path a
    collaborator runs instead: no vault, no pointer written, the prose kept.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "main.py").write_text("print('ok')\n")
        (root / "CONTEXT.md").write_text("# Demo\n\nProse kept.\n")
        for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                     ["-c", "user.email=t@example.com", "-c", "user.name=t",
                      "commit", "-qm", "fixture"]):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        audit(root, None)
        clean = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                               capture_output=True, text=True).stdout == ""
        ready = apply_minimal(root, None)["backbone"]["verdict"] == "READY"
        kept = "Prose kept." in (root / "CONTEXT.md").read_text()
        pointer = subprocess.run(["git", "config", "--get", "polaris.vault"], cwd=root,
                                 capture_output=True, text=True).stdout.strip()
    ok = clean and ready and kept and not pointer
    print(f"polaris_init selfcheck (installed): audit-writes-nothing={'ok' if clean else 'FAIL'} "
          f"apply-ready={'ok' if ready else 'FAIL'} prose-kept={'ok' if kept else 'FAIL'} "
          f"no-pointer={'ok' if not pointer else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="bring a repository into the harness")
    parser.add_argument("verb", nargs="?", choices=["audit", "propose", "apply"])
    parser.add_argument("--selfcheck", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--mode", choices=["minimal"], default="minimal")
    parser.add_argument("--vault", type=Path,
                        default=harness(Path(__file__).resolve().parent))
    args = parser.parse_args()
    if args.selfcheck:
        return selfcheck()
    if args.root is None:
        parser.error("--root is required")
    return _run(args.verb, args.root.resolve(), args.vault and args.vault.resolve())


def _run(verb: str, root: Path, vault: Path | None) -> int:
    if verb == "propose":
        print(propose(audit(root, vault), root))
        return 0
    if verb == "audit":
        print(json.dumps(audit(root, vault), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    try:
        print(json.dumps(apply_minimal(root, vault), indent=2, sort_keys=True))
    except backbone.ContractError as exc:
        print(f"{exc.code}: {exc.detail}")
        return 2
    except OSError as exc:
        print(f"WRITE_REFUSED: {exc.strerror or exc} — nothing was written")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
