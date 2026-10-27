"""L2-T4 (#403) — the declared layer: prose that carries authority and cannot prove it.

The sealed layer answers what HEAD proves; the flight layer what a repository is doing.
Neither can answer for the thing the product repositories are actually made of: twenty-seven
prose ADRs in one, sixty-five in another, a `CONTEXT.md` a human wrote for humans. Before
this layer they were `FRONTMATTER_MISSING` and then, after L2-T2, four rows saying "nothing
typed to seal" — true, and not the same as handing the agent the decision it is about to
re-propose (INC-02, INC-07 of polaris-os#63).

What this file holds down, case by case:

- **A prose ADR is one declared row**, with the title it carries, the status it states, the
  sha256 of the bytes at HEAD and `freshness: UNKNOWN` — never `CURRENT`, because nothing
  proved it against the code, and never `sealed`.
- **`Status:` is read as written, not as hoped.** The real corpus writes `**Status:** Accepted`,
  `Status: **Approved (founder go-ahead …)**` and `status: superseded` inside frontmatter. A
  superseded ADR must say `superseded` and must not say `accepted` anywhere in its row.
- **An ADR is an ADR by where it lives** (plan section 5: `docs/architecture/ADR-*`,
  `docs/adr/*`), and a test fixture is never an authority. Without that, resolving the vault
  would hand the agent this suite's own `ADR-014` fixture as a decision governing the vault.
- **The prose triad enters as declared, and only when it declares something.** A `CONTEXT.md`
  whose whole content is a title says nothing its `unknown` row does not already say
  (`no_frontmatter: readable prose: nothing typed to seal`), so it gets no second row — which
  is also the contract `test_contextpack_budget.py` pins: a prose repository has four rows,
  none of them cuttable. A `CONTEXT.md` that names documents per section is an area map, and
  that map is the row's payload.
- **A lesson enters only once somebody verified it** (founder decision 2026-09-17, question 2
  of the lifecycle plan; INC-14 is the reason). With `verified_against` it is a row carrying
  `recurrence`; without, it is an `unknown` row saying so — counted, never silent.
- **The seal does not move.** `attach` runs after `contextpack_seal.seal`, so `pack_seal`
  keeps meaning "what the commit carries".

Every field is emitted only by whoever can claim it, the convention L2-T2 fixed: `state` on an
ADR, `recurrence` and `verified_against` on a lesson, `area` where an area map placed it. An
absent field is unclaimed, not forgotten.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import contextpack  # noqa: E402

SECTION_4 = ("layer", "kind", "source_id", "path", "freshness", "reason", "source_hash")
ADR = """# ADR-014 — The pricing navigator walks the price list

**Status:** Accepted
**Date:** 2026-08-20

The navigator is the single way to walk the price list.
"""
MAP = """# acme-api — context

## Pricing

The decision lives in `docs/adr/ADR-014-navigator.md`.

## Scheduling

The specification is `docs/research/scheduler.md`.
"""
LESSONS = """# Lessons ledger

## 2026-09-01 — Reserve the id on origin/main before writing it
area: pricing
recurrence: 3
verified_against: {sha}

Two panels spent the same number.

## 2026-09-02 — Never trust a walk somebody re-derived
area: pricing
recurrence: 1

Nobody has checked this one against the code.
"""


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=root, check=True, capture_output=True, text=True)
    return done.stdout.strip()


class Built(unittest.TestCase):
    def repo(self, files: dict[str, str]) -> Path:
        root = Path(tempfile.mkdtemp(prefix="declared-")).resolve()
        self.addCleanup(__import__("shutil").rmtree, root, True)
        for name, body in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(body, encoding="utf-8")
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the repository under test")
        return root

    def rows(self, root: Path, *areas: str) -> list[dict]:
        return contextpack.resolve(root, "", list(areas), degrade=True)["declared"]

    def one(self, root: Path, source_id: str, *areas: str) -> dict:
        found = [row for row in self.rows(root, *areas) if row["source_id"] == source_id]
        self.assertEqual(len(found), 1, f"{source_id} appears {len(found)} times, not once")
        return found[0]

    def digest(self, root: Path, rel: str) -> str:
        return sha256((root / rel).read_bytes()).hexdigest()

    def ledger(self, root: Path) -> Path:
        """`lessons.md` committed with a `verified_against` that RESOLVES in this repository.

        Round 2 (R5 of the #423 breaker): a presence check let `deadbeef` and `HEAD` count
        as a verification, so the value has to be a commit this repository carries — which
        means the ledger can only be written once there is one."""
        (root / "lessons.md").write_text(LESSONS.format(sha=git(root, "rev-parse", "HEAD")),
                                         encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger")
        return root


class TheProseAdrIsADeclaredRow(Built):
    def test_an_adr_in_prose_becomes_one_row_with_title_status_and_hash(self) -> None:
        root = self.repo({"CONTEXT.md": "# prose\n", "docs/adr/ADR-014-navigator.md": ADR})
        row = self.one(root, "docs/adr/ADR-014-navigator.md")
        self.assertEqual(row["layer"], "declared")
        self.assertEqual(row["kind"], "adr")
        self.assertEqual(row["state"], "accepted")
        self.assertEqual(row["freshness"], "UNKNOWN")
        self.assertEqual(row["source_hash"], self.digest(root, "docs/adr/ADR-014-navigator.md"))
        self.assertIn("pricing navigator", row["reason"])

    def test_the_date_it_states_is_the_rows_own_timestamp(self) -> None:
        root = self.repo({"CONTEXT.md": "# prose\n", "docs/adr/ADR-014-navigator.md": ADR})
        self.assertEqual(self.one(root, "docs/adr/ADR-014-navigator.md")["ts"], "2026-08-20")

    def test_a_superseded_adr_says_superseded_and_never_says_accepted(self) -> None:
        """Adversarial AC of #403: `0` times `accepted`, anywhere in the row."""
        body = ADR.replace("**Status:** Accepted", "status: superseded")
        root = self.repo({"CONTEXT.md": "# prose\n", "docs/adr/ADR-014-navigator.md": body})
        row = self.one(root, "docs/adr/ADR-014-navigator.md")
        self.assertEqual(row["state"], "superseded")
        self.assertNotIn("accepted", json.dumps(row).lower())

    def test_an_adr_with_no_status_line_claims_no_status(self) -> None:
        body = "# ADR-015 — A record that never says where it stands\n\nProse.\n"
        root = self.repo({"CONTEXT.md": "# prose\n", "docs/adr/ADR-015-mute.md": body})
        self.assertEqual(self.one(root, "docs/adr/ADR-015-mute.md")["state"], "UNKNOWN")

    def test_an_empty_adr_is_an_unknown_row_and_the_pack_still_exits_zero(self) -> None:
        """Adversarial AC of #403: a file with no content is named, never guessed at."""
        root = self.repo({"CONTEXT.md": "# prose\n", "docs/adr/ADR-016-void.md": "\n"})
        pack = contextpack.resolve(root, "", [], degrade=True)
        self.assertEqual([r for r in pack["declared"] if "ADR-016" in r["source_id"]], [])
        named = [r for r in pack["unknown"] if "ADR-016" in r["source_id"]]
        self.assertEqual(len(named), 1, pack["unknown"])
        self.assertEqual(named[0]["layer"], "unknown")
        self.assertEqual(named[0]["reason"].split(":")[0], "empty")

    def test_a_record_outside_the_declared_locations_is_not_an_authority(self) -> None:
        """Plan section 5 names where an ADR lives. Without this, resolving the vault hands
        the agent this suite's own `ADR-014` fixture as a decision that governs the vault."""
        root = self.repo({"CONTEXT.md": "# prose\n",
                          "skills/archive/ADR-FORMAT.md": "# ADR-FORMAT\n\nA template.\n",
                          "scripts/test/fixtures/no-backbone/adr/ADR-014-x.md": ADR})
        # Round 2 (R4) makes the prose `CONTEXT.md` a declared row in every repository, so
        # the claim is about these two paths and not about the pack being empty.
        self.assertEqual([r["source_id"] for r in self.rows(root) if r["kind"] == "adr"], [])
        self.assertEqual([r["source_id"] for r in self.rows(root)], ["CONTEXT.md"])


class TheProseTriadIsDeclaredNeverSealed(Built):
    def files(self) -> dict[str, str]:
        return {"CONTEXT.md": MAP, "docs/adr/ADR-014-navigator.md": ADR,
                "docs/research/scheduler.md": "# Scheduler redesign\n\nThe specification.\n"}

    def test_a_prose_context_that_declares_documents_gets_a_declared_row(self) -> None:
        """Adversarial AC of #403: `layer: declared`, the file's own sha256, never sealed."""
        root = self.repo(self.files())
        row = self.one(root, "CONTEXT.md", "pricing")
        self.assertEqual(row["layer"], "declared")
        self.assertEqual(row["kind"], "context")
        self.assertEqual(row["source_hash"], self.digest(root, "CONTEXT.md"))
        self.assertEqual(row["freshness"], "UNKNOWN")

    def test_a_prose_context_that_declares_nothing_is_still_a_declared_row(self) -> None:
        """Round 2 (R4 of the #423 breaker): the map is what the row CARRIES, not what
        earns it. The real prose `CONTEXT.md` of a product repository has 179 lines and no
        backtick, and the adversarial AC of #403 wants it `declared` with its own hash."""
        root = self.repo({"CONTEXT.md": "# prose, nothing typed here\n", "source.txt": "x\n"})
        self.assertEqual([(r["source_id"], r["layer"]) for r in self.rows(root)],
                         [("CONTEXT.md", "declared")])

    def test_the_documents_it_names_arrive_under_the_area_that_names_them(self) -> None:
        root = self.repo(self.files())
        self.assertEqual(self.one(root, "docs/adr/ADR-014-navigator.md", "pricing")["area"],
                         "pricing")
        row = self.one(root, "docs/research/scheduler.md", "pricing", "scheduling")
        self.assertEqual((row["area"], row["kind"]), ("scheduling", "document"))

    def test_an_area_nobody_asked_for_is_never_emitted(self) -> None:
        """Residual (G) of the breaker on PR #415: a pack that delivers the pricing decision
        under an area nobody named satisfies an incident while answering a question nobody
        asked. The emitted areas are a subset of the areas passed to `resolve`."""
        root = self.repo(self.files())
        emitted = {row.get("area") for row in self.rows(root, "pricing")} - {None}
        self.assertEqual(emitted, {"pricing"})
        self.assertEqual([r["source_id"] for r in self.rows(root, "pricing")
                          if r["source_id"] == "docs/research/scheduler.md"], [])


class TheLessonEntersOnlyOnceSomebodyVerifiedIt(Built):
    def built(self) -> Path:
        return self.ledger(self.repo({"CONTEXT.md": "# prose\n", "src": "x\n"}))

    def test_two_lessons_one_verified_leaves_exactly_one_declared_row(self) -> None:
        """AC of #403, and the founder's answer to question 2 of the lifecycle plan."""
        root = self.built()
        rows = [r for r in self.rows(root, "pricing") if r["kind"] == "lesson"]
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["recurrence"], 3)
        self.assertEqual(rows[0]["verified_against"], git(root, "rev-parse", "HEAD~1"))

    def test_the_unverified_lesson_is_an_unknown_row_never_silence(self) -> None:
        pack = contextpack.resolve(self.built(), "", ["pricing"], degrade=True)
        named = [r for r in pack["unknown"] if r.get("kind") == "lesson"]
        self.assertEqual(len(named), 1, pack["unknown"])
        self.assertEqual(named[0]["reason"].split(":")[0], "unverified")

    def test_a_lesson_of_another_area_is_not_this_areas_lesson(self) -> None:
        pack = contextpack.resolve(self.built(), "", ["delivery"], degrade=True)
        self.assertEqual([r for r in pack["declared"] if r["kind"] == "lesson"], [])
        self.assertEqual([r for r in pack.get("unknown") or [] if r.get("kind") == "lesson"], [])


class TheSealDoesNotMove(Built):
    def test_the_declared_rows_travel_beside_the_seal_never_inside_it(self) -> None:
        root = self.repo({"CONTEXT.md": MAP, "docs/adr/ADR-014-navigator.md": ADR,
                          "docs/research/scheduler.md": "# s\n"})
        with_layer = contextpack.resolve(root, "", ["pricing", "scheduling"], degrade=True)
        self.assertTrue(with_layer["declared"], "nothing was attached; the test proves nothing")
        with mock.patch.object(contextpack.declared_layer, "attach", lambda r, p, a: p):
            without = contextpack.resolve(root, "", ["pricing", "scheduling"], degrade=True)
        self.assertEqual(with_layer["pack_seal"], without["pack_seal"])

    def test_every_declared_row_speaks_the_plans_vocabulary(self) -> None:
        root = self.ledger(self.repo({"CONTEXT.md": MAP,
                                      "docs/adr/ADR-014-navigator.md": ADR,
                                      "docs/research/scheduler.md": "# s\n"}))
        rows = self.rows(root, "pricing", "scheduling")
        self.assertTrue(rows)
        for row in rows:
            missing = [field for field in SECTION_4 if field not in row]
            self.assertEqual(missing, [], f"{row['source_id']} misses {missing}")
            self.assertEqual(row["layer"], "declared")
            self.assertEqual(row["landed"], True, row["source_id"])


if __name__ == "__main__":
    unittest.main()
