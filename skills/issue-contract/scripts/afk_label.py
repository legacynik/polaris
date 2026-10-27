#!/usr/bin/env python3
"""afk_label — which AFK label an issue carries, and whether the created issue really carries it.

    afk_label.py pick   --human yes|no --labels LABELS.json [--config _polaris/config.yml]
    afk_label.py verify --human yes|no --issue ISSUE.json   --labels LABELS.json [--config ...]
    afk_label.py --selfcheck

LABELS.json is `gh label list --json name --limit 500`; ISSUE.json is `gh issue view N --json
labels`. The label names come from the product repository's `_polaris/config.yml`:

    tracker:
      afk_human: afk:human      # work a person must do; never claimed by an unattended agent
      afk_agent: afk:eligible   # work an unattended agent may claim

Without those keys the repository's own labels decide, first match wins (HUMAN / AGENT below).
`pick` exits 2 when work for a person has no label to carry it: an issue that silently loses
its human label is the defect this script exists to stop. Stdlib only, no network.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HUMAN = ("afk:human", "ready-for-human", "needs-human")
AGENT = ("afk:eligible", "ready-for-agent", "agent-ready")
KEYS = {"yes": "afk_human", "no": "afk_agent"}


def config_labels(path: Path) -> dict[str, str]:
    """`afk_human` / `afk_agent` under the top-level `tracker:` block. Line-based on purpose:
    two flat keys, no YAML loader needed. ponytail: nested or flow-style YAML is not read."""
    found, inside = {}, False
    if not path.is_file():
        return found
    for line in path.read_text(errors="replace").splitlines():
        if re.match(r"^\S", line):
            inside = line.split("#")[0].strip() == "tracker:"
            continue
        m = re.match(r"^\s+(afk_human|afk_agent):\s*(.*)$", line) if inside else None
        if m:
            value = re.sub(r"\s+#.*$", "", m.group(2)).strip().strip("\"'")
            if value:
                found[m.group(1)] = value
    return found


def names(path: Path, key: str | None = None) -> list[str]:
    data = json.loads(path.read_text())
    if key:
        data = data.get(key) or []
    return [str(item.get("name", "")) for item in data if isinstance(item, dict)]


def pick(human: str, repo_labels: list[str], config: dict[str, str]) -> tuple[str, str]:
    """(label, refusal). An empty label with no refusal = this repository has no agent label."""
    configured = config.get(KEYS[human])
    if configured:
        if configured in repo_labels:
            return configured, ""
        return "", (f"_polaris/config.yml names {configured!r} for this work but the repository has "
                    f"no such label: create it (gh label create {configured!r}) or fix the config")
    for label in HUMAN if human == "yes" else AGENT:
        if label in repo_labels:
            return label, ""
    if human == "yes":
        return "", ("work for a person needs a label no agent claims, and this repository has none "
                    f"of {', '.join(HUMAN)}: create one (gh label create afk:human) or name yours "
                    "as tracker.afk_human in _polaris/config.yml")
    return "", ""


def verify(human: str, issue_labels: list[str], repo_labels: list[str],
           config: dict[str, str]) -> list[str]:
    """What is wrong with the created issue's labels; empty = it carries the decision."""
    want, refusal = pick(human, repo_labels, config)
    if refusal:
        return [refusal]
    problems = [] if not want or want in issue_labels else [f"issue lacks {want!r}: add it"]
    other, _ = pick("no" if human == "yes" else "yes", repo_labels, config)
    if human == "yes" and other and other in issue_labels:
        problems.append(f"issue also carries {other!r}, so an agent may claim it: remove it")
    return problems


def selfcheck() -> int:
    repo = ["bug", "afk:eligible", "afk:human"]
    assert pick("yes", repo, {}) == ("afk:human", "")
    assert pick("no", repo, {}) == ("afk:eligible", "")
    assert pick("yes", ["bug"], {})[1], "no human label refuses"
    assert pick("yes", repo, {"afk_human": "x"})[1], "a configured label must exist"
    assert verify("yes", ["afk:human"], repo, {}) == []
    assert len(verify("yes", ["afk:human", "afk:eligible"], repo, {})) == 1
    print("SELFCHECK OK — pick (repo, config, refusal) and verify (missing, contradictory)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selfcheck", action="store_true")
    sub = parser.add_subparsers(dest="mode")
    for mode in ("pick", "verify"):
        p = sub.add_parser(mode)
        p.add_argument("--human", choices=("yes", "no"), required=True)
        p.add_argument("--labels", required=True, type=Path)
        p.add_argument("--config", default="_polaris/config.yml", type=Path)
        if mode == "verify":
            p.add_argument("--issue", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.mode:
        parser.error("pick or verify (or --selfcheck)")
    try:
        repo_labels = names(args.labels)
        issue_labels = names(args.issue, "labels") if args.mode == "verify" else []
    except (OSError, ValueError, AttributeError) as exc:
        print(f"unreadable label input ({exc}): a check that cannot read never passes", file=sys.stderr)
        return 2
    config = config_labels(args.config)
    if args.mode == "pick":
        label, refusal = pick(args.human, repo_labels, config)
        if refusal:
            print(refusal, file=sys.stderr)
            return 2
        print(label)
        return 0
    problems = verify(args.human, issue_labels, repo_labels, config)
    for line in problems:
        print(f"FAIL {line}")
    if not problems:
        print("OK the issue carries its AFK decision")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
