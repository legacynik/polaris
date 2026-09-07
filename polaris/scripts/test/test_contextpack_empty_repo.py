"""#344 — the contract a repository with no history needs before a pack can be emitted.

The resolver shipped in the package is only worth shipping if a repository that installs
it can run it. So this builds a repository from nothing, writes the smallest contract the
backbone validator accepts, seals it with the shipped commands, and asserts a `CTX-` id
comes out. It is the acceptance of the issue, executable, and it is also the contract's
only documentation: what is written below IS what an adopting repository must have.

Five things, and no more. The three live authorities at the root, one accepted Decision
under `decisions/`, and a commit for them to point at — `snapshot_ref` and `source_ref`
name a commit in THIS repository, so the first commit has to exist before they are
written. `decisions/manifest.json` and every seal are computed by `--reseal`, never by
hand. `_polaris/config.yml` is the harness contract and the resolver never reads it: a
repository can emit a pack without one, and this test proves that by not writing it.

The assertions are tied to the validator's own required-field sets, so a contract that
grows a field turns this red instead of leaving a stale recipe in a docstring.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
AUTHORITIES = (("CONTEXT.md", "context"), ("ARCHITECTURE.md", "architecture"),
               ("DOMAIN.md", "domain"))
GOVERNED = "source.txt"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=root, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def cli(name: str, root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / name), *args],
                          cwd=root, capture_output=True, text=True)


def write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(record, indent=2, sort_keys=True)
    path.write_text(f"---\n{body}\n---\n\n# {path.stem}\n", encoding="utf-8")


def authorities(root: Path, sha: str) -> None:
    """The three live documents, each declaring the commit and the scope it describes."""
    base = {"schema_version": 1, "status": "active", "owner": "role:cto",
            "workspace": "acme", "repo": "acme-api", "snapshot_ref": f"git:{sha}",
            "snapshot_scope": [GOVERNED], "review_trigger": ["the governed source changes"]}
    for name, kind in AUTHORITIES:
        record = dict(base, document_type=kind)
        if name == "DOMAIN.md":
            record["domains"] = [{"domain_id": "api", "name": "API"}]
            record["components"] = [{"component_id": "svc", "domains": ["api"],
                                     "paths": [GOVERNED]}]
        write(root / name, record)


def decision(root: Path, sha: str) -> None:
    """One accepted Decision — the pack's whole reason to exist is carrying these."""
    write(root / "decisions" / "DEC-1.md", {
        "schema_version": 1, "decision_id": "DEC-1", "decision_key": "api-shape",
        "title": "The API is versioned in the path", "kind": "architecture",
        "status": "accepted", "owner": "role:cto", "decided_at": "2026-09-06",
        "workspace": "acme", "repos": ["acme-api"],
        "governs": {"domains": ["api"], "components": ["svc"], "concerns": ["routing"]},
        "supersedes": [], "superseded_by": None, "source_ref": f"git:{sha}",
        "evidence": ["issue:acme-api#1"], "enforcement": [GOVERNED],
        "call_sites": [GOVERNED], "prerequisites": [],
        "closure_check": "every route carries /v1", "review_trigger": ["a route is added"],
        "scope_ref": "scope-sha256:" + "0" * 64,
        "legacy_review": {"scope": ["svc"], "sources": []}})


def adopt(root: Path) -> None:
    """A repository with one file, taken to a sealed backbone by the shipped commands."""
    (root / GOVERNED).write_text("the source this repo governs\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "the repo before the harness")
    sha = git(root, "rev-parse", "HEAD")
    authorities(root, sha)
    decision(root, sha)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "adopt the harness")


class EmptyRepoEmitsAPack(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="adopt-")) / "acme-api"
        self.root.mkdir()
        self.addCleanup(__import__("shutil").rmtree, self.root.parent, True)
        adopt(self.root)

    def seal(self) -> None:
        for step in ("--reseal", "--init"):
            done = cli("check_context_backbone.py", self.root, step, ".")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(json.loads(done.stdout)["verdict"], "READY", done.stdout)
            git(self.root, "add", "-A")
            if git(self.root, "status", "--porcelain"):
                git(self.root, "commit", "-qm", f"backbone {step}")

    def test_a_repository_with_no_history_emits_a_context_pack(self) -> None:
        self.seal()
        done = cli("contextpack.py", self.root, "resolve", "--root", ".")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        pack = json.loads(done.stdout)
        self.assertTrue(pack["context_pack_id"].startswith("CTX-"), pack["context_pack_id"])
        self.assertEqual(pack["workspace"], "acme")
        self.assertEqual([d["source_id"] for d in pack["decisions"]], ["DEC-1"])
        self.assertEqual(pack["sealed_commit"], git(self.root, "rev-parse", "HEAD"))

    def test_the_resolver_never_asks_for_the_harness_contract_file(self) -> None:
        """`_polaris/config.yml` is the harness contract, not the resolver's input."""
        self.assertFalse((self.root / "_polaris").exists())
        self.seal()
        self.assertEqual(cli("contextpack.py", self.root, "resolve", "--root", ".").returncode, 0)

    def test_the_written_contract_is_the_whole_contract(self) -> None:
        """If the validator grows a required field, this recipe is stale — say so here."""
        sys.path.insert(0, str(SCRIPTS))
        import check_context_backbone as cbb  # noqa: E402

        self.assertEqual(set(cbb.LIVE_DOCS), {name for name, _ in AUTHORITIES})
        doc = json.loads((self.root / "CONTEXT.md").read_text().split("\n---\n")[0][4:])
        self.assertEqual(cbb.DOC_REQUIRED - set(doc), set())
        dec = json.loads((self.root / "decisions" / "DEC-1.md").read_text()
                         .split("\n---\n")[0][4:])
        self.assertEqual(cbb.DECISION_REQUIRED - set(dec), set())

    def test_an_unsealed_backbone_refuses_to_emit(self) -> None:
        """The seal is the contract, not a formality: no manifest, no pack."""
        done = cli("contextpack.py", self.root, "resolve", "--root", ".")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn(":", done.stderr.strip().splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
