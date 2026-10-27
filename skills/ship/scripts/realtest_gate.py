#!/usr/bin/env python3
"""real-test verdict gate — Phase A step that actually reads real-test's own
artifact before `gh pr create` (MANIFEST fix #2: ship never consumed a
NOT-MERGEABLE verdict, so a diff real-test rejected could still get a PR).

Opt-in, same convention as real-test's own gate.sh: only enforces if the
target repo has `.real-test/enabled` — a repo that hasn't adopted real-test
is never blocked by it. The verdict file's OWN `content_hash` field is
checked against a fresh `git write-tree`, never trusted by filename alone
(mirrors real-test's own bypass-test #2: a renamed/stale verdict must not
pass just because its filename matches).

    realtest_gate.py --root .        exit 0 = proceed/not-installed, 1 = blocked
    realtest_gate.py --selfcheck
"""
from __future__ import annotations
import sys, json, argparse, subprocess
from pathlib import Path

PROCEED = {"MERGEABLE", "MERGEABLE-CON-GAP"}


def tree_hash(root: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(root), "write-tree"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def decide(root: Path) -> dict:
    if not (root / ".real-test" / "enabled").exists():
        return {"verdict": "NOT_INSTALLED", "action": "SKIP",
                "why": "real-test not opted-in for this repo — nothing to consume"}
    tree = tree_hash(root)
    if not tree:
        return {"verdict": "UNKNOWN", "action": "BLOCKED",
                "why": "could not resolve the current tree — refusing to guess"}
    vfile = root / ".real-test" / "verdicts" / f"{tree}.json"
    if not vfile.exists():
        return {"verdict": "MISSING", "action": "BLOCKED",
                "why": f"no real-test verdict for the current tree ({tree})"}
    try:
        data = json.loads(vfile.read_text())
    except (OSError, ValueError) as e:
        return {"verdict": "UNREADABLE", "action": "BLOCKED", "why": str(e)}
    if data.get("content_hash") != tree:
        return {"verdict": "STALE", "action": "BLOCKED",
                "why": "verdict file's own content_hash does not match the current tree "
                       "— the filename alone proves nothing (same rule real-test enforces on itself)"}
    verdetto = data.get("verdetto", "NOT-MERGEABLE")
    if verdetto in PROCEED:
        return {"verdict": verdetto, "action": "PROCEED"}
    return {"verdict": verdetto, "action": "BLOCKED", "why": f"real-test verdict is {verdetto}"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    result = decide(Path(args.root))
    print(json.dumps(result, indent=2))
    return 0 if result["action"] in ("PROCEED", "SKIP") else 1


def selfcheck() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        assert decide(root)["action"] == "SKIP", \
            "not opted-in -> skip, never block a repo that hasn't adopted real-test"

        (root / ".real-test" / "verdicts").mkdir(parents=True)
        (root / ".real-test" / "enabled").touch()
        (root / "f.txt").write_text("x")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
        assert decide(root)["action"] == "BLOCKED", \
            "opted-in, no verdict file for this tree -> blocked, not a guessed pass"

        tree = tree_hash(root)
        vfile = root / ".real-test" / "verdicts" / f"{tree}.json"
        vfile.write_text(json.dumps({"content_hash": tree, "verdetto": "NOT-MERGEABLE"}))
        assert decide(root)["action"] == "BLOCKED", "NOT-MERGEABLE must block PR creation"

        vfile.write_text(json.dumps({"content_hash": tree, "verdetto": "MERGEABLE"}))
        assert decide(root)["action"] == "PROCEED", "MERGEABLE must proceed"

        vfile.write_text(json.dumps({"content_hash": tree, "verdetto": "MERGEABLE-CON-GAP"}))
        assert decide(root)["action"] == "PROCEED", \
            "MERGEABLE-CON-GAP proceeds (declared gap, not a hard block — matches real-test's own contract)"

        # renamed/stale: filename matches the current tree, but the content_hash INSIDE does not.
        vfile.write_text(json.dumps({"content_hash": "deadbeefdeadbeef", "verdetto": "MERGEABLE"}))
        assert decide(root)["action"] == "BLOCKED", \
            "content_hash mismatch inside the file must block even if the filename matches"

    print("SELFCHECK OK — 6 branches: skip-not-installed, missing-verdict-blocks, "
          "NOT-MERGEABLE-blocks, MERGEABLE-proceeds, MERGEABLE-CON-GAP-proceeds, stale-content_hash-blocks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
