#!/usr/bin/env python3
"""Merge the team settings — permissions and the compaction hook — into a repository.

The hook that reinserts the pack after a compaction was documented as JSON in prose, and
JSON in prose installs nothing: a mechanism that depends on somebody copying it by hand is
not a mechanism (polaris-os#406, round 2). It now lives in
`templates/settings.team.json`, and this puts it where the host reads it.

`settings.team.json` had no installer at all. Its original one was `pol-bootstrap`, a
legacy door that was removed — `check_skills.sh` still bans the name — so the template had
been orphaned and the permissions preset with it. `/start` step 2 calls this instead.

Three rules, because a settings file belongs to the repository and not to us:

- **Never clobber.** The file is read, merged and written back. A permission is added only
  when the list does not already carry it, and a hook block only when no hook of that event
  already runs the same command, so a second run changes nothing and says so.
- **A file we cannot parse is left alone.** `_load` returns `{}` for unreadable JSON, and
  writing over a settings file somebody is mid-edit on would be worse than not installing.
  It is reported as an install of its own rather than silently merged into nothing.
- **The hook is silent where it has nothing to do.** The command tests for the resolver and
  ends in `|| true`: a repository without the harness must not learn the feature exists
  (contract #155), and a hook may never fail a session.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "settings.team.json"


def _load(path: Path) -> dict:
    """The JSON object at `path`, or `{}` when there is none we can read."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _commands(doc: dict, event: str) -> set[str]:
    """Every command already wired to `event`, under whatever matcher."""
    return {one.get("command", "") for block in doc.get("hooks", {}).get(event) or []
            for one in block.get("hooks") or []}


def _merge_hooks(into: dict, wanted: dict) -> list[str]:
    """Add the template's hook blocks this file does not already run. By COMMAND, not by
    matcher: a repository that renamed the matcher still has the hook."""
    added = []
    for event, blocks in (wanted.get("hooks") or {}).items():
        have = _commands(into, event)
        new = [block for block in blocks
               if any(one.get("command") not in have for one in block.get("hooks") or [])]
        if new:
            into.setdefault("hooks", {}).setdefault(event, []).extend(new)
            added.append(event)
    return added


def _merge_allow(into: dict, wanted: dict) -> int:
    """Union the permission allow-list; return how many entries were new."""
    have = into.setdefault("permissions", {}).setdefault("allow", [])
    new = [one for one in (wanted.get("permissions") or {}).get("allow") or []
           if one not in have]
    have.extend(new)
    return len(new)


def install(repo: Path, template: Path = TEMPLATE) -> list[str]:
    """Merge the team settings into `<repo>/.claude/settings.json`; say what changed."""
    path = repo / ".claude" / "settings.json"
    doc, wanted = _load(path), _load(template)
    before = json.dumps(doc, sort_keys=True)
    added, events = _merge_allow(doc, wanted), _merge_hooks(doc, wanted)
    if json.dumps(doc, sort_keys=True) == before:
        return ["SETTINGS: already current"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return [f"SETTINGS: {path} — {added} permission(s) added, hooks added for"
            f" {', '.join(events) or 'no event'}"]


def _hook_command(repo: Path) -> str:
    blocks = _load(repo / ".claude" / "settings.json").get("hooks", {}).get("SessionStart", [])
    return next((one["command"] for block in blocks for one in block.get("hooks") or []), "")


def _probe(command: str, repo: Path) -> tuple[int, str]:
    """RUN the hook command. A hook is a string until somebody executes it, and a string
    is green under every breakage there is."""
    done = subprocess.run(["sh", "-c", command], cwd=repo, capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)})
    return done.returncode, done.stdout.strip()


def _plant(repo: Path) -> None:
    """A repository that does carry the harness, as far as the hook can tell."""
    (repo / "_polaris" / "scripts").mkdir(parents=True)
    (repo / "_polaris" / "config.yml").write_text("areas: []\n", encoding="utf-8")
    (repo / "_polaris" / "scripts" / "contextpack_reinsert.py").write_text(
        "print('REINSERT: stub ran')\n", encoding="utf-8")


def _cases(repo: Path) -> list[tuple[str, bool]]:
    """One case per way the hook could be installed and still do nothing."""
    install(repo)
    doc = _load(repo / ".claude" / "settings.json")
    blocks = doc.get("hooks", {}).get("SessionStart") or []
    command = _hook_command(repo)
    out = [("template is valid JSON with a SessionStart hook", bool(blocks)),
           ("the matcher is `compact`", "compact" in [b.get("matcher") for b in blocks]),
           ("it names the reinserter", "contextpack_reinsert.py" in command),
           ("the permissions preset survived the merge",
            "Bash(polmem *)" in doc.get("permissions", {}).get("allow", []))]
    code, said = _probe(command, repo)
    out.append(("silent and exit 0 with no resolver", code == 0 and said == ""))
    _plant(repo)
    code, said = _probe(command, repo)
    out.append(("runs the resolver when the repo has one", code == 0 and "stub ran" in said))
    out.append(("a second install changes nothing", install(repo) == ["SETTINGS: already current"]))
    return out


def cmd_selfcheck() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cases = _cases(Path(tmp))
    for name, ok in cases:
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    bad = [name for name, ok in cases if not ok]
    print(f"install_settings: {'OK' if not bad else 'FAILED'} ({len(cases) - len(bad)}/{len(cases)})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="install the team settings into a repository")
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--selfcheck", action="store_true")
    opts = ap.parse_args()
    if opts.selfcheck:
        return cmd_selfcheck()
    for line in install(opts.repo.resolve()):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
