"""L2-T4 (#403) — every branch the declared layer added, forced with an input built for it.

`test_contextpack_declared.py` holds the decisions: it was red before the layer existed and
green after. This file holds the BRANCHES those decisions introduced, and it is green from
the start — the same shape as `test_id_reservation.py`, and the honest label for a test that
exercises a path rather than driving a behaviour into being.

The reason it exists is the anti-mirror rule: a happy path over three prose records proves
nothing about a repository whose records are actually broken, empty, mis-encoded, typed,
duplicated, unnumbered or too many. Each case below names the branch it drives and the
observable that is wrong if the branch misbehaves. Two of them are not coverage but safety:

- **A live document the validator REFUSED must never become a declared row.** `invalid`
  frontmatter is a refusal, and a layer that read it as prose would carry as authority a
  record the backbone gate rejected. `is_prose` asks the validator; this asserts it.
- **A repository with no commit must not raise.** `_paths` reads HEAD, and a repository
  where HEAD does not resolve is the normal state of a freshly initialised clone; the pack
  owes it an answer, not a traceback.

And one is a contract the layer would otherwise break in silence: more prose ADRs than
`contextpack_records.LIMIT` adds one `unknown` row saying how many were not read. A cap that drops a source
without a word is exactly the silence `contract:pack-never-silent` forbids, only harder to
notice than an exception.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_context_backbone as cbb  # noqa: E402
import contextpack  # noqa: E402
import contextpack_declared as declared  # noqa: E402
import contextpack_prose as prose  # noqa: E402
import contextpack_records as records  # noqa: E402

TYPED = {"schema_version": 1, "document_type": "context", "status": "active",
         "owner": "role:cto", "workspace": "acme", "repo": "acme-api",
         "snapshot_ref": "scope-sha256:0", "snapshot_scope": ["src"],
         "review_trigger": ["never"]}
MAP = """# acme-api

## Pricing

Named and committed: `docs/adr/ADR-014-navigator.md`.
Named and absent: `docs/adr/ADR-999-ghost.md`.
Not a document: `scripts/run.sh`, `acme-api`.
"""


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


class Built(unittest.TestCase):
    def repo(self, files: dict[str, bytes | str], commit: bool = True) -> Path:
        root = Path(tempfile.mkdtemp(prefix="declared-adv-")).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        for name, body in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(body if isinstance(body, bytes) else body.encode())
        git(root, "init", "-q")
        if commit:
            git(root, "add", "-A")
            git(root, "commit", "-qm", "the repository under test")
        return root

    def pack(self, root: Path, *areas: str) -> dict:
        return contextpack.resolve(root, "", list(areas), degrade=True)

    def ids(self, rows: list[dict]) -> set[str]:
        return {row["source_id"] for row in rows}


class TheRefusalOfTheValidatorIsNeverOverruled(Built):
    def section(self, body: str) -> dict[str, str]:
        """A repository the UNKNOWN branch reaches: `CONTEXT.md` is prose, so its failure is
        an ABSENCE and the resolver degrades instead of refusing; the document under test is
        the second authority, and it names a committed document in a `## ` section."""
        return {"CONTEXT.md": "# acme-api\n\nProse, no map.\n",
                "ARCHITECTURE.md": body + "\n## Pricing\n\n`docs/adr/ADR-014-x.md`\n",
                "docs/adr/ADR-014-x.md": "# ADR-014\n\n- Status: accepted\n"}

    def test_a_live_document_with_broken_frontmatter_gets_no_declared_row(self) -> None:
        """`invalid` is a refusal, not prose: carrying it would promote what the backbone
        gate rejected, and would read its sections as an area map. The `unknown` row of
        L2-T2 stays its only row."""
        pack = self.pack(self.repo(self.section("---\n: :\nschema_version: 1\n---\n")),
                         "pricing")
        self.assertNotIn("ARCHITECTURE.md", self.ids(pack["declared"]))
        self.assertEqual([r for r in pack["unknown"] if r["source_id"] == "ARCHITECTURE.md"
                          ][0]["reason"].split(":")[0], "invalid")

    def test_a_typed_live_document_gets_no_declared_row_either(self) -> None:
        """The other side: a document the sealed layer or L2-T2 owns is not read here, so
        frontmatter that PARSES keeps its sections out of the area map too."""
        body = "---\n" + json.dumps(TYPED, indent=2) + "\n---\n"
        pack = self.pack(self.repo(self.section(body)), "pricing")
        self.assertNotIn("ARCHITECTURE.md", self.ids(pack["declared"]))

    def test_an_empty_live_document_is_not_an_area_map(self) -> None:
        root = self.repo({"CONTEXT.md": "\n", "docs/adr/ADR-1-x.md": "# ADR-1\n"})
        self.assertNotIn("CONTEXT.md", self.ids(self.pack(root, "pricing")["declared"]))


class ARepositoryWithNoHeadStillAnswers(Built):
    def test_no_commit_is_no_rows_and_no_traceback(self) -> None:
        """`_paths` reads HEAD; a freshly initialised clone has none. The layer owes an
        answer, and the answer is that it found nothing to declare."""
        root = self.repo({"CONTEXT.md": "# prose\n"}, commit=False)
        self.assertEqual(declared.rows(root, ["pricing"]), ([], []))

    def test_the_resolver_over_the_same_repository_does_not_raise(self) -> None:
        root = self.repo({"CONTEXT.md": "# prose\n"}, commit=False)
        self.assertEqual(self.pack(root, "pricing")["declared"], [])


class NothingIsDroppedWithoutAWord(Built):
    def files(self, many: int) -> dict[str, str]:
        files = {"CONTEXT.md": "# prose\n"}
        files.update({f"docs/adr/ADR-{i:03d}-x.md": f"# ADR-{i:03d}\n\n- Status: accepted\n"
                      for i in range(many)})
        return files

    def test_more_adrs_than_the_layer_reads_adds_one_unknown_row_with_the_count(self) -> None:
        root = self.repo(self.files(5))
        with mock.patch.object(records, "LIMIT", 3):
            pack = self.pack(root)
        self.assertEqual(len([r for r in pack["declared"] if r["kind"] == "adr"]), 3)
        over = [r for r in pack["unknown"] if r["source_id"] == "adr:over-limit"]
        self.assertEqual(len(over), 1, pack["unknown"])
        self.assertIn("2 prose ADR(s) not read", over[0]["reason"])
        self.assertEqual((over[0]["layer"], over[0]["path"]), ("unknown", None))

    def test_under_the_limit_nothing_is_announced(self) -> None:
        pack = self.pack(self.repo(self.files(2)))
        self.assertEqual([r for r in pack["unknown"] if r["source_id"] == "adr:over-limit"], [])

    def test_the_rows_kept_are_the_newest_so_the_cut_is_not_arbitrary(self) -> None:
        """#457 superseded "the first by path": five records in ONE commit carry no time
        to tell them apart, so the sequence number does — the highest is the newest."""
        root = self.repo(self.files(5))
        with mock.patch.object(records, "LIMIT", 3):
            kept = [r["source_id"] for r in self.pack(root)["declared"] if r["kind"] == "adr"]
        self.assertEqual(kept, [f"docs/adr/ADR-{i:03d}-x.md" for i in (4, 3, 2)])


class ThePrimitivesDoNotGuess(unittest.TestCase):
    def test_a_recurrence_that_is_not_a_number_is_not_a_count(self) -> None:
        """Round 2 (R8 of the #423 breaker): `Recurrence: many` answered 0, and 0 is a
        number nobody wrote. A count that cannot be read is absent, not zero."""
        self.assertIsNone(prose.count("many"))
        self.assertIsNone(prose.count(""))
        self.assertEqual(prose.count("1 (acme-api, slice 1)."), 1)

    def test_a_record_with_no_h1_is_addressed_by_its_filename(self) -> None:
        self.assertEqual(prose.title("no heading at all\n", "docs/adr/ADR-7-thing.md"),
                         "ADR-7-thing")

    def test_a_status_stated_twice_is_read_once_and_the_first_wins(self) -> None:
        text = "# x\n\n**Status:** accepted\n\nLater on: status: superseded\n"
        self.assertEqual(prose.word(prose.fields(text)["status"]), "accepted")

    def test_a_field_name_keeps_its_underscore(self) -> None:
        """Stripping `_` as emphasis would silently delete the one field the founder's
        decision of 2026-09-17 made mandatory."""
        self.assertEqual(prose.fields("verified_against: abc123\n")["verified_against"],
                         "abc123")

    def test_a_blank_verified_against_is_not_a_verification(self) -> None:
        self.assertEqual(prose.fields("verified_against:    \n").get("verified_against", ""),
                         "")


class AMapNamesOnlyWhatTheRepositoryHas(Built):
    def test_a_named_document_absent_from_head_gets_no_row(self) -> None:
        """A path a human typed and the repository does not carry is not a source: the
        pack would otherwise hand over a row with the sha256 of empty bytes."""
        root = self.repo({"CONTEXT.md": MAP,
                          "docs/adr/ADR-014-navigator.md": "# ADR-014\n\n- Status: accepted\n",
                          "scripts/run.sh": "#!/bin/sh\n"})
        ids = self.ids(self.pack(root, "pricing")["declared"])
        self.assertIn("docs/adr/ADR-014-navigator.md", ids)
        self.assertNotIn("docs/adr/ADR-999-ghost.md", ids)
        self.assertNotIn("scripts/run.sh", ids, "a shell script is not a declared document")

    def test_the_document_the_adr_scan_already_carries_is_stamped_not_duplicated(self) -> None:
        root = self.repo({"CONTEXT.md": MAP,
                          "docs/adr/ADR-014-navigator.md": "# ADR-014\n\n- Status: accepted\n"})
        rows = [r for r in self.pack(root, "pricing")["declared"]
                if r["source_id"] == "docs/adr/ADR-014-navigator.md"]
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual((rows[0]["kind"], rows[0]["area"]), ("adr", "pricing"))


class BytesNoCalendarOrCodecCanRead(Built):
    def test_an_adr_that_is_not_utf8_still_reaches_the_agent(self) -> None:
        """A byte sequence no codec can read is not a reason to lose the record."""
        root = self.repo({"CONTEXT.md": "# prose\n",
                          "docs/adr/ADR-1-x.md": b"# ADR-1 \xff\xfe\n\n- Status: accepted\n"})
        row = [r for r in self.pack(root)["declared"] if r["kind"] == "adr"]
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0]["state"], "accepted")
        self.assertEqual(row[0]["source_hash"],
                         cbb._source_hash(root, root / "docs/adr/ADR-1-x.md", at_head=True))

    def test_a_typed_repository_grows_no_unknown_key(self) -> None:
        """T2's landed contract: a healthy sealed pack carries no unknown layer at all,
        and this layer must not be the one that creates the key."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cbb._fixture(root)
            self.assertNotIn("unknown", contextpack.resolve(root, "", [], degrade=True))


if __name__ == "__main__":
    unittest.main()
