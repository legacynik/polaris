"""#156 (L4) — the typed lesson consolidator PROPOSES; nothing here promotes.

The ledger is append-only evidence: 170 blocks in this vault, 130 in one product repository
and 175 in another, written in five metadata shapes and, in one of the three, in none at
all. CLAUDE.md's rule for that pile is a consolidator that deduplicates, marks supersession
and moves a lesson along `note -> context -> gate -> archived` — and #156's own words are
`0 automatic promotion before deterministic approval`.

So every case here asserts two things at once: the classification is right, AND the ledger
on disk did not move. A consolidator that writes is a second source of truth, which is the
one thing the founder's rule forbids.

The cases:

- **four outcomes, zero duplicate actives** — the AC of #156. `keep`, `context`,
  `gate-candidate` and `archive` all appear, and no two ACTIVE rows are the same lesson.
- **three is the threshold** — recurrence 3 yields exactly one `gate-candidate`, and the
  file's hash is the same after the run as before it.
- **a block nobody can parse is NAMED** — `UNPARSED`, never dropped: rows == blocks, which
  is the contract that keeps a 130-block ledger with no metadata from reading as empty.
- **crash-after-archive** — a marker already in the ledger survives a second run: exit 0,
  one marker, no duplicate.
- **conflicting-supersession** — two lessons superseding each other resolve to nothing, so
  the run exits 2 with a `LESSON_CONFLICT` line each and promotes nothing.
- **verified_against is proposed, never taken** — the proposal must RESOLVE to a commit by
  `contextpack_lessons`' own predicate, or it is not a proposal.
- **signing writes one field** — the diff of `--apply --sign` is the field and nothing else,
  and an id nobody proposed is refused with no write at all.
- **the pipe** — a signed lesson is a `kind: lesson` row of the declared layer, which is the
  whole point of the task: before it, the three ledgers carry zero.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import shutil
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import contextpack_lessons as lessons  # noqa: E402
import lesson_consolidate as lc  # noqa: E402
import lesson_consolidate_verify as verify  # noqa: E402

CLI = ROOT / "scripts" / "lesson_consolidate.py"

KEEP = ("## 2026-01-02 — A note nobody has seen twice (@x)\n\n"
        "- rule: keep the fixture out of live state.\n- tier: note\n- recurrence: 1\n")
CONTEXT = ("## 2026-01-03 — Read the log before the model's story (@x)\n\n"
           "- rule: read the audit rows first.\n- tier: note\n- recurrence: 2\n")
GATE = ("## 2026-01-04 — Verify the branch before every commit (@x)\n\n"
        "- rule: assert the branch before a commit.\n- tier: context\n- recurrence: 4\n")
OLD = ("## 2026-01-05 — A rule stated once and restated later (@x)\n\n"
       "- rule: the first statement.\n- tier: note\n- recurrence: 1\n")
NEW = ("## 2026-01-06 — A rule stated once and restated later (@x)\n\n"
       "- rule: the second statement.\n- tier: note\n- recurrence: 1\n"
       "- Supersedes: 2026-01-05-a-rule-stated-once-and-restated-later\n")
PROSE_ONLY = ("## 2026-01-07 — A ledger with no metadata at all (@x)\n\n"
              "Prose, a paragraph, and a **Regola:** with nothing typed beside it.\n")


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=root, check=True, capture_output=True, text=True)
    return done.stdout.strip()


class Built(unittest.TestCase):
    """A throwaway repository whose `lessons.md` is the subject."""

    def build(self, body: str, extra: dict[str, str] | None = None) -> Path:
        root = Path(tempfile.mkdtemp(prefix="lesson-consolidate-")).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        (root / "lessons.md").write_text(body, encoding="utf-8")
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the ledger under test")
        if extra:
            self.commit(root, extra)
        return root

    def commit(self, root: Path, files: dict[str, str]) -> str:
        """A SECOND commit that does not touch the ledger: independent evidence."""
        self.write(root, files)
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the rule, applied")
        return git(root, "rev-parse", "HEAD")

    def write(self, root: Path, files: dict[str, str]) -> None:
        for name, text in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text, encoding="utf-8")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(CLI), *args],
                              capture_output=True, text=True)

    def digest(self, path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    def rows(self, root: Path) -> list[dict]:
        found, conflicts = lc.classify(root, (root / "lessons.md").read_text("utf-8"))
        self.assertEqual(conflicts, [], f"unexpected conflict: {conflicts}")
        return found

    def proposals(self, rows: list[dict]) -> list[str]:
        return [row["proposal"] for row in rows]


class FourOutcomes(Built):
    def test_the_four_lifecycle_outcomes_and_no_duplicate_active_lesson(self) -> None:
        """The AC of #156: four destinations classified, zero duplicate actives."""
        root = self.build(KEEP + "\n" + CONTEXT + "\n" + GATE + "\n" + OLD + "\n" + NEW)
        found = self.rows(root)
        self.assertEqual(len(found), 5, found)
        self.assertEqual(set(self.proposals(found)),
                         {"keep", "context", "gate-candidate", "archive"})
        actives = [row["id"] for row in found if row["proposal"] in lc.ACTIVE]
        self.assertEqual(len(actives), len(set(actives)), actives)
        self.assertEqual(lc.duplicate_actives(found), 0, found)

    def test_selfcheck_exits_zero(self) -> None:
        done = self.run_cli("--selfcheck")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("SELFCHECK OK", done.stdout)


class ThreeIsTheThreshold(Built):
    def test_recurrence_three_yields_exactly_one_gate_candidate(self) -> None:
        root = self.build(KEEP + "\n" + CONTEXT + "\n" + GATE)
        found = self.rows(root)
        gates = [row for row in found if row["proposal"] == "gate-candidate"]
        self.assertEqual(len(gates), 1, found)
        self.assertEqual(gates[0]["recurrence"], 4)

    def test_a_superseded_lesson_is_never_a_gate_candidate(self) -> None:
        """Supersession wins over recurrence: an archived rule is not promoted."""
        stale = GATE.replace("- recurrence: 4",
                             "- recurrence: 4\n- Archived: 2026-01-09 superseded by 2026-01-09-x")
        root = self.build(stale)
        self.assertEqual(self.proposals(self.rows(root)), ["archive"])

    def test_classify_writes_nothing(self) -> None:
        root = self.build(KEEP + "\n" + CONTEXT + "\n" + GATE + "\n" + OLD + "\n" + NEW)
        before = self.digest(root / "lessons.md")
        done = self.run_cli("classify", "--ledger", str(root / "lessons.md"),
                            "--root", str(root))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.digest(root / "lessons.md"), before, "classify wrote")


class NothingIsDropped(Built):
    def test_a_block_with_no_metadata_is_named_unparsed(self) -> None:
        """130 of one repository's blocks look like this; silence would read as empty."""
        root = self.build(KEEP + "\n" + PROSE_ONLY)
        found = self.rows(root)
        self.assertEqual(len(found), 2, found)
        bare = [row for row in found if row["proposal"] == "unparsed"]
        self.assertEqual(len(bare), 1, found)
        self.assertEqual(bare[0]["tier"], lc.UNPARSED)

    def test_two_blocks_sharing_a_title_get_distinct_ids(self) -> None:
        """An id is an address for --sign; two of them must never collide."""
        twin = KEEP.replace("2026-01-02", "2026-01-02")
        found = self.rows(self.build(KEEP + "\n" + twin))
        self.assertEqual(len({row["id"] for row in found}), 2, found)


class Fixtures(Built):
    def test_crash_after_archive_resumes_with_one_marker(self) -> None:
        done = self.run_cli("--fixture", "crash-after-archive")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        self.assertIn("markers=1", done.stdout)
        self.assertIn("duplicates=0", done.stdout)

    def test_conflicting_supersession_exits_two_and_promotes_nothing(self) -> None:
        done = self.run_cli("--fixture", "conflicting-supersession")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(done.stdout.count("LESSON_CONFLICT"), 2, done.stdout)
        self.assertIn("gate-candidate=0", done.stdout)

    def test_a_conflict_blocks_the_whole_classification(self) -> None:
        """Not one promotion escapes a ledger whose supersession does not resolve."""
        a = ("## 2026-02-01 — First of a mutual pair (@x)\n\n- rule: a.\n- tier: note\n"
             "- recurrence: 3\n- Supersedes: 2026-02-02-second-of-a-mutual-pair\n")
        b = ("## 2026-02-02 — Second of a mutual pair (@x)\n\n- rule: b.\n- tier: note\n"
             "- recurrence: 3\n- Supersedes: 2026-02-01-first-of-a-mutual-pair\n")
        root = self.build(a + "\n" + b)
        found, conflicts = lc.classify(root, (root / "lessons.md").read_text("utf-8"))
        self.assertEqual(len(conflicts), 2, conflicts)
        self.assertEqual([r for r in found if r["proposal"] == "gate-candidate"], [])


class Rings(Built):
    """Breaker 1: a two-lesson ring was caught and a three-lesson ring was not."""

    def ledger(self, links: list[tuple[int, int | None]]) -> str:
        """One block per entry; `None` means this block supersedes nothing."""
        blocks = []
        for one, two in links:
            body = (f"## 2026-04-0{one} — Lesson number {one} of the ring (@x)\n\n"
                    f"- rule: r{one}.\n- tier: note\n- recurrence: 3\n")
            if two is not None:
                body += f"- Supersedes: 2026-04-0{two}-lesson-number-{two}-of-the-ring\n"
            blocks.append(body)
        return "\n".join(blocks)

    def test_a_three_lesson_ring_is_a_conflict(self) -> None:
        root = self.build(self.ledger([(1, 2), (2, 3), (3, 1)]))
        rows, faults = lc.classify(root, (root / "lessons.md").read_text("utf-8"))
        self.assertTrue(faults, "A -> B -> C -> A resolved to nothing and said nothing")
        self.assertTrue(all("LESSON_CONFLICT" in line for line in faults), faults)
        self.assertEqual([r for r in rows if r["proposal"] == "archive"], [])

    def test_a_linear_chain_is_not_a_conflict(self) -> None:
        """Two supersessions in a row are a history, not a contradiction."""
        root = self.build(self.ledger([(1, 2), (2, 3), (3, None)]))
        rows, faults = lc.classify(root, (root / "lessons.md").read_text("utf-8"))
        self.assertEqual(faults, [], faults)
        self.assertEqual(sum(1 for r in rows if r["proposal"] == "archive"), 2, rows)


class Verification(Built):
    def build_cited(self) -> Path:
        cited = ("## 2026-03-01 — The branch is asserted before a commit (@x)\n\n"
                 "- rule: run `scripts/guard.py` before every commit.\n- tier: note\n"
                 "- recurrence: 3\n")
        return self.build(cited, {"scripts/guard.py": "# the rule, applied\n"})

    def test_a_proposal_resolves_to_a_commit(self) -> None:
        root = self.build_cited()
        made = verify.propose(root, self.rows(root))
        self.assertEqual(len(made), 1, made)
        sha, why, path = next(iter(made.values()))
        self.assertTrue(lessons._resolves(root, sha), f"{sha} resolves to no commit")
        self.assertIn("scripts/guard.py", why)
        self.assertEqual(path, "scripts/guard.py")

    def test_a_carried_path_beats_a_word_in_backticks(self) -> None:
        """`python3` dates the last commit that mentions it, which verifies nothing."""
        cited = ("## 2026-03-02 — Run it with `python3` after `scripts/guard.py` (@x)\n\n"
                 "- rule: a bare word is prose in backticks.\n- tier: note\n"
                 "- recurrence: 1\n")
        root = self.build(cited, {"scripts/guard.py": "# python3 lives here too\n"})
        made = verify.propose(root, self.rows(root))
        self.assertIn("modifies `scripts/guard.py`", next(iter(made.values()))[1], made)

    def test_a_bare_word_alone_is_not_evidence(self) -> None:
        root = self.build("## 2026-03-03 — Run it with `python3` (@x)\n\n"
                          "- rule: nothing named.\n- tier: note\n- recurrence: 1\n")
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_a_symbol_the_repository_does_not_carry_as_a_path_is_not_evidence(self) -> None:
        """F2/F3: a textual match (`git log -S`) dated the last commit that MENTIONS the
        string. Only a commit that MODIFIES a path the lesson cites is evidence now."""
        root = self.build("## 2026-03-06 — Never call `wiki_aggregate.py` from nowhere (@x)"
                          "\n\n- rule: a name, not a path.\n- tier: note\n- recurrence: 1\n")
        self.commit(root, {"docs/note.md": "wiki_aggregate.py is mentioned here\n"})
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_the_ledger_itself_is_never_the_evidence(self) -> None:
        """`last commit that touches lessons.md` dates the lesson, it does not verify it."""
        root = self.build("## 2026-03-04 — Keep it in `lessons.md` (@x)\n\n"
                          "- rule: the ledger cites itself.\n- tier: note\n- recurrence: 1\n")
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_a_directory_is_not_evidence_for_one_lesson(self) -> None:
        """`last commit that modifies scripts/` is the last commit that modified anything."""
        root = self.build("## 2026-03-09 — Everything under `scripts/` needs a caller (@x)"
                          "\n\n- rule: a directory.\n- tier: note\n- recurrence: 1\n")
        self.commit(root, {"scripts/guard.py": "# applied\n"})
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_a_live_authority_is_not_evidence_for_one_lesson(self) -> None:
        """`DOMAIN.md` moves whenever any component list does; it dates, never verifies."""
        root = self.build("## 2026-03-08 — Keep the scope of `DOMAIN.md` honest (@x)\n\n"
                          "- rule: a live authority.\n- tier: note\n- recurrence: 1\n")
        self.commit(root, {"DOMAIN.md": "# the typed authority\n"})
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_the_denylist_is_what_keeps_an_authority_out(self) -> None:
        """The rule must be the LIST, not an accident of the fixture: emptied, the same
        ledger gets a proposal on `CLAUDE.md`; restored, it gets none."""
        root = self.build("## 2026-03-10 — The rule lives in `CLAUDE.md` (@x)\n\n"
                          "- rule: a live authority.\n- tier: note\n- recurrence: 1\n")
        self.commit(root, {"CLAUDE.md": "# the instructions\n"})
        self.assertEqual(verify.propose(root, self.rows(root)), {})
        self.addCleanup(setattr, verify, "DENIED", verify.DENIED)
        verify.DENIED = set()
        self.assertEqual(len(verify.propose(root, self.rows(root))), 1,
                         "without the denylist nothing else was refusing it")

    def test_the_commit_that_wrote_the_lesson_cannot_verify_it(self) -> None:
        """F1 of the critic: `a1941eb` was the commit that WROTE the lesson. Circular."""
        root = Path(tempfile.mkdtemp(prefix="lesson-circular-")).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        self.write(root, {"lessons.md": "## 2026-03-05 — Guard it with `scripts/guard.py` (@x)"
                                        "\n\n- rule: one commit.\n- tier: note\n- recurrence: 1\n",
                          "scripts/guard.py": "# written in the same commit\n"})
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "the lesson and its subject, together")
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_a_commit_older_than_the_lesson_cannot_verify_it(self) -> None:
        """Breaker 5: `5fc5a14` precedes the lesson's own `last_triggered`."""
        root = self.build_cited()
        ledger = root / "lessons.md"
        ledger.write_text(ledger.read_text("utf-8").replace(
            "- recurrence: 3", "- recurrence: 3\n- last_triggered: 2099-01-01"),
            encoding="utf-8")
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_a_lesson_citing_nothing_gets_no_proposal(self) -> None:
        """A proposal nobody can point at a commit is not a proposal."""
        root = self.build(PROSE_ONLY)
        self.assertEqual(verify.propose(root, self.rows(root)), {})

    def test_a_lesson_already_verified_is_not_proposed_again(self) -> None:
        root = self.build_cited()
        head = git(root, "rev-parse", "HEAD")
        ledger = root / "lessons.md"
        ledger.write_text(ledger.read_text("utf-8").replace(
            "- tier: note", f"- verified_against: {head}\n- tier: note"), encoding="utf-8")
        self.assertEqual(verify.propose(root, self.rows(root)), {})


class Signing(Built):
    def sign(self, root: Path, area: str = "") -> subprocess.CompletedProcess:
        args = ["propose-verification", "--ledger", str(root / "lessons.md"),
                "--root", str(root), "--apply", "--sign",
                "2026-03-01-the-branch-is-asserted-before-a-commit"]
        return self.run_cli(*args, *(["--area", area] if area else []))

    def build_cited(self) -> Path:
        cited = ("## 2026-03-01 — The branch is asserted before a commit (@x)\n\n"
                 "- rule: run `scripts/guard.py` before every commit.\n- tier: note\n"
                 "- recurrence: 3\n")
        return self.build(cited + "\n" + KEEP, {"scripts/guard.py": "# applied\n"})

    def test_the_signature_records_why(self) -> None:
        """A sha alone is a claim; the path it came from is what a reader can check."""
        root = self.build_cited()
        self.assertEqual(self.sign(root).returncode, 0)
        body = (root / "lessons.md").read_text("utf-8")
        self.assertIn("- verified_why: scripts/guard.py@", body)

    def test_an_area_outside_the_vocabulary_is_refused(self) -> None:
        """F5: the value was written verbatim into the ledger, whatever it was."""
        root = self.build_cited()
        before = self.digest(root / "lessons.md")
        done = self.sign(root, "../../etc; rm")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(self.digest(root / "lessons.md"), before, "a refusal wrote")

    def test_one_area_may_not_be_claimed_for_two_lessons_at_once(self) -> None:
        """`--area` is one claim about one lesson, not a constant for the run."""
        second = ("\n## 2026-03-07 — Do not edit `scripts/other.py` by hand (@x)\n\n"
                  "- rule: the second citing lesson.\n- tier: note\n- recurrence: 1\n")
        root = self.build_cited()
        (root / "lessons.md").write_text((root / "lessons.md").read_text("utf-8") + second,
                                         encoding="utf-8")
        self.commit(root, {"scripts/other.py": "# applied\n"})
        before = self.digest(root / "lessons.md")
        done = self.run_cli("propose-verification", "--ledger", str(root / "lessons.md"),
                            "--root", str(root), "--apply", "--area", "gates", "--sign",
                            "2026-03-01-the-branch-is-asserted-before-a-commit,"
                            "2026-03-07-do-not-edit-scripts-other-py-by-hand")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(self.digest(root / "lessons.md"), before, "a refusal wrote")

    def test_the_line_endings_of_the_ledger_are_preserved(self) -> None:
        """Breaker 3: a CRLF ledger came back LF, so the diff was the whole file."""
        root = self.build_cited()
        ledger = root / "lessons.md"
        ledger.write_bytes(ledger.read_text("utf-8").replace("\n", "\r\n").encode())
        self.assertEqual(self.sign(root).returncode, 0)
        raw = ledger.read_bytes()
        self.assertNotIn(b"\r\r", raw)
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), "an LF line was written")

    def test_a_ledger_outside_the_root_is_refused(self) -> None:
        """Breaker 6: the consolidator read one repository and verified against another."""
        root, other = self.build_cited(), self.build(KEEP)
        done = self.run_cli("classify", "--ledger", str(other / "lessons.md"),
                            "--root", str(root))
        self.assertEqual(done.returncode, 2, done.stdout)

    def test_apply_adds_the_field_and_nothing_else(self) -> None:
        root = self.build_cited()
        before = (root / "lessons.md").read_text("utf-8").splitlines()
        done = self.sign(root)
        self.assertEqual(done.returncode, 0, done.stderr)
        after = (root / "lessons.md").read_text("utf-8").splitlines()
        added = [line for line in after if line not in before]
        self.assertEqual(len(added), 2, added)
        self.assertTrue(added[0].startswith("- verified_against: "), added)
        self.assertTrue(added[1].startswith("- verified_why: "), added)
        self.assertEqual([l for l in before if l not in after], [], "a line was lost")

    def test_apply_refuses_an_id_nobody_proposed(self) -> None:
        root = self.build_cited()
        before = self.digest(root / "lessons.md")
        done = self.run_cli("propose-verification", "--ledger", str(root / "lessons.md"),
                            "--root", str(root), "--apply", "--sign", "not-a-lesson")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(self.digest(root / "lessons.md"), before, "a refusal wrote")

    def test_apply_is_idempotent(self) -> None:
        root = self.build_cited()
        self.assertEqual(self.sign(root).returncode, 0)
        signed = self.digest(root / "lessons.md")
        done = self.sign(root)
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(self.digest(root / "lessons.md"), signed, "a second sign wrote")


class TheOutput(Built):
    """Breakers 2 and 4, and F8: what a machine and a human read off a run."""

    def test_json_stays_parseable_when_the_ledger_conflicts(self) -> None:
        a = ("## 2026-05-01 — One of a mutual pair (@x)\n\n- rule: a.\n- tier: note\n"
             "- recurrence: 1\n- Supersedes: 2026-05-02-two-of-a-mutual-pair\n")
        b = ("## 2026-05-02 — Two of a mutual pair (@x)\n\n- rule: b.\n- tier: note\n"
             "- recurrence: 1\n- Supersedes: 2026-05-01-one-of-a-mutual-pair\n")
        root = self.build(a + "\n" + b)
        done = self.run_cli("classify", "--ledger", str(root / "lessons.md"),
                            "--root", str(root), "--json")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertEqual(len(json.loads(done.stdout)), 2, done.stdout[:200])
        self.assertIn("LESSON_CONFLICT", done.stderr)

    def test_the_census_says_why_a_block_is_unparsed(self) -> None:
        """F8: `unparsed=130` is a number nobody can act on without the reason."""
        root = self.build(PROSE_ONLY)
        done = self.run_cli("classify", "--ledger", str(root / "lessons.md"),
                            "--root", str(root))
        self.assertIn("unparsed=1", done.stdout)
        self.assertIn("no tier/recurrence field", done.stdout)

    def test_two_undated_blocks_order_by_position_not_by_slug(self) -> None:
        """Breaker 4: `undated-` ids compared as strings, so the slug decided which was
        newer. The ledger is newest-on-top, so the block written FIRST is the newer one."""
        twin = ("## Zebra comes last in the alphabet and first in this file (@x)\n\n"
                "- rule: one.\n- tier: note\n- recurrence: 1\n")
        older = twin.replace("- rule: one.", "- rule: two.")
        rows = self.rows(self.build(twin + "\n" + older))
        marked = [row for row in rows if row["proposal"].startswith("duplicate-of:")]
        self.assertEqual(len(marked), 1, rows)
        self.assertEqual(marked[0]["line"], max(row["line"] for row in rows), marked)


@unittest.skipUnless((ROOT / ".github" / "workflows" / "suite-ci.yml").is_file(),
                     "reads the vault's own CI workflow; a package that installs this has none")
class TheCiGate(Built):
    """F4: the step piped the consolidator into `tail`, so its exit 2 was swallowed."""

    def fragment(self) -> str:
        """The consolidator lines of the real workflow step, as CI runs them."""
        body = (ROOT / ".github" / "workflows" / "suite-ci.yml").read_text(encoding="utf-8")
        step = body.split("- name: lesson consolidator")[1].split("\n      - name:")[0]
        shell = step.split("run: |\n")[1]
        lines = [line[10:] for line in shell.splitlines()
                 if line.strip() and not line.strip().startswith("#")
                 and "pytest" not in line and "pip install" not in line
                 and "selfcheck" not in line]
        self.assertTrue(any("lesson_consolidate.py classify" in one for one in lines), lines)
        # The vault path holds spaces: unquoted, bash splits it and the step fails for
        # the wrong reason — which is how this case passed while the defect was live.
        return "\n".join(lines).replace(
            "scripts/lesson_consolidate.py",
            shlex.quote(str(ROOT / "scripts" / "lesson_consolidate.py")))

    def test_a_conflicting_ledger_turns_the_step_red(self) -> None:
        a = ("## 2026-06-01 — One of a mutual pair (@x)\n\n- rule: a.\n- tier: note\n"
             "- recurrence: 1\n- Supersedes: 2026-06-02-two-of-a-mutual-pair\n")
        b = ("## 2026-06-02 — Two of a mutual pair (@x)\n\n- rule: b.\n- tier: note\n"
             "- recurrence: 1\n- Supersedes: 2026-06-01-one-of-a-mutual-pair\n")
        root = self.build(a + "\n" + b)
        done = subprocess.run(["bash", "-e", "-c", self.fragment()], cwd=root,
                              capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0,
                            f"the step passed on a conflicting ledger: {done.stdout}")


class ThePipe(Built):
    def test_a_signed_lesson_becomes_a_declared_row_of_its_area(self) -> None:
        """The whole task in one case: zero lesson rows before, one after."""
        cited = ("## 2026-03-01 — The branch is asserted before a commit (@x)\n\n"
                 "- area: gates\n- rule: run `scripts/guard.py` first.\n- tier: note\n"
                 "- recurrence: 3\n")
        root = self.build(cited, {"scripts/guard.py": "# applied\n"})
        self.assertEqual(lessons.rows(root, ["lessons.md"], ["gates"])[0]["layer"],
                         "unknown", "an unverified lesson is not a declared row")
        done = self.run_cli("propose-verification", "--ledger", str(root / "lessons.md"),
                            "--root", str(root), "--apply", "--sign",
                            "2026-03-01-the-branch-is-asserted-before-a-commit")
        self.assertEqual(done.returncode, 0, done.stderr)
        git(root, "commit", "-qam", "the founder signed one lesson")
        found = lessons.rows(root, ["lessons.md"], ["gates"])
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0]["layer"], "declared", found[0])
        self.assertTrue(found[0]["verified_against"], found[0])


if __name__ == "__main__":
    unittest.main()
