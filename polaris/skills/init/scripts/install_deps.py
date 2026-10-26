#!/usr/bin/env python3
"""install_deps.py — what each harness needs around the skills, through its own command.

  deps   [--apply]  binaries (bd, browser-harness), the MCP servers Serena, Context7, Sequential
                    Thinking and ai-memory per harness, Beads per harness. Dry-run without --apply.
  doctor            read-only: skills per harness, missing deps per Polaris skill, homonyms, dead
                    hooks, eval judge keys (presence only).
  --selfcheck       both modes in a throwaway HOME with stub harnesses on PATH.

The skills are read from --src, by default the skills root this script is installed in (the
parent of `init/`). A Polaris skill is one whose description carries `◇ Polaris`.
Claude Code hooks are written only for what a caller passes: `--hook EVENT:MATCHER:REL` registers
`python3 "<src>/<REL>"` once, and `--mark FRAG` lets the run repoint or prune dead hooks whose
path contains FRAG (the caller's own checkout layout). Without them no hook is ever written.

Native commands only: `claude mcp add`, `codex mcp add`, `pi mcp add`; `hermes mcp add` is
interactive (it prompts for the tool list), so Hermes lines are printed, never run; omo has no
mcp command, so its ~/.omo/agent/mcp.json is merged. ai-memory and Beads wire themselves
(`ai-memory install-mcp|install-hooks`, `bd setup`). Configs are read for their NAMES only:
no value from any config or env var is ever printed or written. Python >= 3.9, stdlib only.

Exit: 0 done (a failed native command is reported, not fatal) · 2 usage error.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
SKILLS = Path(__file__).resolve().parents[2]  # <skills root>/init/scripts/install_deps.py
POLARIS = "◇ Polaris"

MCP = {  # name -> command; {ctx} is the harness's Serena context
    "serena": ["serena", "start-mcp-server", "--context={ctx}", "--project-from-cwd"],
    "context7": ["npx", "-y", "@upstash/context7-mcp"],
    "sequential-thinking": ["npx", "-y", "@modelcontextprotocol/server-sequential-thinking"],
}
# harness -> binary, Serena context, ai-memory client name, `bd setup` recipe
HARNESSES = {
    "claude": ("claude", "claude-code", "claude-code", "claude"),
    "codex": ("codex", "codex", "codex", "codex"),
    "hermes": ("hermes", "agent", None, None),
    "pi": ("pi", "agent", "pi", None),
    "omo": ("omo", "agent", None, None),
}
BINARIES = {  # binary -> how to get it; printed under dry-run, run under --apply
    "bd": "brew install beads",
    "browser-harness": "uv tool install git+https://github.com/browser-use/browser-harness",
    "serena": "uv tool install -p 3.13 serena-agent",
    "ai-memory": None,  # its installer is `curl | sh`: never run by us, see its README
}
AIMEM_HOOKS = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json",
               "pi": ".pi/agent/extensions/ai-memory-pi.ts"}  # where ai-memory's hooks land
BD_MARKS = {"claude": ".claude/settings.json", "codex": ".codex/AGENTS.md"}  # where `bd setup` writes `bd prime`
JUDGE_KEYS = ["OPENROUTER_API_KEY", "TYPESAFE_API_KEY"]
SKILL_ROOTS = [".claude/skills", ".codex/skills", ".agents/skills", ".pi/skills",
               ".omo/agent/skills", ".hermes/skills"]


class Unreadable(Exception):
    """A config that exists but does not parse: it is reported and never rewritten."""


def load_json(path, strict=False):
    """Missing file -> {}. Unparseable -> {} for reading, Unreadable when about to write it."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        if strict:
            raise Unreadable(path)
        return {}


def configured(harness):
    """MCP server names a harness already has. Keys only: values may hold secrets."""
    if harness == "claude":
        names = set(load_json(HOME / ".claude.json").get("mcpServers", {}))
        plugins = load_json(HOME / ".claude" / "settings.json").get("enabledPlugins", {})
        return names | {k.split("@")[0] for k, on in plugins.items() if on}
    if harness == "codex":
        text = read(HOME / ".codex" / "config.toml")
        return set(re.findall(r'^\[mcp_servers\."?([^\]".]+)"?\]', text, re.M))
    if harness == "hermes":  # the `mcp_servers:` block, two-space keys
        block = re.search(r"^mcp_servers:\n((?:[ \t].*\n?|\n)*)", read(HOME / ".hermes" / "config.yaml"), re.M)
        return set(re.findall(r"^  ([A-Za-z0-9_.-]+):", block.group(1), re.M)) if block else set()
    return set(load_json(HOME / f".{harness}" / "agent" / "mcp.json").get("mcpServers", {}))


def paths_in(cmd):
    """The absolute paths a hook command names, read the way the shell reads them: quoted
    paths with spaces stay whole. Unparseable shell names no path we can judge.
    Returns (as written, expanded) pairs."""
    try:
        words = shlex.split(cmd)
    except ValueError:
        return []
    return [(w, os.path.expanduser(w)) for w in words if w.startswith(("/", "~/"))]


def hook_text(path):
    """What a harness would run: the `hooks` block of a JSON config, or the whole text file
    (an extension, an AGENTS.md). A permission like `Bash(ai-memory status)` is not a hook."""
    return json.dumps(load_json(path).get("hooks", {})) if path.suffix == ".json" else read(path)


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def sh(cmd):
    return " ".join(shlex.quote(c) for c in cmd)


def act(apply, label, cmd):
    """Print one planned native command; under --apply, run it and say how it went."""
    if not apply:
        print(f"  {label}: add — {sh(cmd)}")
        return
    if not shutil.which(cmd[0]):
        print(f"  {label}: skipped — {cmd[0]} not on PATH — {sh(cmd)}")
        return
    rc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    print(f"  {label}: {'done' if rc == 0 else f'FAILED (exit {rc})'} — {sh(cmd)}")


def mcp_add_cmd(harness, name, cmd):
    if harness == "claude":
        return ["claude", "mcp", "add", "-s", "user", name, "--"] + cmd
    if harness in ("codex", "pi"):
        return [harness, "mcp", "add", name, "--"] + cmd
    return ["hermes", "mcp", "add", name, "--command", cmd[0], "--args"] + cmd[1:]


def merge_omo(name, cmd, apply):
    path = HOME / ".omo" / "agent" / "mcp.json"
    if not apply:
        print(f"  [omo] mcp {name}: add — {path} mcpServers.{name} = {json.dumps({'command': cmd[0], 'args': cmd[1:]})}")
        return
    try:
        data = load_json(path, strict=True)
    except Unreadable:
        print(f"  [omo] mcp {name}: {path} does not parse — not touched")
        return
    data.setdefault("mcpServers", {})[name] = {"command": cmd[0], "args": cmd[1:]}
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, data)
    print(f"  [omo] mcp {name}: done — merged into {path}")


def write_atomic(path, data):
    path = path.resolve()  # a dotfiles symlink stays a symlink: write its target
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def deps_binaries(apply):
    print("== binaries")
    for name, how in BINARIES.items():
        if shutil.which(name):
            print(f"  {name}: present")
        elif how is None or not apply:
            print(f"  {name}: missing — {how or 'see its README (installer is curl | sh, run it yourself)'}")
        else:
            act(apply, name, shlex.split(how))


def deps_harness(harness, apply):
    binary, ctx, aimem, bd_recipe = HARNESSES[harness]
    if not shutil.which(binary):
        print(f"  [{harness}] not installed, skipped")
        return
    have = configured(harness)
    for name, tmpl in MCP.items():
        cmd = [c.format(ctx=ctx) for c in tmpl]
        if name in have:
            print(f"  [{harness}] mcp {name}: present")
        elif harness == "omo":
            merge_omo(name, cmd, apply)
        elif harness == "hermes":  # interactive prompt: never run headless
            print(f"  [hermes] mcp {name}: run yourself (interactive) — {sh(mcp_add_cmd(harness, name, cmd))}")
        else:
            act(apply, f"[{harness}] mcp {name}", mcp_add_cmd(harness, name, cmd))
    if "ai-memory" in have or (harness == "pi" and "ai-memory" in read(HOME / AIMEM_HOOKS["pi"])):
        print(f"  [{harness}] mcp ai-memory: present")  # on pi, its extension bridges the MCP tools
    elif aimem:
        act(apply, f"[{harness}] mcp ai-memory", ["ai-memory", "install-mcp", "--client", aimem, "--apply"])
    else:
        print(f"  [{harness}] mcp ai-memory: not covered by `ai-memory install-mcp`; add its "
              f"`ai-memory mcp-bridge --server-url <your server>` entry by hand")
    if harness == "hermes":  # ai-memory renders the Hermes block; it never writes that YAML
        print("  [hermes] hooks ai-memory: run yourself — ai-memory install-hooks --agent hermes "
              "(prints the hooks: block for ~/.hermes/config.yaml)")
    elif harness in AIMEM_HOOKS and "ai-memory" in hook_text(HOME / AIMEM_HOOKS[harness]):
        print(f"  [{harness}] hooks ai-memory: present")
    elif aimem:
        act(apply, f"[{harness}] hooks ai-memory", ["ai-memory", "install-hooks", "--agent", aimem, "--apply"])
    if bd_recipe and shutil.which("bd"):  # read the marker: any bd call writes ~/.beads
        if "bd prime" in hook_text(HOME / BD_MARKS[harness]):
            print(f"  [{harness}] beads: present")
        else:
            act(apply, f"[{harness}] beads", ["bd", "setup", bd_recipe, "--global"])


def is_canonical(src):
    """Hooks are registered only from a stable checkout: a linked git worktree (its `.git` is a
    file) disappears, and every hook pointing into it dies with it."""
    real = src.resolve()
    for d in [real] + list(real.parents):
        if (d / ".git").exists():
            return (d / ".git").is_dir()
    return True


def heal_hooks(settings, src, canonical, mark):
    """Suite-owned hooks (a command naming a path containing `mark`) whose file is gone:
    repoint them at `src` when the same file lives there and `src` is canonical, else prune.
    Foreign hooks are never touched. Returns (repointed (old, new) path pairs, pruned paths):
    paths only, never the command, which may carry an inline token."""
    repointed, pruned = [], []
    for event, entries in list(settings.get("hooks", {}).items()):
        kept_entries = []
        for entry in entries:
            items = []
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                dead = [(w, p) for w, p in paths_in(cmd) if mark in p and not os.path.exists(p)]
                rels = [p.split(mark, 1)[1] for _, p in dead]
                if not dead:
                    items.append(h)
                elif canonical and all((src / r).exists() for r in rels):
                    new = cmd
                    for (word, _), rel in zip(dead, rels):
                        quoted = any(q + word + q in cmd for q in "\"'")
                        target = f"{src}/{rel}"
                        new = new.replace(word, target if quoted else shlex.quote(target))
                    if new not in [i.get("command") for i in items]:
                        items.append(dict(h, command=new))
                    repointed += [(p, f"{src}/{r}") for (_, p), r in zip(dead, rels)]
                else:
                    pruned += [p for _, p in dead]
            if items or not entry.get("hooks"):
                kept_entries.append(dict(entry, hooks=items) if "hooks" in entry else entry)
        settings["hooks"][event] = kept_entries
    return repointed, pruned


def deps_hooks(src, apply, hooks, mark):
    if not (hooks or mark):
        return
    print("== hooks (Claude Code)")
    path = HOME / ".claude" / "settings.json"
    try:
        settings = load_json(path, strict=True)
    except Unreadable:
        print(f"  {path} does not parse — not touched; fix it and re-run")
        return
    canonical = is_canonical(src)
    repointed, pruned = heal_hooks(settings, src, canonical, mark) if mark else ([], [])
    for old, new in repointed:
        print(f"  hook repointed{'' if apply else ' (dry-run)'}: {old} -> {new}")
    for old in pruned:
        print(f"  hook pruned{'' if apply else ' (dry-run)'}: {old}")
    added = 0
    for event, matcher, rel in hooks:
        want = f'python3 "{src}/{rel}"'
        present = [h for e in settings.get("hooks", {}).get(event, []) for h in e.get("hooks", [])
                   if rel in h.get("command", "")]
        if present:
            print(f"  suite hook {event} {matcher} {rel}: present")
        elif not canonical:
            print(f"  suite hook {event} {matcher} {rel}: skipped — {src} is inside a linked git "
                  "worktree, not the canonical install; run from the main checkout")
        else:
            settings.setdefault("hooks", {}).setdefault(event, []).append(
                {"matcher": matcher, "hooks": [{"type": "command", "command": want}]})
            added += 1
            print(f"  suite hook {event} {matcher}: {'registered' if apply else 'add'} — {want}")
    if apply and (added or repointed or pruned):
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(path, settings)


def cmd_deps(src, apply, hooks=(), mark=None):
    deps_binaries(apply)
    print("== MCP servers, ai-memory and Beads per harness")
    for harness in HARNESSES:
        deps_harness(harness, apply)
    deps_hooks(src, apply, hooks, mark)
    print("\n" + ("applied." if apply else "DRY-RUN: nothing changed. Re-run with --apply."))


def skills_in(root):
    return sorted(p.name for p in root.iterdir() if (p / "SKILL.md").exists()) if root.is_dir() else []


def declared_deps(src):
    """`Requires X, Y and Z.` in a Polaris skill's description -> the known names it mentions."""
    known = list(BINARIES) + ["gh", "git", "python3"] + list(MCP)
    out = {}
    for skill in sorted(p for p in src.iterdir() if (p / "SKILL.md").exists()):
        desc = re.search(r"^description:(.*)$", read(skill / "SKILL.md"), re.M)
        m = desc and POLARIS in desc.group(1) and re.search(r"Requires ([^.\n]+)", desc.group(1))
        if m:
            words = re.findall(r"[a-z0-9-]+", m.group(1).lower())
            found = [k for k in known if k in words]
            if found:  # "Requires materialized evidence" names no dependency
                out[skill.name] = found
    return out


def homonyms(roots):
    seen = {}
    for root in roots:
        for name in skills_in(root):
            seen.setdefault(name, set()).add((root / name).resolve())
    return sorted(n for n, reals in seen.items() if len(reals) > 1)


def dead_hooks():
    for event, entries in load_json(HOME / ".claude" / "settings.json").get("hooks", {}).items():
        for entry in entries:
            for h in entry.get("hooks", []):
                missing = [p for _, p in paths_in(h.get("command", "")) if not os.path.exists(p)]
                if missing:  # the path, never the command: it may carry an inline token
                    yield event, " ".join(missing)


def cmd_doctor(src):
    roots = [HOME / r for r in SKILL_ROOTS]
    print("== skills per harness root")
    for root in roots:
        print(f"  {root}: {len(skills_in(root))} skills" if root.is_dir() else f"  {root}: absent")
    print(f"== missing deps per {POLARIS} skill (declared in the description as `Requires ...`)")
    deps = declared_deps(src)
    have = set().union(*(configured(h) for h in HARNESSES))
    missing = {s: [d for d in ds if not (shutil.which(d) or d in have)] for s, ds in deps.items()}
    for skill, ds in missing.items():
        print(f"  {skill}: missing {', '.join(ds)}" if ds else f"  {skill}: ok")
    print(f"  {len(deps)} skills declare deps")
    print("== homonyms (same name, different location) across ~/.claude, ~/.codex, ~/.agents")
    names = homonyms(roots[:3])
    for n in names:
        print(f"  homonym  {n}")
    print(f"  {len(names)} homonym(s)")
    print("== dead hooks (Claude Code settings.json)")
    dead = list(dead_hooks())
    for event, cmd in dead:
        print(f"  dead hook  {event}  {cmd}")
    print(f"  {len(dead)} dead hook(s)")
    print("== judge keys (presence only)")
    for key in JUDGE_KEYS:
        print(f"  {key}: {'set' if os.environ.get(key) else 'unset'}")


def selfcheck():
    """Both modes, as a subprocess, in a throwaway HOME with every harness a logging stub."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        home, bin_, src, log = tmp / "home", tmp / "bin", tmp / "skills", tmp / "argv.log"
        for d in (home, bin_, src / "alpha"):
            d.mkdir(parents=True)
        for name in ["bd", "npx", "serena", "ai-memory", "browser-harness", *(h[0] for h in HARNESSES.values())]:
            (bin_ / name).write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n')
            (bin_ / name).chmod(0o755)
        (src / "alpha" / "SKILL.md").write_text(
            f"---\nname: alpha\ndescription: {POLARIS} - a. Requires bd and context7.\n---\n", encoding="utf-8")
        env = {"HOME": str(home), "PATH": f"{bin_}{os.pathsep}/usr/bin{os.pathsep}/bin", "LANG": "C.UTF-8"}

        def run(*args):
            out = subprocess.run([sys.executable, "-B", __file__, *args, "--src", str(src)],
                                 capture_output=True, text=True, env=env)
            assert out.returncode == 0, out.stderr
            return out.stdout
        dry = run("deps")
        assert "claude mcp add -s user serena -- serena start-mcp-server" in dry and "DRY-RUN" in dry, dry
        doc = run("doctor")
        assert "alpha: missing context7" in doc and "judge keys" in doc, doc
        assert not log.exists() and not any(home.iterdir()), "a dry-run or doctor ran or wrote something"
    print("SELFCHECK OK — deps dry-run and doctor in a throwaway HOME: commands planned, none run, nothing written")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=["deps", "doctor"])
    ap.add_argument("--src", type=Path, default=SKILLS, help="the skills root (default: the one holding init/)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--hook", action="append", default=[], metavar="EVENT:MATCHER:REL",
                    help="a Claude Code hook to register as python3 \"<src>/<REL>\" (repeatable)")
    ap.add_argument("--mark", help="repoint or prune dead hooks whose path contains this fragment")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return selfcheck()
    if not a.mode:
        ap.error("a mode is required: deps or doctor")
    hooks = [h.split(":", 2) for h in a.hook]
    if any(len(h) != 3 for h in hooks):
        ap.error("--hook takes EVENT:MATCHER:REL")
    src = a.src.resolve()
    if a.mode == "deps":
        cmd_deps(src, a.apply, hooks, a.mark)
    else:
        cmd_doctor(src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
