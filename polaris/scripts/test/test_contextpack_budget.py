"""L2-T5 (#404) — the budget: what it may cut, in which order, and when it refuses.

`DEC-polaris-contextpack-flight-layer-001` is accepted and says it twice — "the budget
must cut flight before sealed", "Budget degradation cuts flight rows first and never a
sealed row" — so the order is flight, then declared. §8 of the lifecycle plan had written
declared first; a slice plan does not supersede an accepted Decision, so the plan was the
thing that got corrected.

`unknown` is not a candidate either. The same Decision's `contract:pack-never-silent` says
a missing source produces an UNKNOWN row, never silence, and dropping the row that says a
source is missing IS that silence, only harder to notice: a prose repository at
`--budget 200` used to ship one row of four and report `unknown: 1`. A pack still over its
ceiling after every permitted cut refuses instead, exactly as it already did for sealed
rows, and the receipt counts `unknown` from a snapshot taken before the cut.

Neither cuttable layer exists yet (L2-T3, L2-T4), so the order is proved on a synthetic
pack carrying all five keys at once. The guard that says no sealed row was cut is proved
non-vacuous the only way a guard can be: by mutating `CUT_ORDER` until it fires. It used
to label a cut with the pack KEY, so that mutation dropped fourteen Decisions while every
assertion looking for `sealed` stayed green.
"""
from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contextpack  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_seal as sealer  # noqa: E402
import contextpack_unknown  # noqa: E402

PROSE = {"CONTEXT.md": "# prose, nothing typed here\n", "source.txt": "x\n"}


@contextlib.contextmanager
def mutated(module, **values):
    """Swap module constants for the body of a test, so a guard can be shown to fire."""
    before = {key: getattr(module, key) for key in values}
    for key, value in values.items():
        setattr(module, key, value)
    try:
        yield
    finally:
        for key, value in before.items():
            setattr(module, key, value)


def cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / "contextpack.py"), *args],
                          cwd=root, capture_output=True, text=True)


class Built(unittest.TestCase):
    def build(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="budget-")).resolve()
        for name, body in PROSE.items():
            (root / name).write_text(body, encoding="utf-8")
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "under test"]):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                           cwd=root, check=True, capture_output=True)
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def emit(self, root: Path, sid: str, *extra: str) -> dict:
        done = cli(root, "resolve", "--root", ".", "--sid", sid, *extra)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads((root / f"state/session/{sid}/area-all.json").read_text())

    def five_layers(self) -> dict:
        """One row in every key a pack can carry, so an order can be read off the result."""
        return {"decisions": [{"source_id": "DEC-1"}], "documents": [{"source_id": "CONTEXT.md"}],
                "declared": [{"source_id": "adr"}], "flight": [{"source_id": "pr:1"}],
                "unknown": [{"source_id": "DOMAIN.md"}]}


class TheBudgetCutsFromTheBottom(Built):
    def test_an_unknown_row_is_never_cut_and_the_pack_refuses_instead(self) -> None:
        """`contract:pack-never-silent`: cutting the row that says "this is missing" IS
        the silence the row exists to end. Since L2-T4 round 2 a prose repository has THREE
        unknown rows plus one `declared` row for the prose `CONTEXT.md` the declared layer
        can read — so the cut has exactly one candidate, and a ceiling it still cannot meet
        must refuse rather than quietly ship one row. The ceiling is 100 because the three
        uncuttable rows measure 151 tokens: 200 is now MEETABLE by cutting the declared row,
        and a test whose premise the code satisfies proves nothing."""
        root = self.build()
        done = cli(root, "resolve", "--root", ".", "--sid", "s1", "--budget", "100")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("CONTEXT_OVERFLOW", done.stderr)
        self.assertFalse((root / "state" / "session" / "s1").exists(),
                         "a pack that did not emit leaves no receipt")
        pack = contextpack.resolve(root, "", [], degrade=True)
        self.assertEqual(len(pack["unknown"]), 3)
        self.assertEqual({c["layer"] for c in receipt.fit(dict(pack), 0)}, {"declared"},
                         "the declared row is the only candidate; no unknown row is one")
        self.assertEqual(len(pack["unknown"]), 3, "and the cut did not reach them")

    def test_the_receipt_counts_unknown_before_any_cut(self) -> None:
        """Even if a later layer list let `unknown` through, the receipt reports the truth.

        100, not 200, for the same reason as the case above: three rows measure 151 tokens,
        so a 200 ceiling leaves the mutation nothing to cut and the guard would pass by
        never firing."""
        root = self.build()
        receipt.configure("s-count", "", 100)
        self.addCleanup(receipt.configure, None, "", 4000)
        with mutated(receipt, CUT_ORDER=("unknown",)):
            receipt.close(root, sealer.seal(root, contextpack_unknown.pack(root, "", [])))
        rec = json.loads((root / "state/session/s-count/area-all.json").read_text())
        self.assertEqual(len(rec["unknown"]), 3, "counted before the cut, not after")
        self.assertTrue(rec["cuts"], "the mutation did cut — the count still tells the truth")

    def test_the_budget_applies_without_a_sid(self) -> None:
        """A `--budget` that only mattered when a receipt was asked for was a silent no-op."""
        root = self.build()
        done = cli(root, "resolve", "--root", ".", "--budget", "100")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("CONTEXT_OVERFLOW", done.stderr)
        self.assertFalse((root / "state").exists(), "no --sid, no receipt, budget or not")

    def test_two_thousand_leaves_this_pack_whole_and_cuts_nothing(self) -> None:
        root = self.build()
        rec = self.emit(root, "s1", "--budget", "2000")
        self.assertEqual(rec["cuts"], [])
        self.assertEqual(len(rec["unknown"]), 3)

    def test_the_cut_order_is_flight_then_declared_and_reaches_nothing_else(self) -> None:
        """The order the accepted Decision fixes, proved on all five keys at once.

        `DEC-polaris-contextpack-flight-layer-001`: "the budget must cut flight before
        sealed". The lifecycle plan's §8 had declared first; a slice plan does not
        supersede an accepted Decision, so the plan is the thing that was corrected."""
        pack = self.five_layers()
        cuts = receipt.fit(pack, 0)
        self.assertEqual([c["layer"] for c in cuts], ["flight", "declared"])
        self.assertEqual(receipt.CUT_ORDER, ("flight", "declared"))
        self.assertEqual(pack["decisions"], [{"source_id": "DEC-1"}], "sealed is never a candidate")
        self.assertEqual(pack["documents"], [{"source_id": "CONTEXT.md"}])
        self.assertEqual(pack["unknown"], [{"source_id": "DOMAIN.md"}], "never silence")

    def test_a_sealed_key_in_the_cut_order_is_labelled_sealed(self) -> None:
        """The "no sealed row was cut" guard must fire, not pass by never being asked.

        `fit` used to label a cut with the pack KEY it came from, so a mutation putting
        `decisions` in the order produced rows labelled `decisions` and every assertion
        looking for `sealed` stayed green while fourteen Decisions were dropped. The label
        is now the LAYER of the key, so the same mutation turns the guard red."""
        pack = self.five_layers()
        with mutated(receipt, CUT_ORDER=("decisions", "documents")):
            cuts = receipt.fit(pack, 0)
        self.assertEqual([c["layer"] for c in cuts], ["sealed", "sealed"])
        self.assertEqual(len([c for c in cuts if c["layer"] == "sealed"]), 2,
                         "the guard used elsewhere in this file must be able to see these")


if __name__ == "__main__":
    unittest.main()
