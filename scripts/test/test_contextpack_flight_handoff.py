"""L2-T5 × L2-T3 (#404 × #420) — the contract between the receipt and the flight layer.

The coordinator fixed the order the plan had left open: `resolve` ends as

    receipt.close(root, flight_layer.attach(root, sealer.seal(root, pack), domains))

so `sealer.seal` freezes `pack_seal` over the SEALED rows, T3 attaches the flight rows
outside that seal, and `close` runs last. Three things follow, and this file is where they
are held down so that whichever of #404 and #420 merges second finds the contract already
executable rather than described.

**`close` never recomputes `pack_seal`.** The breaker on #420 watched the seal move when an
untracked file changed, because attaching rows before a second seal folded them in. A seal
that moves when a row is attached or cut proves nothing about the rows it was supposed to
prove. So the fit measures the whole pack — sealed, unknown and flight — and touches none
of the four fields `seal` wrote.

**The fit is always active.** It used to run only when `--budget` narrowed the default,
which was invisible while no layer produced rows: with T3's 24 flight rows on the vault the
default `resolve` exits 2 with `CONTEXT_OVERFLOW: 4089>4000` instead of cutting flight to
fit. A ceiling that only applies when someone restates it is not a ceiling.

**The bookkeeping never reaches the agent, and never counts against it.** Measured on the
vault with both branches in: the pack weighed 64,245 bytes of which 51,242 were
`flight_budget.cut`, so the estimate read 16,126 tokens against 4,000, the fit emptied all
24 flight rows and still sat at 14,252, and the vault stopped emitting. `cut` is the record
of what was REMOVED: counting it against the ceiling that removed it, and then handing it
to the agent, is the opposite of both its jobs. So the estimate counts delivered rows and
nothing else, and `close` copies those cuts into the receipt and pops the key.

**The oldest flight row goes first.** T3 orders flight rows newest-first and gives each a
`ts`, so popping from the tail of that list IS the plan's "volo dal più vecchio". The order
WITHIN a layer belongs to T3; what belongs here is reading it the right way round, and a
test that fails if either side flips its convention.

The flight rows below are synthetic on purpose: #420 is not merged, and a handoff test that
waits for the other side is a handoff test nobody runs.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_context_backbone as cbb  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_seal as sealer  # noqa: E402
import contextpack_unknown  # noqa: E402

PROSE = {"CONTEXT.md": "# prose, nothing typed here\n", "source.txt": "x\n"}
NEWEST = datetime(2026, 9, 1, tzinfo=timezone.utc)


def flight_rows(count: int, padding: int = 0) -> list[dict]:
    """What T3 attaches: newest first, each carrying the `ts` the cut order reads."""
    return [{"source_id": f"flight-{i}", "layer": "flight", "kind": "pr", "landed": False,
             "freshness": "UNKNOWN", "ts": (NEWEST - timedelta(days=i)).isoformat(),
             "reason": "open PR on the area" + "." * padding} for i in range(count)]


class Handed(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="handoff-")).resolve()
        for name, body in PROSE.items():
            (self.root / name).write_text(body, encoding="utf-8")
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "under test"]):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                           cwd=self.root, check=True, capture_output=True)
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(receipt.configure, None, "", sealer.BUDGET)

    def attached(self, **extra) -> dict:
        """A pack sealed first and extended after, exactly as `resolve` will order it."""
        pack = sealer.seal(self.root, contextpack_unknown.pack(self.root, "", []))
        pack.update(extra)
        return pack

    def receipt_of(self, sid: str) -> dict:
        return json.loads((self.root / f"state/session/{sid}/area-all.json").read_text())


class TheSealIsFrozenBeforeAnythingIsAttached(Handed):
    def test_close_returns_the_seal_it_was_given_whatever_the_budget_cuts(self) -> None:
        frozen = sealer.seal(self.root, contextpack_unknown.pack(self.root, "", []))["pack_seal"]
        seals = []
        for budget in (500, sealer.BUDGET):
            receipt.configure(f"s-{budget}", "", budget)
            seals.append(receipt.close(self.root, self.attached(flight=flight_rows(24, 800)))["pack_seal"])
        self.assertEqual(seals, [frozen, frozen], "a seal that moves when a row is cut proves nothing")
        self.assertTrue(self.receipt_of("s-500")["cuts"], "500 must bind on 24 flight rows")

    def test_the_sealed_fields_are_not_rewritten_by_the_fit(self) -> None:
        sealed = sealer.seal(self.root, contextpack_unknown.pack(self.root, "", []))
        before = {k: sealed[k] for k in ("sealed_commit", "token_estimate", "pack_seal",
                                         "context_pack_id")}
        receipt.configure("s1", "", 500)
        closed = receipt.close(self.root, dict(sealed, flight=flight_rows(24, 800)))
        self.assertEqual({k: closed[k] for k in before}, before)


class TheFitIsAlwaysActive(Handed):
    def test_the_default_budget_cuts_flight_instead_of_refusing(self) -> None:
        """24 flight rows put the vault's own default resolve at 4089 > 4000."""
        receipt.configure("s1", "", sealer.BUDGET)
        over = self.attached(flight=flight_rows(24, 800))
        self.assertGreater(receipt._estimate(over), sealer.BUDGET, "the fixture must exceed 4000")
        closed = receipt.close(self.root, over)
        self.assertLessEqual(receipt._estimate(closed), sealer.BUDGET)
        self.assertTrue(self.receipt_of("s1")["cuts"])
        self.assertEqual([c for c in self.receipt_of("s1")["cuts"] if c["layer"] != "flight"], [])


class TheBookkeepingNeverReachesTheAgent(Handed):
    def test_a_large_flight_budget_neither_counts_nor_ships(self) -> None:
        """The measured failure: 200 cut rows put the vault at 16,126 tokens against 4,000."""
        pack = self.attached(flight=flight_rows(24),
                             flight_budget={"cut": flight_rows(200, 200), "cap": {"pr": 24}})
        self.assertLess(receipt._estimate(pack), sealer.BUDGET)
        receipt.configure("s1", "", sealer.BUDGET)
        closed = receipt.close(self.root, pack)
        self.assertNotIn("flight_budget", closed, "bookkeeping must not reach the agent")
        self.assertEqual(len(closed["flight"]), 24, "nothing needed cutting: the pack fits")
        cuts = self.receipt_of("s1")["cuts"]
        self.assertEqual(len([c for c in cuts if c["cut"] == "per-kind cap"]), 200)

    def test_the_estimate_counts_rows_and_not_the_envelope(self) -> None:
        """A seal, an id and a budget field are the pack's identity, not its content."""
        pack = self.attached()
        before = receipt._estimate(pack)
        pack.update(pack_seal="x" * 4000, context_pack_id="y" * 4000, token_budget=1)
        self.assertEqual(receipt._estimate(pack), before)

    def test_a_pack_that_still_overflows_on_rows_alone_refuses(self) -> None:
        """Dropping the bookkeeping must not become a way to smuggle rows past a ceiling."""
        receipt.configure("s1", "", 500)
        with self.assertRaises(cbb.ContractError) as caught:
            receipt.close(self.root, self.attached(declared=[], flight=[],
                                                   unknown=flight_rows(40, 400)))
        self.assertEqual(caught.exception.code, "CONTEXT_OVERFLOW")


class TheOldestFlightRowGoesFirst(Handed):
    def test_popping_the_tail_of_a_newest_first_list_cuts_the_oldest(self) -> None:
        keep = self.attached(flight=flight_rows(3)[:2])
        receipt.configure("s1", "", receipt._estimate(keep))
        closed = receipt.close(self.root, self.attached(flight=flight_rows(3)))
        self.assertEqual([r["source_id"] for r in closed["flight"]], ["flight-0", "flight-1"])
        self.assertEqual([c["source_id"] for c in self.receipt_of("s1")["cuts"]], ["flight-2"])


class TheReceiptCopiesTheCutsTheFlightLayerAlreadyMade(Handed):
    def test_a_per_kind_cap_cut_is_carried_into_the_receipt(self) -> None:
        """T3 caps per kind before the budget ever runs: those cuts must not be silent."""
        capped = flight_rows(1)[0]
        receipt.configure("s1", "", sealer.BUDGET)
        receipt.close(self.root, self.attached(flight_budget={"cut": [capped]}))
        cuts = self.receipt_of("s1")["cuts"]
        self.assertEqual([c["source_id"] for c in cuts], ["flight-0"])
        self.assertEqual(cuts[0]["cut"], "per-kind cap")
        self.assertEqual(cuts[0]["reason"], capped["reason"], "T3's own reason is kept")

    def test_no_flight_budget_key_leaves_the_receipt_to_the_budget_alone(self) -> None:
        receipt.configure("s1", "", sealer.BUDGET)
        receipt.close(self.root, self.attached())
        self.assertEqual(self.receipt_of("s1")["cuts"], [])


if __name__ == "__main__":
    unittest.main()
