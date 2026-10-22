"""L2-T7 (#406) — putting the pack back after a compaction, and paying for it only once.

A compaction takes the pack out of the agent's context and leaves the receipt on disk.
The naive repair is to resolve again, which is what this file refuses: resolving again
walks the tracker over the network for every area, twice, and hands back a pack that is
identical to the one already recorded whenever `HEAD` has not moved. So the contract is
`HEAD`-bound: **at a still `HEAD` the rows come back from the receipt with zero tracker
calls; only a moved `HEAD` pays for a new emission, and the receipt it writes names the
one it followed.**

Four things are held down here, each because the cheap version of it is silently wrong:

- **"zero tracker calls" is counted, not asserted in prose.** The stub on PATH appends
  every invocation to `.gh-calls`, so a reinsertion that quietly re-resolved shows up as
  two lines rather than as a passing test with a slower clock.
- **A re-emission may not overwrite the receipt it followed.** One file per area per
  session was the T5 rule while a pack could only be emitted once; a second emission at a
  moved `HEAD` is a different claim about a different commit, and a receipt that replaces
  it destroys the only record of what the agent had before the compaction.
- **`prev` is the debt of #404 and it has two ends.** The first receipt of a session names
  the `start.json` that opened it; each later one names the receipt it superseded. A chain
  that only links receipts to each other proves nothing about which session they belong to.
- **The flight layer must be asked for an AREA.** Residue 1 of the #426 gate: `resolve`
  handed it `polaris.*` domain ids, which the tracker discards, so the pack reported open
  issues at time 0 and carried none at time 1 — and the label it asked for was `area:<slug>`
  where this tracker's issues carry `domain:<slug>`.

`gh` is replayed from a stub written onto PATH and the remote is a URL that is never dialled:
no case here reaches GitHub.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contextpack  # noqa: E402
import contextpack_receipt as receipt  # noqa: E402
import contextpack_reinsert as reinsert  # noqa: E402
import contextpack_seal as sealer  # noqa: E402
import session_receipt as srcpt  # noqa: E402

# Prose where the resolver wants a typed authority: no DOMAIN.md, so `--area` reaches the
# tracker as a raw label slug, which is the shape every adopting repository has (#344).
# `state/` is ignored here because it is ignored in every repository that runs this: the
# flight layer reports uncommitted files, so a receipt left in the worktree would itself
# become a flight row and make the SECOND emission of an unchanged pack differ from the
# first — a difference invented by the act of recording, not by anything that moved.
PROSE = {"CONTEXT.md": "# prose, nothing typed here\n", "source.txt": "x\n",
         ".gitignore": "state/\n.gh-calls\n"}
LAYERS = ("sealed", "declared", "flight", "unknown")
STUB = '''#!/usr/bin/env python3
"""Recorded `gh` for L2-T7: it answers from the commit, and it COUNTS."""
import sys
from pathlib import Path

args = sys.argv[1:]
with (Path.cwd() / ".gh-calls").open("a") as fh:
    fh.write(" ".join(args) + "\\n")
slug = next((a.split(":", 1)[1] for a in args if ":" in a and not a.startswith("-")), "")
recorded = Path.cwd() / ".gh-fixture" / f"{args[0]}-{slug}.json"
print(recorded.read_text(encoding="utf-8") if recorded.is_file() else "[]")
'''


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


def _record(root: Path) -> None:
    """One open issue and one open PR, filed under the label the tracker must ask for."""
    (root / ".gh-fixture").mkdir(parents=True)
    for kind in ("issue", "pr"):
        (root / ".gh-fixture" / f"{kind}-memoria.json").write_text(json.dumps(
            [{"number": 7, "title": f"an open {kind}", "state": "open",
              "headRefName": "work", "updatedAt": "2026-09-01T00:00:00Z"}]), encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _record(root)
    for name, body in PROSE.items():
        (root / name).write_text(body, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "the repository under test")
    _git(root, "remote", "add", "origin", "https://github.com/x/fixture.git")
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "gh").write_text(STUB, encoding="utf-8")
    (stub / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{stub}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(receipt, "_CFG", dict(receipt._CFG))
    return root


def _emit(root: Path, sid: str, area: str) -> dict:
    """One emission through the library door the dashboard uses at time 1."""
    receipt.configure(sid, area, sealer.BUDGET)
    return contextpack.resolve(root, "", receipt.selected_domains(root, area, []), degrade=True)


def _start(root: Path, sid: str) -> dict:
    return srcpt.write(srcpt.dir_for(root, sid) / "start.json",
                       {"phase": "start", "sid": sid, "ts": "2026-09-18T10:00:00+0000"})


def _calls(root: Path) -> list[str]:
    path = root / ".gh-calls"
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def _written(root: Path, sid: str) -> list[Path]:
    return sorted((root / "state" / "session" / sid).glob("area-*.json"))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _move_head(root: Path) -> None:
    (root / "source.txt").write_text("moved\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "HEAD moves under the session")


def test_a_still_head_reprints_the_receipt_and_never_asks_the_tracker(repo: Path) -> None:
    """(a) The whole point: a compaction is not a reason to pay for the pack twice."""
    _emit(repo, "s1", "memoria")
    first = _read(_written(repo, "s1")[0])
    (repo / ".gh-calls").unlink(missing_ok=True)
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert _calls(repo) == [], "a reinsertion at a still HEAD went back to the tracker"
    assert len(_written(repo, "s1")) == 1, [p.name for p in _written(repo, "s1")]
    assert f"seal={first['pack_seal'][:12]}" in "\n".join(lines), lines
    rows = [line for line in lines if line.startswith(LAYERS)]
    assert len(rows) == len(first["included"]) + len(first["unknown"]), lines


def test_a_moved_head_re_emits_and_the_second_receipt_names_the_first(repo: Path) -> None:
    """(b) A different commit is a different claim, and both survive."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    _emit(repo, "s1", "memoria")
    first = _read(_written(repo, "s1")[0])
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "memoria")
    written = _written(repo, "s1")
    assert len(written) == 2, [p.name for p in written]
    second = max((_read(path) for path in written), key=lambda rec: rec["ts"])
    assert second["pack_seal"] != first["pack_seal"]
    assert second["prev"] == first["rows_hash"], (second.get("prev"), first["rows_hash"])


def test_an_unchanged_re_emission_stays_one_receipt(repo: Path) -> None:
    """The other side of (b): a generation per emission would make the audit unreadable."""
    _emit(repo, "s1", "memoria")
    first = _read(_written(repo, "s1")[0])
    _emit(repo, "s1", "memoria")
    assert len(_written(repo, "s1")) == 1, [p.name for p in _written(repo, "s1")]
    assert _read(_written(repo, "s1")[0])["prev"] == first["prev"]


def test_no_receipt_at_all_re_emits_and_says_so(repo: Path) -> None:
    """(c) A missing receipt is a reason to resolve, never a reason to hand back nothing."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [line for line in lines if line.startswith("RECEIPT_MISSING")], lines
    assert len(_written(repo, "s1")) == 1
    assert [line for line in lines if line.startswith(LAYERS)], lines


def test_the_cli_exits_zero_when_it_had_to_re_emit(repo: Path) -> None:
    """(c) exit 0: a reinsertion that resolved is a success, not a failure."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"),
                           "reinsert", "--root", ".", "--sid", "s1", "--area", "memoria"],
                          cwd=repo, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "RECEIPT_MISSING" in done.stdout, done.stdout


def test_a_receipt_of_another_area_is_not_reused(repo: Path) -> None:
    """(d) The cheap `glob` reused the neighbour's pack and called it a reinsertion."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    _emit(repo, "s1", "gates")
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [line for line in lines if line.startswith("AREA_MISMATCH")], lines
    names = {path.name for path in _written(repo, "s1")}
    assert names == {"area-gates.json", "area-memoria.json"}, names


def test_prev_links_the_first_receipt_of_a_session_to_its_start(repo: Path) -> None:
    """(e) first half — the debt left open on #404: a pack receipt nothing tied to a session."""
    start = _start(repo, "s1")
    _emit(repo, "s1", "memoria")
    assert _read(_written(repo, "s1")[0])["prev"] == start["receipt_hash"]


def test_a_deleted_receipt_breaks_the_chain(repo: Path) -> None:
    """(e) second half: the link is worth what its verification is worth."""
    _start(repo, "s1")
    _emit(repo, "s1", "memoria")
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "memoria")
    assert reinsert.chain(repo, "s1") == [], "two linked receipts must verify"
    (repo / "state" / "session" / "s1" / "area-memoria.json").unlink()
    faults = reinsert.chain(repo, "s1")
    assert [line for line in faults if line.startswith("CHAIN_BROKEN")], faults


def test_the_flight_layer_asks_the_tracker_for_the_area_label(repo: Path) -> None:
    """(f) Residue 1 of #426: the area never reached the tracker, and the label was wrong."""
    pack = _emit(repo, "s1", "memoria")
    asked = [line for line in _calls(repo) if "domain:memoria" in line]
    assert len(asked) == 2, _calls(repo)
    assert [row for row in pack["flight"] if row.get("kind") in ("issue", "pr")], pack["flight"]


def test_no_area_asks_the_tracker_nothing(repo: Path) -> None:
    """(f) the other half: no area named is no question asked, not an empty answer invented."""
    pack = _emit(repo, "s2", "")
    assert _calls(repo) == [], _calls(repo)
    assert not [row for row in pack["flight"] if row.get("kind") in ("issue", "pr")]


def test_the_cli_finds_the_open_session_when_no_sid_is_named(repo: Path) -> None:
    """The host hook knows a compaction happened and nothing else — least of all a `sid`.

    Wiring a hook to a flag only a human can fill is a hook that reports success and
    reinserts nothing, which is the failure mode this repository has already paid for."""
    _start(repo, "open-one")
    _emit(repo, "open-one", "memoria")
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"),
                           "reinsert", "--root", "."], cwd=repo, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "HEAD unchanged" in done.stdout, done.stdout
    assert "reused from area-memoria.json" in done.stdout, done.stdout


def test_with_no_open_session_the_cli_says_so_and_exits_zero(repo: Path) -> None:
    """A compaction outside a session is not an error: there is nothing to put back."""
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"),
                           "reinsert", "--root", "."], cwd=repo, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "NO_OPEN_SESSION" in done.stdout, (done.stdout, done.stderr)
    assert not (repo / "state" / "session").exists(), "nothing to reinsert, nothing written"


# --- round 2: what the critic and the breaker found on b7e15e2 -----------------------
# Five things a reinsertion must refuse to do. Four of them end the same way — re-emit
# instead of reusing — because after a compaction the agent must not be left with nothing;
# the refusal is of the RECEIPT, never of the reinsertion.


def _receipt_at(root: Path, sid: str, name: str) -> Path:
    return root / "state" / "session" / sid / name


def _rewrite(path: Path, rec: dict) -> None:
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")


def test_a_newer_receipt_of_another_area_does_not_hide_this_ones(repo: Path) -> None:
    """W1: `_latest` took the newest receipt of the SESSION, then compared its area.

    Any second area emitted after the one being reinserted turned a still HEAD into an
    AREA_MISMATCH and a full re-emission — the exact cost the task exists to avoid, on the
    most ordinary path there is: a session that looked at two areas."""
    _emit(repo, "s1", "memoria")
    _emit(repo, "s1", "gates")
    (repo / ".gh-calls").unlink(missing_ok=True)
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert _calls(repo) == [], "the area's own receipt was on disk and the tracker was paid"
    assert "reused from area-memoria.json" in "\n".join(lines), lines


def test_a_session_id_that_is_a_path_is_refused(repo: Path) -> None:
    """W2: the write path validated `sid` as a name; the READ path never did.

    `--sid ../session/victim` walked out of its own folder and reinserted another
    session's pack, exit 0 — the receipt directory is per-session for a reason."""
    _start(repo, "victim")
    _emit(repo, "victim", "memoria")
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"), "reinsert",
                           "--root", ".", "--sid", "../session/victim"],
                          cwd=repo, capture_output=True, text=True)
    assert done.returncode == 2, (done.returncode, done.stdout)
    assert "RECEIPT_NAME_INVALID" in done.stderr, done.stderr
    assert "area-memoria" not in done.stdout, done.stdout


def test_a_receipt_that_does_not_hash_to_its_own_claims_is_not_reused(repo: Path) -> None:
    """W3: the reinsertion trusted the receipt it read.

    `rows_hash` is the tamper-evidence the audit already computes, and the reinsertion
    put rows in front of the agent without ever asking it: a `source_id` rewritten in
    place came back as a real row of a real pack."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    _emit(repo, "s1", "memoria")
    path = _receipt_at(repo, "s1", "area-memoria.json")
    rec = _read(path)
    assert rec["included"], "the fixture must carry at least one included row"
    rec["included"][0]["source_id"] = "EVIL.md"
    _rewrite(path, rec)
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [line for line in lines if line.startswith("RECEIPT_TAMPERED")], lines
    assert "EVIL.md" not in "\n".join(lines), lines


def test_a_corrupt_receipt_is_neither_reported_missing_nor_overwritten(repo: Path) -> None:
    """W3, second half: unreadable was reported as absent, and then destroyed.

    `_read` returning None made the receipt invisible twice over — the reinsertion said
    RECEIPT_MISSING, which is a different and false claim, and `_place` saw no readable
    generation and handed the re-emission the same filename."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    _emit(repo, "s1", "memoria")
    path = _receipt_at(repo, "s1", "area-memoria.json")
    path.write_text("{not json", encoding="utf-8")
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [line for line in lines if line.startswith("RECEIPT_UNREADABLE")], lines
    assert path.read_text(encoding="utf-8") == "{not json", "the corrupt receipt was overwritten"
    assert _receipt_at(repo, "s1", "area-memoria.2.json").is_file(), "no new generation written"


def test_a_receipt_that_names_itself_breaks_the_chain(repo: Path) -> None:
    """W4: `prev` pointing at its own `rows_hash` resolved, so the chain said nothing.

    A link that names itself is not a link; it is how a forged chain terminates."""
    _emit(repo, "s1", "memoria")
    path = _receipt_at(repo, "s1", "area-memoria.json")
    rec = _read(path)
    _rewrite(path, dict(rec, prev=rec["rows_hash"]))
    assert [one for one in reinsert.chain(repo, "s1") if one.startswith("CHAIN_BROKEN")], \
        reinsert.chain(repo, "s1")


def test_two_receipts_that_name_each_other_break_the_chain(repo: Path) -> None:
    """W4: every `prev` resolved, and the ring reached no start receipt at all."""
    _start(repo, "s1")
    _emit(repo, "s1", "memoria")
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "memoria")
    first, second = _receipt_at(repo, "s1", "area-memoria.json"), \
        _receipt_at(repo, "s1", "area-memoria.2.json")
    older, newer = _read(first), _read(second)
    _rewrite(first, dict(older, prev=newer["rows_hash"]))
    assert [one for one in reinsert.chain(repo, "s1") if one.startswith("CHAIN_BROKEN")], \
        reinsert.chain(repo, "s1")


def test_a_receipt_written_for_another_session_is_not_reused(repo: Path) -> None:
    """W4: the receipt carries its own `sid` and nobody compared it with the folder.

    Dropping another session's receipt into this folder under the same name was enough
    to have its pack reinserted here."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    _emit(repo, "other", "memoria")
    source = _receipt_at(repo, "other", "area-memoria.json")
    target = _receipt_at(repo, "s1", "area-memoria.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [line for line in lines if line.startswith("SID_MISMATCH")], lines


def test_a_chain_that_reaches_no_start_receipt_says_so(repo: Path) -> None:
    """W4: an unanchored chain read exactly like a sound one.

    It is a fault, not a break: the links are all there, and nothing ties them to a
    session. `test_a_deleted_receipt_breaks_the_chain` is the guard on the other side —
    with a start receipt present, the chain reports nothing at all."""
    _emit(repo, "s1", "memoria")
    faults = reinsert.chain(repo, "s1")
    assert [one for one in faults if one.startswith("CHAIN_UNANCHORED")], faults


def test_a_broken_chain_is_not_reprinted(repo: Path) -> None:
    """W4: the verdict has to reach the reinsertion, or verifying the chain is decoration."""
    _start(repo, "s1")
    _emit(repo, "s1", "memoria")
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "memoria")
    _receipt_at(repo, "s1", "area-memoria.json").unlink()
    (repo / ".gh-calls").unlink(missing_ok=True)
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [line for line in lines if line.startswith("CHAIN_BROKEN")], lines
    assert _calls(repo) != [], "a pack whose chain does not resolve was reprinted anyway"


# --- round 2 (last): what survived the first repair -----------------------------------


def test_a_tampered_receipt_is_kept_as_the_evidence_it_is(repo: Path) -> None:
    """V2: refusing to REUSE a tampered receipt and then writing over it is not a refusal.

    `_place` compared the digest against the `rows_hash` the file CLAIMS, which a tamperer
    leaves intact — so the re-emission at a still HEAD matched it and took the same
    filename. The only copy of what the agent was nearly handed disappeared inside the
    repair for it."""
    _start(repo, "s1")  # W3c: a reinsertion needs an opened session (DEC stale-degrades)
    _emit(repo, "s1", "memoria")
    path = _receipt_at(repo, "s1", "area-memoria.json")
    rec = _read(path)
    rec["included"][0]["source_id"] = "EVIL.md"
    _rewrite(path, rec)
    reinsert.reinsert(repo, "s1", "memoria")
    assert _read(path)["included"][0]["source_id"] == "EVIL.md", "the evidence was overwritten"
    assert _receipt_at(repo, "s1", "area-memoria.2.json").is_file(), "no generation beside it"


def test_a_broken_chain_in_another_area_does_not_cost_this_one(repo: Path) -> None:
    """V3: `_why_not` read the whole session's chain, so one area's break taxed them all.

    A receipt deleted under `gates` made every later reinsertion of `memoria` pay the
    tracker at a still HEAD, permanently — the chain is per area, because `_place` only
    ever looks at one area's generations."""
    _start(repo, "s1")
    _emit(repo, "s1", "gates")
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "gates")
    _emit(repo, "s1", "memoria")
    _receipt_at(repo, "s1", "area-gates.json").unlink()
    (repo / ".gh-calls").unlink(missing_ok=True)
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert _calls(repo) == [], "another area's broken chain was charged to this one"
    assert "reused from area-memoria.json" in "\n".join(lines), lines


def test_chain_exits_zero_on_a_session_that_is_merely_unanchored(repo: Path) -> None:
    """V4: the command called UNANCHORED «not a break» and then exited 1 on it.

    Every session that never opened a start receipt is unanchored (#155), so `chain` was
    red on the normal case — and a gate that is red on the normal case gets ignored on
    the day it means something."""
    _emit(repo, "s1", "memoria")
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"),
                           "chain", "--root", ".", "--sid", "s1"],
                          cwd=repo, capture_output=True, text=True)
    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    assert "CHAIN_UNANCHORED" in done.stdout, done.stdout


def test_chain_exits_one_on_a_link_that_does_not_resolve(repo: Path) -> None:
    """V4, the other side: the exit code still has to mean something."""
    _start(repo, "s1")
    _emit(repo, "s1", "memoria")
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "memoria")
    _receipt_at(repo, "s1", "area-memoria.json").unlink()
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"),
                           "chain", "--root", ".", "--sid", "s1"],
                          cwd=repo, capture_output=True, text=True)
    assert done.returncode == 1, (done.returncode, done.stdout)
    assert "CHAIN_BROKEN" in done.stdout, done.stdout


def test_an_unanchored_chain_is_reported_by_the_reinsertion_too(repo: Path) -> None:
    """V4: the reader of the pack is the one who needs to know it is tied to nothing."""
    _emit(repo, "s1", "memoria")
    lines = reinsert.reinsert(repo, "s1", "memoria")
    assert [one for one in lines if one.startswith("CHAIN_UNANCHORED")], lines


def test_a_reinsertion_over_a_broken_chain_still_exits_zero(repo: Path) -> None:
    """The exit code belongs to `chain`, not to `reinsert`.

    A reinsertion that had to resolve is a success with a cost — that is the whole
    contract of RECEIPT_MISSING and its four siblings — and making the chain's verdict
    the command's verdict would have quietly turned the most defensible refusal into a
    failed hook."""
    _start(repo, "s1")
    _emit(repo, "s1", "memoria")
    _move_head(repo)
    reinsert.reinsert(repo, "s1", "memoria")
    _receipt_at(repo, "s1", "area-memoria.json").unlink()
    done = subprocess.run([sys.executable, str(SCRIPTS / "contextpack_reinsert.py"), "reinsert",
                           "--root", ".", "--sid", "s1", "--area", "memoria"],
                          cwd=repo, capture_output=True, text=True)
    assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
    assert "CHAIN_BROKEN" in done.stdout, done.stdout
