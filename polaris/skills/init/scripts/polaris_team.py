#!/usr/bin/env python3
"""polaris_team.py — team mode: the repository pins a Polaris version and keeps it installed.

  polaris_team.py --team required|optional --ref <tag> --repo <owner>/<name> [--root .]

--repo is the GitHub repository Polaris was installed from (POLARIS_REPO when omitted); the
script names no repository of its own.

Writes, for the team to commit (gstack's team mode, with a pinned version instead of latest):
  .polaris/team.json         the pin: mode, ref, and the `npx skills add` source at that ref
  .polaris/session-start.sh  the session hook: installs the pin in the background, retried at
                             most once an hour, silently; a failure never touches the session
  .claude/settings.json      SessionStart runs the hook; `required` also runs it with --check
                             before every skill, which exits 2 (blocks) while the pin is missing
  AGENTS.md                  one marked section: the same rule for every other harness

`optional` nudges once per session while the pin is missing; `required` says STOP and blocks
skills. Re-running is idempotent; switching mode rewrites only what this script owns.
Exit: 0 written · 2 usage error.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SOURCE = "https://github.com/{repo}/tree/{ref}/polaris/skills"
HOOK_CMD = 'sh "$CLAUDE_PROJECT_DIR/.polaris/session-start.sh"'
START, END = "<!-- polaris-team:start -->", "<!-- polaris-team:end -->"

HOOK = r"""#!/bin/sh
# Polaris team mode, written by `init --team`. Change the pin in .polaris/team.json, not here.
# SessionStart: install the pinned skills in the background, retried at most once an hour,
# silently; any failure leaves the session alone. A pinned tag never changes, so an installed
# pin is never fetched again: a new pin (new ref) is the update. --check (required mode, before
# a skill runs): exit 2 while the pin is not installed; the harness blocks and shows stderr.
# ponytail: "installed" is a per-pin marker under $HOME/.polaris; removing the skills by hand
# is not noticed until the pin changes.
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
pin="$root/.polaris/team.json"
[ -f "$pin" ] || exit 0
field() { sed -n "s/.*\"$1\": *\"\([^\"]*\)\".*/\1/p" "$pin" | head -n 1; }
mode=$(field mode); src=$(field source); ref=$(field ref)
state="${POLARIS_STATE_DIR:-$HOME/.polaris}"
key=$(printf '%s' "$src" | cksum | cut -d' ' -f1)
installed="$state/installed-$key"
how="npx skills add $src -g -y --skill '*'"
if [ "${1:-}" = "--check" ]; then
  [ -f "$installed" ] && exit 0
  echo "Polaris $ref is required in this repository and is not installed. Install it: $how" >&2
  exit 2
fi
[ -f "$installed" ] && exit 0
mkdir -p "$state" 2>/dev/null
stamp="$state/checked-$key"
if [ -z "$(find "$stamp" -mmin -60 2>/dev/null)" ]; then
  touch "$stamp" 2>/dev/null
  ( npx -y skills add "$src" -g -y --skill '*' </dev/null >/dev/null 2>&1 && touch "$installed" ) \
    </dev/null >/dev/null 2>&1 &
fi
if [ "$mode" = "required" ]; then
  echo "STOP: Polaris $ref is required in this repository and is not installed yet (an install is running in the background). Skills are blocked until it lands; if it keeps failing, ask the user to run: $how"
else
  echo "Polaris $ref is recommended in this repository and is not installed: $how"
fi
exit 0
"""


def section(mode, ref, source):
    rule = ("**Required.** If the Polaris skills are not installed, STOP and ask the user to "
            "install them before any work." if mode == "required" else
            "Recommended: without it the Polaris skills referenced here are unavailable.")
    return (f"{START}\n## Polaris (team: {mode})\n\nThis repository pins Polaris `{ref}` in "
            "`.polaris/team.json`. Claude Code installs and updates it at session start "
            "(`.polaris/session-start.sh`); in any other harness, run once:\n\n"
            f"    npx skills add {source} -g -y --skill '*'\n\n{rule}\n{END}\n")


def write(path, text, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(tmp, mode or 0o644)
    os.replace(tmp, path)


def merge_settings(path, mode):
    """Drop every hook item this script owns, then add the ones `mode` needs. Foreign hooks stay."""
    try:
        settings = json.loads(path.read_text())
    except FileNotFoundError:
        settings = {}
    hooks = settings.setdefault("hooks", {})
    for event in list(hooks):
        kept = []
        for entry in hooks[event]:
            items = [h for h in entry.get("hooks", []) if ".polaris/session-start.sh" not in h.get("command", "")]
            if items or not entry.get("hooks"):
                kept.append(dict(entry, hooks=items) if "hooks" in entry else entry)
        hooks[event] = kept
    hooks.setdefault("SessionStart", []).append({"hooks": [{"type": "command", "command": HOOK_CMD}]})
    if mode == "required":
        hooks.setdefault("PreToolUse", []).append(
            {"matcher": "Skill", "hooks": [{"type": "command", "command": HOOK_CMD + " --check"}]})
    for event in [e for e, entries in hooks.items() if not entries]:
        del hooks[event]
    write(path, json.dumps(settings, indent=2) + "\n")


def apply(root, mode, ref, repo):
    source = SOURCE.format(repo=repo, ref=ref)
    pin = {"mode": mode, "ref": ref, "source": source}
    write(root / ".polaris" / "team.json", json.dumps(pin, indent=2) + "\n")
    write(root / ".polaris" / "session-start.sh", HOOK, 0o755)
    merge_settings(root / ".claude" / "settings.json", mode)
    agents = root / "AGENTS.md"
    text = agents.read_text() if agents.exists() else ""
    block = section(mode, ref, source)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
    text = pattern.sub(lambda _: block, text) if pattern.search(text) else (
        text.rstrip("\n") + "\n\n" + block if text else block)
    write(agents, text)
    for p in (".polaris/team.json", ".polaris/session-start.sh", ".claude/settings.json", "AGENTS.md"):
        print(f"  + {p}")
    print(f"\nTeam mode ({mode}) at {ref}. Commit: git add .polaris .claude/settings.json AGENTS.md")


def selfcheck():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        apply(root, "required", "v0.0.1", "acme/polaris")
        apply(root, "optional", "v0.0.2", "acme/polaris")
        s = json.loads((root / ".claude" / "settings.json").read_text())["hooks"]
        assert "PreToolUse" not in s and len(s["SessionStart"]) == 1, s
        assert (root / "AGENTS.md").read_text().count(START) == 1
    print("SELFCHECK OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", choices=["required", "optional"])
    ap.add_argument("--ref", help="the Polaris release tag to pin, e.g. v0.25.2")
    ap.add_argument("--repo", default=os.environ.get("POLARIS_REPO"),
                    help="<owner>/<name> of the Polaris package repo (default: $POLARIS_REPO)")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return selfcheck()
    if not a.team or not a.ref:
        ap.error("--team and --ref are required")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", a.ref):  # it lands in a URL and a shell hook
        ap.error(f"--ref {a.ref!r}: letters, digits and . _ / - only")
    if not a.repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repo):
        ap.error(f"--repo {a.repo!r}: <owner>/<name> of the repo Polaris was installed from "
                 "(or set POLARIS_REPO)")
    apply(a.root.resolve(), a.team, a.ref, a.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
