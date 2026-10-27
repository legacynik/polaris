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
- **A file we cannot parse is left alone, and that is now true.** It was not: `_load`
  returned `{}` for unparseable JSON and the merge then wrote the template over it, so one
  missing brace in a repository's settings cost its `deny` list, its `model`, its
  permissions and every other plugin's hooks — with no backup and a non-atomic write. A
  file that exists, does not parse and is not blank now stops the install with
  `SETTINGS_UNREADABLE` and a non-zero exit, and nothing is written at all.
- **The hook is silent where it has nothing to do, and loud where it fails.** The command
  runs the door only `if` it exists: a repository without the harness must not learn the
  feature exists (contract #155). A door that exists and fails exits non-zero — a
  SessionStart hook's exit code never blocks a session, so swallowing it bought nothing
  and hid every broken reinsertion.
"""
from __future__ import annotations

import argparse
import json
import os
import re
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


OURS = re.compile(r"contextpack_reinsert|session_gate\.py")


def _drop_ours(into: dict, event: str) -> None:
    """Remove the blocks that are an OLDER version of the hook we are about to write.

    Merging by command alone installed a SECOND block the day the command changed, and the
    stale one kept running — against the wrong root, silently. A block whose every command
    is one of ours is ours to replace; anybody else's is never touched."""
    blocks = into.get("hooks", {}).get(event) or []
    kept = [block for block in blocks
            if not all(OURS.search(one.get("command", "")) for one in block.get("hooks") or [{}])]
    if len(kept) != len(blocks):
        into["hooks"][event] = kept


def _merge_hooks(into: dict, wanted: dict) -> list[str]:
    """Add the template's hook blocks this file does not already run. By COMMAND, not by
    matcher: a repository that renamed the matcher still has the hook."""
    added = []
    for event, blocks in (wanted.get("hooks") or {}).items():
        have = _commands(into, event)
        new = [block for block in blocks
               if any(one.get("command") not in have for one in block.get("hooks") or [])]
        if new:
            _drop_ours(into, event)
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


def _target(path: Path) -> tuple[dict, str]:
    """(the settings already there, the reason they may not be touched).

    A blank file and a bare `{}` are a fresh start and merge normally. Anything else that
    exists and does not parse is somebody's configuration, mid-edit or hand-written, and
    the only safe move is to stop: merging into `{}` writes the template OVER it."""
    if not path.is_file():
        return {}, ""
    try:
        raw = path.read_text(encoding="utf-8")
        doc = json.loads(raw) if raw.strip() not in ("", "{}") else {}
    except (OSError, ValueError) as exc:
        return {}, f"SETTINGS_UNREADABLE: {path} — {exc}; left alone, nothing installed"
    if not isinstance(doc, dict):
        return {}, (f"SETTINGS_UNREADABLE: {path} — top level is {type(doc).__name__},"
                    f" not an object; left alone, nothing installed")
    return doc, ""


def _write(path: Path, doc: dict) -> None:
    """Atomically: the host reads this file at session start, and half of one is worse
    than none. Temp file beside it, then `os.replace`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def install(repo: Path, template: Path = TEMPLATE) -> list[str]:
    """Merge the team settings into `<repo>/.claude/settings.json`; say what changed."""
    path = repo / ".claude" / "settings.json"
    doc, refusal = _target(path)
    if refusal:
        return [refusal]
    before = json.dumps(doc, sort_keys=True)
    wanted = _load(template)
    added, events = _merge_allow(doc, wanted), _merge_hooks(doc, wanted)
    if json.dumps(doc, sort_keys=True) == before:
        return ["SETTINGS: already current"]
    _write(path, doc)
    return [f"SETTINGS: {path} — {added} permission(s) added, hooks added for"
            f" {', '.join(events) or 'no event'}"]


def _hook_command(repo: Path) -> str:
    blocks = _load(repo / ".claude" / "settings.json").get("hooks", {}).get("SessionStart", [])
    return next((one["command"] for block in blocks for one in block.get("hooks") or []), "")


def _probe(command: str, repo: Path) -> tuple[int, str]:
    """RUN the hook command. A hook is a string until somebody executes it, and a string
    is green under every breakage there is.

    Against THIS package: the command names `$CLAUDE_PLUGIN_ROOT/skills`, which outside an
    install falls back to `~/.agents/skills`. A checkout is not an installation, and its skills
    root is not always called `skills` (`skills-suite/` in polaris-os), so the probe gets a
    plugin root of its own whose `skills` IS the root this file ships in."""
    plugin = repo / ".probe-plugin"
    if not (plugin / "skills").exists():
        plugin.mkdir(exist_ok=True)
        (plugin / "skills").symlink_to(HERE.parents[1])
    env = {k: v for k, v in os.environ.items() if k != "POLARIS_VAULT"}   # no machine vault
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               CLAUDE_PROJECT_DIR=str(repo), CLAUDE_PLUGIN_ROOT=str(plugin))
    done = subprocess.run(["sh", "-c", command], cwd=repo, capture_output=True, text=True, env=env)
    return done.returncode, done.stdout.strip()


def _plant(repo: Path, body: str = "print('REINSERT: stub ran')\n") -> None:
    """A repository that does carry the harness, as far as the hook can tell."""
    (repo / "_polaris" / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "_polaris" / "config.yml").write_text("areas: []\n", encoding="utf-8")
    (repo / "_polaris" / "scripts" / "contextpack_reinsert.py").write_text(body, encoding="utf-8")


OTHERS = {"permissions": {"allow": ["Bash(git *)"], "deny": ["Bash(rm -rf /)"]},
          "model": "opus",
          "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
              {"type": "command", "command": "echo another plugin"}]}]}}


def _settings(repo: Path, body: str) -> Path:
    path = repo / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _keeps_what_was_there(repo: Path) -> list[tuple[str, bool]]:
    """A settings file belongs to the repository. Two ways to take it away from it."""
    broken = _settings(repo, json.dumps(OTHERS)[:-3])       # one brace short of parseable
    before = broken.read_text(encoding="utf-8")
    said = install(repo)
    out = [("a malformed settings file refuses", said[0].startswith("SETTINGS_UNREADABLE")),
           ("and is not written to", broken.read_text(encoding="utf-8") == before)]
    _settings(repo, json.dumps(OTHERS))
    install(repo)
    doc = _load(broken)
    out += [("another plugin's hooks survive the merge",
             bool(doc.get("hooks", {}).get("PreToolUse"))),
            ("deny and model survive it too",
             doc.get("model") == "opus" and doc["permissions"].get("deny") == OTHERS[
                 "permissions"]["deny"]),
            ("and the compaction hook landed beside them",
             "session_gate.py" in _hook_command(repo))]
    return out


def _cases(repo: Path) -> list[tuple[str, bool]]:
    """One case per way the hook could be installed and still do nothing."""
    install(repo)
    doc = _load(repo / ".claude" / "settings.json")
    blocks = doc.get("hooks", {}).get("SessionStart") or []
    command = _hook_command(repo)
    out = [("template is valid JSON with a SessionStart hook", bool(blocks)),
           ("the matcher is `compact`", "compact" in [b.get("matcher") for b in blocks]),
           ("it names the door that finds the reinserter", "session_gate.py" in command),
           ("the template grants no tool permission",
            not doc.get("permissions", {}).get("allow"))]
    code, said = _probe(command, repo)
    out.append(("silent and exit 0 with no resolver", code == 0 and said == ""))
    _plant(repo)
    code, said = _probe(command, repo)
    out.append(("runs the resolver when the repo has one", code == 0 and "stub ran" in said))
    out.append(("a second install changes nothing", install(repo) == ["SETTINGS: already current"]))
    _plant(repo, "import sys\nsys.exit(2)\n")
    code, _ = _probe(command, repo)
    out.append(("a failing reinserter is visible (non-zero)", code != 0))
    return out + _keeps_what_was_there(repo / "other") + [_upgrades(repo / "old")]


# What an older machine carries: the first hook, before the door existed. Its trailing fail-open
# is left out: install recognises the hook by the script it names (OURS), not by its tail.
LEGACY = {"hooks": {"SessionStart": [{"matcher": "compact", "hooks": [
    {"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/_polaris/scripts/'
                                   'contextpack_reinsert.py" reinsert --root "$r"'}]}]}}


def _upgrades(repo: Path) -> tuple[str, bool]:
    """A machine that already ran the previous version keeps ONE hook, not two.

    Two blocks on one event is not a cosmetic duplicate: the stale one keeps running, and it
    is the one that asks the wrong root."""
    _settings(repo, json.dumps(LEGACY))
    install(repo)
    blocks = _load(repo / ".claude" / "settings.json")["hooks"]["SessionStart"]
    return ("an older copy of the hook is replaced, not doubled",
            len(blocks) == 1 and "session_gate.py" in _hook_command(repo))


def cmd_selfcheck() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "other").mkdir()
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
    lines = install(opts.repo.resolve())
    for line in lines:
        print(line)
    # A refusal is a failure of the install, not a quiet no-op: a caller that does not read
    # stdout must still learn that the hook it asked for is not installed.
    return 1 if any(one.startswith("SETTINGS_UNREADABLE") for one in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
