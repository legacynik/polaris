"""A throwaway HOST repository, built from the package's own `_polaris` templates.

Every test in this lane runs the scripts the shipped SKILL.md bodies name, inside a real
`git init` tree that carries the contract a host repo would carry. Nothing here writes a
stub the test then asserts on: the fixtures are the templates the package ships, and the
commands are read out of the shipped skill bodies (`skill_block`) so a skill that stops
calling its script fails the test instead of passing it.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
TEMPLATES = PKG / "skills" / "start" / "templates" / "repo-contract"
LOGIN = "acme-dev"


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def host_repo(login: str = LOGIN, name: str = "acme-api") -> Path:
    """A committed repo with `_polaris/` seeded from the package templates.

    `name` is the checkout's own directory: the founder's vault lives under a directory with
    spaces in it, and every path this package prints has to survive that (polaris#14).
    """
    repo = Path(tempfile.mkdtemp(prefix="pm-a-")).resolve() / name
    (repo / "_polaris" / "state").mkdir(parents=True)
    (repo / "_polaris" / "team" / login / "sessions").mkdir(parents=True)
    (repo / "_polaris" / "team" / login / "weeks").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@t"), ("user.name", "T"), ("polaris.login", login)):
        git(repo, "config", key, value)
    (repo / "_polaris" / "config.yml").write_text("root: _polaris\n")
    seed_state(repo, "current.md")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "contract")
    return repo


def seed_state(repo: Path, name: str) -> Path:
    """Copy one state template into the host repo and return its path."""
    dest = repo / "_polaris" / "state" / name
    shutil.copyfile(TEMPLATES / "state" / name, dest)
    return dest


def written(path: Path, row: str, week: str = "") -> None:
    """Place a row with the SHIPPED writer: a hand-typed fixture only proves the reader
    agrees with itself. A `week` picks the todos door; without one it is a cockpit thread."""
    script = PKG / "skills" / "end" / "scripts" / "state_upsert.py"
    args = ["--week", week] if week else ["--owner", LOGIN, "--now", "2026-09-03"]
    done = subprocess.run([sys.executable, str(script), "week" if week else "thread",
                           str(path), *args], input=row + "\n", capture_output=True, text=True)
    if done.returncode:
        raise AssertionError(f"the shipped writer refused the fixture: {done.stderr.strip()}")


def env_for(repo: Path, login: str = LOGIN) -> dict:
    """The environment a session skill resolves before running any of its blocks."""
    root = repo / "_polaris"
    return {**os.environ,
            "CLAUDE_PLUGIN_ROOT": str(PKG),
            "ROOT": str(root),
            "MAIN_WT": str(repo),
            "LOGIN": login,
            "CURRENT": str(root / "state" / "current.md")}


def skill_block(skill: str, needle: str) -> str:
    """The shipped bash block that contains `needle`, verbatim from the SKILL.md or one of its
    references (the 60-line form moved most commands there in 0.33.0)."""
    d = PKG / "skills" / skill
    body = "\n".join(f.read_text(encoding="utf-8")
                     for f in [d / "SKILL.md", *sorted((d / "references").glob("*.md"))] if f.is_file())
    blocks = [textwrap.dedent(b) for b in
              re.findall(r"^[ \t]*```bash\n(.*?)^[ \t]*```", body, re.M | re.S)]
    hits = [b for b in blocks if needle in b]
    if len(hits) != 1:
        raise AssertionError(
            f"/{skill} has {len(hits)} shipped bash blocks containing {needle!r} — the skill "
            "no longer names the command this contract is about, or names it twice")
    return hits[0]


def run_block(skill: str, needle: str, repo: Path, **extra: str) -> subprocess.CompletedProcess:
    """Execute that block in the host repo, exactly as the skill instructs."""
    env = {**env_for(repo), **extra}
    return subprocess.run(["bash", "-c", skill_block(skill, needle)],
                          cwd=str(repo), env=env, capture_output=True, text=True)


def run_script(skill: str, name: str, *args: str, **kw) -> subprocess.CompletedProcess:
    """Run one shipped script directly, for the branches a single block cannot force."""
    script = PKG / "skills" / skill / "scripts" / name
    runner = [sys.executable] if name.endswith(".py") else ["bash"]
    return subprocess.run([*runner, str(script), *args], capture_output=True, text=True, **kw)
