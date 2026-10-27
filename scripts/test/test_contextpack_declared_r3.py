"""L2-T4 (#403) round 3 — the seven findings of the critic and breaker on PR #423, round 2.

Round 2 recovered the records `ADR-*.md` missed. It also let a date through where a date is
not a record number, believed the first word of any status line, believed any string that
git could resolve, and put the one row an incident turns on at the front of the queue to be
cut. Seven cases, each with the input that produced it.

**(S1) a date is not a record number.** `^\\d{4}-.*\\.md$` matched
`docs/architecture/2026-06-29-loop-engineer-design.md`, so five design notes entered one
product repository as decisions and its count went from 27 to 32 — the acceptance criterion
of #403 broken by the fix for R3. The numeric form is now refused in `architecture`, which
holds all sorts of documents, and a `\\d{4}-\\d{2}-` prefix is refused as a sequence number
anywhere. A folder whose NAME says decisions keeps answering in full: everything in `adr`,
`adrs` or `decisions` is a record, date-named included, because that is what those folders
are for — and this vault's own `adr/` names all seven of its prose ADRs by date.

**(S2) the first word of a status line is not a status.** `**Status:** No new contract
introduced by the Fase-1 refactor` answered `state: no`, an authority nobody wrote. Only a
state the lifecycle uses is a state; everything else is `UNKNOWN`, which is what the row
said before round 2 taught it to guess.

**(S3) `verified_against` was a denylist of three strings.** `main`, an annotated tag and a
blob's own sha all passed the shape check and two of them resolved, so the founder's answer
to question 2 was still satisfied by something that is not a verification. The value must
LOOK like an object name — 7 to 40 hex characters — and then resolve to a COMMIT.

**(S4) a comment is a fence too.** `<!--\\nStatus: accepted\\n-->` beat `**Status:** rejected`
below it, which is the same defect as R6 through the other syntax Markdown hides text in.

**(S5) the budget cut the one row the incidents turn on.** `receipt.fit` pops the TAIL of
`pack["declared"]`, and round 2 built that list with the records first and the triad last:
on a 32-record repository at `--budget 3000` the first row to fall was `CONTEXT.md` — the
row that closes INC-02 and INC-07 — while 26 ADRs stayed. Survival order is now the order
of the list: the triad and the area's lessons first, the documents its map names next, the
repo-wide records last, so what falls is the thing there are thirty of.

**(S6) the fixture stops naming a real machine path.** `/etc/passwd` was a declared
impurity; a synthetic absolute target reproduces the same `unknown`/`symlink` row, so the
line comes back out of `gate_purity.allow` — the list may only shrink.

**(S7) two modules were coupled by a piece of prose.** `contextpack_unknown` decided a
document was the declared layer's by reading the `no_frontmatter` token out of a reason
STRING, while `contextpack_declared` decided the same thing from its own second read. Two
answers to one question, and with the declared layer inert `CONTEXT.md` would have vanished
from both. There is one predicate now, `contextpack_prose.is_readable_prose`, and both call
it.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_context_backbone as cbb  # noqa: E402
import contextpack  # noqa: E402
import contextpack_declared as declared  # noqa: E402
import contextpack_prose as prose  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_unknown as unknown  # noqa: E402

PROSE = "# acme-api\n\nProse, no frontmatter.\n"
RECORD = "# ADR-{n} — a record\n\n- Status: accepted\n"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=root, check=True, capture_output=True, text=True)
    return done.stdout.strip()


class Built(unittest.TestCase):
    def build(self, files: dict[str, str]) -> Path:
        root = Path(tempfile.mkdtemp(prefix="declared-r3-")).resolve()
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

    def declared_rows(self, root: Path, *areas: str) -> list[dict]:
        return contextpack.resolve(root, "", list(areas), degrade=True)["declared"]

    def ids(self, rows: list[dict]) -> list[str]:
        return [row["source_id"] for row in rows]

    def one(self, root: Path, source: str, *areas: str) -> dict:
        pack = contextpack.resolve(root, "", list(areas), degrade=True)
        found = [row for key in ("declared", "unknown") for row in pack.get(key) or []
                 if row["source_id"] == source]
        self.assertEqual(len(found), 1, f"{source} appears {len(found)} times: {found}")
        return found[0]


class ADateIsNotARecordNumber(Built):
    def test_a_dated_design_note_in_an_architecture_folder_is_not_a_decision(self) -> None:
        """S1: five of these turned one repository's 27 records into 32."""
        root = self.build({"CONTEXT.md": PROSE,
                           "docs/architecture/2026-06-29-loop-engineer-design.md":
                               "# Loop engineer — design\n\nA design note.\n"})
        self.assertEqual([r for r in self.declared_rows(root) if r["kind"] == "adr"], [])

    def test_and_it_is_not_reported_as_a_record_the_pack_could_not_name(self) -> None:
        """`architecture` is not a decisions folder, so nothing there is a missed record."""
        root = self.build({"CONTEXT.md": PROSE,
                           "docs/architecture/2026-06-29-loop-engineer-design.md": "# x\n"})
        self.assertNotIn("adr:unnameable", self.ids(self.declared_rows(root)))
        pack = contextpack.resolve(root, "", [], degrade=True)
        self.assertEqual([r for r in pack["unknown"] if r["source_id"] == "adr:unnameable"], [])

    def test_the_sequence_form_in_a_decisions_folder_is_still_a_record(self) -> None:
        root = self.build({"CONTEXT.md": PROSE,
                           "docs/architecture/decisions/0001-pick-a-queue.md":
                               "# 1. Pick a queue\n\n- Status: accepted\n"})
        self.assertEqual(self.one(root, "docs/architecture/decisions/0001-pick-a-queue.md"
                                  )["state"], "accepted")

    def test_a_date_named_record_in_a_folder_that_says_decisions_is_still_a_record(self) -> None:
        """This vault names all seven of its own prose ADRs by date under `adr/`. A folder
        whose NAME says decisions is answered for in full, so the date form is a record
        THERE and refused in `architecture` — that is the whole of the S1 boundary."""
        root = self.build({"CONTEXT.md": PROSE,
                           "adr/2026-08-13-adr-books-as-reference.md":
                               "# ADR — books as reference\n\n- Status: superseded\n"})
        self.assertEqual(self.one(root, "adr/2026-08-13-adr-books-as-reference.md")["state"],
                         "superseded")

    def test_a_sequence_number_outside_a_decisions_folder_is_not_a_record(self) -> None:
        root = self.build({"CONTEXT.md": PROSE, "docs/architecture/0001-a-note.md": "# n\n"})
        self.assertEqual([r for r in self.declared_rows(root) if r["kind"] == "adr"], [])


class OnlyAStateIsAState(Built):
    def test_a_status_line_that_states_no_state_answers_unknown(self) -> None:
        """S2: `No new contract introduced by the Fase-1 refactor` answered `no`."""
        root = self.build({"CONTEXT.md": PROSE, "docs/adr/ADR-1-x.md":
                           "# ADR-1\n\n**Status:** No new contract introduced by the "
                           "Fase-1 refactor. Documents 3 EXISTING seams.\n"})
        self.assertEqual(self.one(root, "docs/adr/ADR-1-x.md")["state"], "UNKNOWN")

    def test_the_states_the_lifecycle_uses_are_read_as_written(self) -> None:
        for stated, want in (("accepted", "accepted"), ("**Approved (go-ahead)**", "approved"),
                             ("superseded", "superseded"), ("Rejected.", "rejected"),
                             ("Active — supersedes #1181", "active"), ("proposed", "proposed")):
            self.assertEqual(prose.word(stated), want, stated)

    def test_anything_else_is_unknown_and_never_a_word_from_the_sentence(self) -> None:
        for stated in ("No new contract introduced", "Consensus-approved planning decision",
                       "unclear", ""):
            self.assertEqual(prose.word(stated), "UNKNOWN", stated)


class VerifiedAgainstMeansACommit(Built):
    def ledger(self, value: str) -> Path:
        root = self.build({"CONTEXT.md": PROSE, "src": "x\n"})
        self.write(root, {"lessons.md": "# Lessons\n\n## 2026-09-01 — A lesson\n"
                          f"area: pricing\nrecurrence: 3\nverified_against: {value}\n\nB.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        return root

    def lesson(self, root: Path) -> dict:
        pack = contextpack.resolve(root, "", ["pricing"], degrade=True)
        found = [row for key in ("declared", "unknown") for row in pack.get(key) or []
                 if row.get("kind") == "lesson"]
        self.assertEqual(len(found), 1, found)
        return found[0]

    def test_a_branch_name_verifies_nothing(self) -> None:
        """S3: `main` resolves in every repository and moves with every commit."""
        self.assertEqual(self.lesson(self.ledger("main"))["layer"], "unknown")

    def test_an_annotated_tag_verifies_nothing_either(self) -> None:
        root = self.build({"CONTEXT.md": PROSE, "src": "x\n"})
        git(root, "tag", "-a", "v1", "-m", "a tag")
        self.write(root, {"lessons.md": "# Lessons\n\n## 2026-09-01 — A lesson\n"
                          "area: pricing\nverified_against: v1\n\nB.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        self.assertEqual(self.lesson(root)["layer"], "unknown")

    def test_a_blob_sha_looks_right_and_is_not_a_commit(self) -> None:
        """The case that proves `^{commit}` earns its place: 40 hex that git resolves."""
        root = self.build({"CONTEXT.md": PROSE, "src": "x\n"})
        blob = git(root, "rev-parse", "HEAD:src")
        self.write(root, {"lessons.md": "# Lessons\n\n## 2026-09-01 — A lesson\n"
                          f"area: pricing\nverified_against: {blob}\n\nB.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        row = self.lesson(root)
        self.assertEqual((row["layer"], row["reason"].split(":")[0]), ("unknown", "unresolved"))

    def test_an_abbreviated_commit_sha_is_a_verification(self) -> None:
        root = self.build({"CONTEXT.md": PROSE, "src": "x\n"})
        short = git(root, "rev-parse", "--short=7", "HEAD")
        self.write(root, {"lessons.md": "# Lessons\n\n## 2026-09-01 — A lesson\n"
                          f"area: pricing\nverified_against: {short}\n\nB.\n"})
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        self.assertEqual(self.lesson(root)["layer"], "declared")


class AnHtmlCommentHidesNothing(Built):
    def test_a_status_inside_a_comment_does_not_decide_the_record(self) -> None:
        """S4: the same defect as R6, through the other syntax Markdown hides text in."""
        root = self.build({"CONTEXT.md": PROSE, "docs/adr/ADR-1-x.md":
                           "# ADR-1\n\n<!--\nStatus: accepted\n-->\n\n**Status:** rejected\n"})
        self.assertEqual(self.one(root, "docs/adr/ADR-1-x.md")["state"], "rejected")

    def test_a_one_line_comment_is_skipped_without_swallowing_the_document(self) -> None:
        text = "<!-- Status: accepted -->\n**Status:** rejected\n"
        self.assertEqual(prose.fields(text)["status"], "rejected")

    def test_an_unclosed_comment_swallows_the_rest_as_a_reader_would(self) -> None:
        self.assertEqual(prose.fields("<!--\nstatus: accepted\n"), {})

    def test_a_comment_inside_a_fence_still_leaves_the_prose_readable(self) -> None:
        text = "```\n<!-- status: accepted -->\n```\nstatus: rejected\n"
        self.assertEqual(prose.fields(text)["status"], "rejected")


class TheBudgetCutsWhatThereAreThirtyOf(Built):
    def crowded(self, records: int) -> Path:
        files = {"CONTEXT.md": "# acme-api\n\n## Pricing\n\n`docs/research/spec.md`\n",
                 "docs/research/spec.md": "# the specification\n\nProse.\n"}
        files.update({f"docs/adr/ADR-{i:03d}-x.md": RECORD.format(n=i) for i in range(30)})
        return self.build(files)

    def test_the_first_rows_to_fall_are_the_repo_wide_records(self) -> None:
        """S5: at a tight ceiling the row that closed INC-02 and INC-07 fell FIRST while
        twenty-six records stayed, because `fit` pops the tail and the triad was the tail."""
        pack = contextpack.resolve(self.crowded(30), "", ["pricing"], degrade=True)
        self.assertGreater(len([r for r in pack["declared"] if r["kind"] == "adr"]), 20)
        cuts = receipt.fit(pack, 900)
        self.assertTrue(cuts, "nothing was cut; the case proves nothing")
        self.assertEqual({c["kind"] for c in cuts}, {"adr"}, "a record is what may fall")
        self.assertIn("CONTEXT.md", self.ids(pack["declared"]))

    def test_the_area_document_outlives_the_records_too(self) -> None:
        pack = contextpack.resolve(self.crowded(30), "", ["pricing"], degrade=True)
        receipt.fit(pack, 900)
        self.assertIn("docs/research/spec.md", self.ids(pack["declared"]))

    def test_the_survival_order_is_the_order_of_the_list(self) -> None:
        rows = contextpack.resolve(self.crowded(30), "", ["pricing"], degrade=True)["declared"]
        kinds = [row["kind"] for row in rows]
        self.assertEqual(kinds[0], "context", kinds[:4])
        self.assertEqual(kinds[-1], "adr", kinds[-4:])


class OnePredicateNotTwoReadings(Built):
    def test_both_layers_ask_the_same_question_of_the_same_document(self) -> None:
        """S7: the two modules used to answer it separately, one of them off a reason
        string, so they could drift into a gap or a duplicate."""
        root = self.build({"CONTEXT.md": PROSE, "ARCHITECTURE.md": "\n", "src": "x\n"})
        self.assertTrue(prose.is_readable_prose(root, "CONTEXT.md"))
        self.assertFalse(prose.is_readable_prose(root, "ARCHITECTURE.md"), "empty")
        self.assertFalse(prose.is_readable_prose(root, "DOMAIN.md"), "absent")

    def test_the_unknown_layer_omits_exactly_what_the_predicate_accepts(self) -> None:
        root = self.build({"CONTEXT.md": PROSE, "ARCHITECTURE.md": "\n", "src": "x\n"})
        named = {row["source_id"] for row in unknown.rows(root)}
        accepted = {name for name in cbb.LIVE_DOCS if prose.is_readable_prose(root, name)}
        self.assertEqual(accepted & named, set(), f"both layers claim {accepted & named}")
        self.assertEqual(accepted, {"CONTEXT.md"})

    def test_and_the_declared_layer_emits_exactly_those(self) -> None:
        root = self.build({"CONTEXT.md": PROSE, "ARCHITECTURE.md": "\n", "src": "x\n"})
        emitted = {row["source_id"] for row in declared.rows(root, [])[0]
                   if row["kind"] in cbb.LIVE_DOCS.values()}
        self.assertEqual(emitted, {name for name in cbb.LIVE_DOCS
                                   if prose.is_readable_prose(root, name)})

    def test_no_live_document_is_lost_between_them(self) -> None:
        root = self.build({"CONTEXT.md": PROSE, "ARCHITECTURE.md": "\n", "src": "x\n"})
        pack = contextpack.resolve(root, "", [], degrade=True)
        seen = {row["source_id"] for key in ("declared", "unknown") for row in pack[key]}
        self.assertTrue(set(cbb.LIVE_DOCS) <= seen, f"lost {set(cbb.LIVE_DOCS) - seen}")


if __name__ == "__main__":
    unittest.main()
