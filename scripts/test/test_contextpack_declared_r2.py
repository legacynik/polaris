"""L2-T4 (#403) round 2 — what the critic and the breaker of PR #423 found, as tests.

Round 1 built the layer. Round 1 also trusted `_placed` with no guards, named ADRs by one
spelling, read `verified_against` as a string, and let a code fence decide an ADR's status.
Eight findings, each one below, each with the input that produced it.

**(R1) `_placed` had none of the guards the rest of the layer has.** A path a prose section
names went straight to a `declared` row, so an EMPTY ADR already degraded to `unknown` came
back as an authority, a TYPED `ARCHITECTURE.md` got a declared row the sealed layer owns, and
a path under `fixtures/` entered as a decision. The fix is one rule, not three patches: the
area map STAMPS a source this layer already produced a row for, whatever that row's layer,
and refuses a path another layer owns or a path no layer may own.

**(R1, second half) one source, one row — for real this time.** Round 1 left a prose
`CONTEXT.md` with two rows, T2's `unknown` and this layer's `declared`, and argued the two
claims were different. They are not: the layer that can read the document supersedes the
layer that could only say it was unreadable. The declared row now REPLACES the unknown one,
which is what plan section 5 means by *la triade entra come dichiarata*.

**(R2) a committed symlink crashed the resolver.** `cbb._source_bytes` resolves a path before
taking it relative to the root, so a link pointing outside the repository raised `ValueError`
and the CLI died with a traceback where the contract says exit 2 or a row. Symlinks are no
longer sources: we cannot vouch for bytes we would have to follow out of the tree, and the
ones in a decision folder get an `unknown` row rather than vanishing.

**(R3) `ADR-*.md` is one spelling of several.** Two repositories of this vault keep 28 and 10
prose decision records, none of them named `ADR-*`: they are `docs/architecture/decisions/
0001-x.md` and `_project_specs/adr/0007-y.md`. A numeric form is accepted, `references/`,
`wiki/` and `.worktrees/` are never authorities, and a `.md` in a folder whose NAME says
decisions that matches no form is counted in one `unknown` row instead of disappearing.

**(R4) the acceptance criterion wanted the triad row unconditionally.** Round 1 emitted it
only when the document named another document in backticks, and the real prose `CONTEXT.md`
of a product repository has 179 lines and no backticks — so it came out `unknown` only, which
is exactly what the adversarial AC of #403 forbids. Every non-empty prose triad document is
now a declared row; the map is what the row CARRIES, not what earns it.

**(R5) `verified_against` was a presence check.** `deadbeef`, `HEAD` and a bare path all
counted as "somebody verified this lesson", which is the opposite of the founder's answer to
question 2. It must resolve to a commit in this repository.

**(R6) a code fence could set an ADR's status.** `Status: accepted` inside a fenced example
won over `**Status:** rejected` in the prose below it, so a rejected record entered as
accepted. Fenced lines state nothing.

**(R7) two lessons with the same first 60 characters collided.** Same `source_id` and same
`source_hash` — the hash was of the whole ledger — so one of them was unreachable and the
pack deduplicated it in silence. The id carries the block's index and the hash is the
block's, which is also what lets a receipt say WHICH lesson was delivered.

**(R8) `Recurrence: many` answered 0.** A count nobody stated is not zero; the field is
absent unless an integer was stated.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import contextpack  # noqa: E402
import contextpack_prose as prose  # noqa: E402

TYPED = {"schema_version": 1, "document_type": "architecture", "status": "active",
         "owner": "role:cto", "workspace": "acme", "repo": "acme-api",
         "snapshot_ref": "scope-sha256:0", "snapshot_scope": ["src"],
         "review_trigger": ["never"]}
ADR = "# ADR-014 — the navigator\n\n- Status: accepted\n"
# An absolute path that exists on no machine. A symlink row is about WHERE a link points,
# so the target never has to be real — and a synthetic one keeps this fixture out of
# `gate_purity.allow`, a list that may only shrink (S6 of the #423 breaker, round 2).
OUTSIDE = "/nonexistent/definitely-not-here"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=root, check=True, capture_output=True, text=True)
    return done.stdout.strip()


class Built(unittest.TestCase):
    def build(self, files: dict[str, str]) -> Path:
        root = Path(tempfile.mkdtemp(prefix="declared-r2-")).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        self.write(root, files)
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the repository under test")
        return root

    def write(self, root: Path, files: dict[str, str]) -> None:
        for name, body in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(body, encoding="utf-8")

    def rows(self, root: Path, *areas: str) -> list[dict]:
        """Every row the pack hands over, wherever the resolver files it."""
        pack = contextpack.resolve(root, "", list(areas), degrade=True)
        lists = [value for value in pack.values() if isinstance(value, list)]
        lists += [area.get("documents", []) for area in pack.get("areas") or []]
        return [row for value in lists for row in value
                if isinstance(row, dict) and "source_id" in row]

    def only(self, root: Path, source: str, *areas: str) -> dict:
        found = [row for row in self.rows(root, *areas) if row["source_id"] == source]
        self.assertEqual(len(found), 1, f"{source} appears {len(found)} times: {found}")
        return found[0]

    def absent(self, root: Path, source: str, *areas: str) -> None:
        found = [row for row in self.rows(root, *areas) if row["source_id"] == source]
        self.assertEqual(found, [], f"{source} reached the agent: {found}")


# --- R1: the area map stamps, it never promotes ------------------------------------


class TheMapStampsAndNeverPromotes(Built):
    def named(self, extra: dict[str, str], ref: str) -> Path:
        return self.build(dict({"CONTEXT.md": f"# acme-api\n\n## Pricing\n\n`{ref}`\n"}, **extra))

    def test_an_empty_adr_the_map_names_stays_unknown_and_gets_exactly_one_row(self) -> None:
        """(a) The empty record was already degraded; the map must not undo that."""
        root = self.named({"docs/adr/ADR-016-void.md": "\n"}, "docs/adr/ADR-016-void.md")
        row = self.only(root, "docs/adr/ADR-016-void.md", "pricing")
        self.assertEqual(row["layer"], "unknown")
        self.assertEqual(row["reason"].split(":")[0], "empty")
        self.assertEqual(row["area"], "pricing", "the map still says which area named it")

    def test_a_typed_live_document_the_map_names_gets_no_declared_row(self) -> None:
        """(b) `ARCHITECTURE.md` belongs to the sealed layer or to L2-T2, never here."""
        body = "---\n" + json.dumps(TYPED, indent=2) + "\n---\n\n# the architecture\n"
        root = self.named({"ARCHITECTURE.md": body}, "ARCHITECTURE.md")
        self.assertEqual([r["layer"] for r in self.rows(root, "pricing")
                          if r["source_id"] == "ARCHITECTURE.md"], ["unknown"])

    def test_a_path_no_layer_may_own_stays_out_even_when_the_map_names_it(self) -> None:
        """(c) A test input is not an authority because a human linked it."""
        root = self.named({"scripts/test/fixtures/x/adr/ADR-1-a.md": ADR,
                           "docs/_archived/adr/ADR-2-b.md": ADR},
                          "scripts/test/fixtures/x/adr/ADR-1-a.md")
        self.absent(root, "scripts/test/fixtures/x/adr/ADR-1-a.md", "pricing")
        self.absent(root, "docs/_archived/adr/ADR-2-b.md", "pricing")

    def test_a_record_the_scan_already_carries_is_stamped_once(self) -> None:
        root = self.named({"docs/adr/ADR-014-x.md": ADR}, "docs/adr/ADR-014-x.md")
        row = self.only(root, "docs/adr/ADR-014-x.md", "pricing")
        self.assertEqual((row["layer"], row["kind"], row["area"]), ("declared", "adr", "pricing"))


class OneSourceOneRow(Built):
    def test_a_prose_triad_document_leaves_the_unknown_layer_when_it_is_declared(self) -> None:
        """The layer that READ the document supersedes the layer that could not."""
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n", "src": "x\n"})
        row = self.only(root, "CONTEXT.md")
        self.assertEqual(row["layer"], "declared")
        self.assertEqual(row["source_hash"], sha256((root / "CONTEXT.md").read_bytes()).hexdigest())

    def test_the_other_two_authorities_still_have_their_unknown_row(self) -> None:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n", "src": "x\n"})
        pack = contextpack.resolve(root, "", [], degrade=True)
        self.assertEqual(sorted(r["source_id"] for r in pack["unknown"]),
                         ["ARCHITECTURE.md", "DOMAIN.md", "decisions/"])


# --- R2: a symlink is not a source -------------------------------------------------


class ASymlinkIsNeverASource(Built):
    def linked(self, target: str) -> Path:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n",
                           "docs/adr/ADR-1-real.md": ADR})
        (root / "docs" / "adr" / "ADR-400-symlink.md").symlink_to(target)
        git(root, "add", "-A")
        git(root, "commit", "-qm", "a committed symlink")
        return root

    def test_a_link_out_of_the_tree_is_a_row_and_not_a_traceback(self) -> None:
        """The crash the breaker of #423 found: exit 1 with `ValueError` from
        `Path.relative_to`, where the contract is exit 2 with a code, or a row. The target
        is synthetic (S6): it names no real file and reproduces the same row."""
        root = self.linked(OUTSIDE)
        row = self.only(root, "docs/adr/ADR-400-symlink.md")
        self.assertEqual((row["layer"], row["reason"].split(":")[0]), ("unknown", "symlink"))

    def test_the_real_record_beside_it_still_arrives(self) -> None:
        self.assertEqual(self.only(self.linked(OUTSIDE),
                                   "docs/adr/ADR-1-real.md")["layer"], "declared")

    def test_a_link_inside_the_tree_is_refused_on_the_same_grounds(self) -> None:
        """Following it would hash a file the row does not name — the same defect the
        flight layer fixed by hashing WHERE a link points instead of what is there."""
        row = self.only(self.linked("ADR-1-real.md"), "docs/adr/ADR-400-symlink.md")
        self.assertEqual(row["layer"], "unknown")

    def test_the_cli_exits_zero_over_a_repository_full_of_them(self) -> None:
        root = self.linked(OUTSIDE)
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "contextpack.py"),
                               "resolve", "--root", str(root)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


# --- R3: one spelling of several ---------------------------------------------------


class ARecordIsNotOnlyNamedAdr(Built):
    def test_the_numeric_form_of_two_real_repositories_is_a_record(self) -> None:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n",
                           "docs/architecture/decisions/0001-pick-a-queue.md":
                               "# 1. Pick a queue\n\n- Status: accepted\n",
                           "_project_specs/adr/0007-retry.md":
                               "# 7. Retry\n\n- Status: superseded\n"})
        self.assertEqual(self.only(root, "docs/architecture/decisions/0001-pick-a-queue.md"
                                   )["state"], "accepted")
        self.assertEqual(self.only(root, "_project_specs/adr/0007-retry.md")["state"],
                         "superseded")

    def test_a_record_in_a_decisions_folder_that_fits_no_form_is_counted(self) -> None:
        """Not silence: a folder whose NAME says decisions is answered for in full."""
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n",
                           "docs/adr/ADR-1-a.md": ADR,
                           "docs/adr/some-old-note.md": "# a note\n",
                           "docs/adr/another-one.md": "# another\n"})
        row = self.only(root, "adr:unnameable")
        self.assertEqual((row["layer"], row["reason"].split(":")[0]), ("unknown", "unnameable"))
        self.assertIn("2", row["reason"])

    def test_an_architecture_folder_is_not_a_decisions_folder(self) -> None:
        """`architecture` holds all sorts of documents, so only an explicitly named record
        is one and nothing there is ever reported as missed — otherwise a skill directory
        called `architecture` would put an `unknown` row in a healthy sealed pack."""
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n",
                           "skills/architecture/SKILL.md": "# a skill\n",
                           "skills/architecture/EVAL-REPORT.md": "# a report\n"})
        self.absent(root, "adr:unnameable")
        self.absent(root, "skills/architecture/SKILL.md")

    def test_a_pinned_external_corpus_is_never_an_authority(self) -> None:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n",
                           "references/bmad/adr/ADR-9-theirs.md": ADR,
                           "wiki/decisions/a-page.md": "# a page\n",
                           ".worktrees/other/docs/adr/ADR-8-theirs.md": ADR})
        for source in ("references/bmad/adr/ADR-9-theirs.md",
                       ".worktrees/other/docs/adr/ADR-8-theirs.md", "adr:unnameable"):
            self.absent(root, source)


# --- R4: the triad row is unconditional --------------------------------------------


class EveryProseTriadDocumentIsDeclared(Built):
    def test_a_prose_context_with_no_backtick_at_all_is_still_declared(self) -> None:
        """The shape of a real product repository: 179 lines of prose, no code span."""
        body = "# acme-api\n\n" + "Prose that names nothing.\n" * 40
        root = self.build({"CONTEXT.md": body, "src": "x\n"})
        row = self.only(root, "CONTEXT.md")
        self.assertEqual((row["layer"], row["kind"]), ("declared", "context"))
        self.assertEqual(row["source_hash"], sha256(body.encode()).hexdigest())

    def test_an_empty_prose_triad_document_is_still_not_declared(self) -> None:
        root = self.build({"CONTEXT.md": "\n", "src": "x\n"})
        self.assertEqual([r["layer"] for r in self.rows(root)
                          if r["source_id"] == "CONTEXT.md"], ["unknown"])

    def test_the_map_it_carries_is_still_read_when_it_has_one(self) -> None:
        root = self.build({"CONTEXT.md": "# acme-api\n\n## Pricing\n\n`docs/adr/ADR-1-a.md`\n",
                           "docs/adr/ADR-1-a.md": ADR})
        self.assertEqual(self.only(root, "docs/adr/ADR-1-a.md", "pricing")["area"], "pricing")


# --- R5, R7, R8: the lesson ---------------------------------------------------------


class ALessonIsVerifiedAgainstACommitOrItIsNot(Built):
    def ledger(self, value: str, extra: str = "") -> Path:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n", "src": "x\n"})
        self.write(root, {"lessons.md": "# Lessons\n\n"
                          "## 2026-09-01 — Reserve the id before writing it\n"
                          "area: pricing\nrecurrence: 3\n"
                          f"verified_against: {value}\n\nTwo panels spent it.\n{extra}"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        return root

    def lesson_rows(self, root: Path) -> list[dict]:
        return [row for row in self.rows(root, "pricing") if row.get("kind") == "lesson"]

    def test_a_sha_that_resolves_to_no_commit_is_not_a_verification(self) -> None:
        rows = self.lesson_rows(self.ledger("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"))
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual((rows[0]["layer"], rows[0]["reason"].split(":")[0]),
                         ("unknown", "unresolved"))

    def test_a_path_is_not_a_commit_either(self) -> None:
        rows = self.lesson_rows(self.ledger(OUTSIDE))
        self.assertEqual([r["layer"] for r in rows], ["unknown"])

    def test_a_moving_name_is_not_a_commit_either(self) -> None:
        """`HEAD` resolves today and means something else tomorrow, so it verifies nothing."""
        self.assertEqual([r["layer"] for r in self.lesson_rows(self.ledger("HEAD"))],
                         ["unknown"])

    def test_a_real_commit_of_this_repository_is_a_verification(self) -> None:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n", "src": "x\n"})
        sha = git(root, "rev-parse", "HEAD")
        self.write(root, {"lessons.md": "# Lessons\n\n"
                          "## 2026-09-01 — Reserve the id before writing it\n"
                          f"area: pricing\nrecurrence: 3\nverified_against: {sha}\n\nBody.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        rows = self.lesson_rows(root)
        self.assertEqual([r["layer"] for r in rows], ["declared"])
        self.assertEqual((rows[0]["recurrence"], rows[0]["verified_against"]), (3, sha))

    def test_two_lessons_with_the_same_first_sixty_characters_are_two_rows(self) -> None:
        """R7: one id and one hash for two blocks made one of them unreachable."""
        head = "## 2026-09-01 — A title long enough to collide on its first sixty chars"
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n", "src": "x\n"})
        self.write(root, {"lessons.md": f"# Lessons\n\n{head} (one)\narea: pricing\n\nFirst.\n"
                                        f"\n{head} (two)\narea: pricing\n\nSecond.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "two lessons")
        rows = self.lesson_rows(root)
        self.assertEqual(len(rows), 2, rows)
        self.assertEqual(len({r["source_id"] for r in rows}), 2, "one id for two lessons")
        self.assertEqual(len({r["source_hash"] for r in rows}), 2, "one hash for two lessons")

    def test_the_hash_is_the_block_and_not_the_whole_ledger(self) -> None:
        root = self.ledger("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
        whole = sha256((root / "lessons.md").read_bytes()).hexdigest()
        self.assertNotEqual(self.lesson_rows(root)[0]["source_hash"], whole)

    def test_a_recurrence_that_is_not_an_integer_is_not_a_count(self) -> None:
        """R8: `many` answered 0, which is a number nobody wrote."""
        self.assertIsNone(prose.count("many"))
        self.assertIsNone(prose.count(""))
        self.assertEqual(prose.count("3 (acme-api, slice 1)."), 3)

    def test_a_lesson_with_an_unreadable_recurrence_claims_none(self) -> None:
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n", "src": "x\n"})
        sha = git(root, "rev-parse", "HEAD")
        self.write(root, {"lessons.md": "# Lessons\n\n## 2026-09-01 — A lesson\n"
                          f"area: pricing\nrecurrence: many\nverified_against: {sha}\n\nBody.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        self.assertNotIn("recurrence", self.lesson_rows(root)[0])


# --- R6: a fence states nothing -----------------------------------------------------


class AFenceStatesNothing(Built):
    def test_a_status_inside_a_code_fence_does_not_decide_the_record(self) -> None:
        body = ("# ADR-020 — a record that shows an example\n\n"
                "```\nStatus: accepted\n```\n\n**Status:** rejected\n")
        root = self.build({"CONTEXT.md": "# acme-api\n\nProse.\n",
                           "docs/adr/ADR-020-x.md": body})
        self.assertEqual(self.only(root, "docs/adr/ADR-020-x.md")["state"], "rejected")

    def test_the_primitive_says_the_same_on_its_own(self) -> None:
        text = "```\nstatus: accepted\n```\n**Status:** rejected\n"
        self.assertEqual(prose.word(prose.fields(text)["status"]), "rejected")

    def test_a_tilde_fence_counts_too_and_an_unclosed_one_swallows_the_rest(self) -> None:
        self.assertEqual(prose.fields("~~~\nstatus: accepted\n~~~\nstatus: rejected\n"
                                      )["status"], "rejected")
        self.assertEqual(prose.fields("```\nstatus: accepted\n"), {})


if __name__ == "__main__":
    unittest.main()
