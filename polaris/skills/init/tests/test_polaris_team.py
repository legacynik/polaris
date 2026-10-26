"""init --team required|optional: the repo pins a Polaris version and keeps it installed.

Two seams. polaris_team.py writes the files a team commits (pin, session hook, Claude settings,
AGENTS.md section). The written hook is then run as the harness runs it, with a stub `npx` on
PATH, so throttle, silence and fail-open are observed, not read.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "polaris_team.py"
REPO = "acme/polaris"
SOURCE = f"https://github.com/{REPO}/tree/v9.9.9/polaris/skills"


def team(root, mode, ref="v9.9.9", repo=REPO, env=None):
    root.mkdir(exist_ok=True)
    extra = ["--repo", repo] if repo else []
    return subprocess.run([sys.executable, str(CLI), "--team", mode, "--ref", ref, "--root", str(root), *extra],
                          capture_output=True, text=True, env=env)


def files(root):
    return {p: (root / p).read_text() for p in
            (".polaris/team.json", ".polaris/session-start.sh", ".claude/settings.json", "AGENTS.md")}


def commands(root, event):
    entries = json.loads((root / ".claude" / "settings.json").read_text())["hooks"].get(event, [])
    return [h["command"] for e in entries for h in e["hooks"]]


def test_required_writes_pin_hook_settings_and_agents_section_once(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Repo rules\n\nkeep me\n")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(
        {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}))
    assert team(tmp_path, "required").returncode == 0
    first = files(tmp_path)
    pin = json.loads(first[".polaris/team.json"])
    assert pin == {"mode": "required", "ref": "v9.9.9", "source": SOURCE}
    assert os.access(tmp_path / ".polaris" / "session-start.sh", os.X_OK)
    assert "echo mine" in commands(tmp_path, "SessionStart")
    assert sum(".polaris/session-start.sh" in c for c in commands(tmp_path, "SessionStart")) == 1
    assert any(c.endswith("--check") for c in commands(tmp_path, "PreToolUse"))
    assert "keep me" in first["AGENTS.md"] and "STOP" in first["AGENTS.md"]
    assert team(tmp_path, "required").returncode == 0
    assert files(tmp_path) == first, "a second run changes nothing"


def test_switching_to_optional_drops_the_block_and_keeps_one_section(tmp_path):
    team(tmp_path, "required")
    team(tmp_path, "optional")
    assert json.loads((tmp_path / ".polaris" / "team.json").read_text())["mode"] == "optional"
    assert not any(".polaris/" in c for c in commands(tmp_path, "PreToolUse"))
    agents = (tmp_path / "AGENTS.md").read_text()
    assert agents.count("<!-- polaris-team:start -->") == 1 and "STOP" not in agents


def hook_env(tmp_path, npx_exit=0):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    log = tmp_path / "npx.log"
    (bin_ / "npx").write_text(f'#!/bin/sh\necho "npx $*" >> "{log}"\nexit {npx_exit}\n')
    (bin_ / "npx").chmod(0o755)
    env = {"HOME": str(tmp_path / "home"), "PATH": f"{bin_}:/usr/bin:/bin",
           "CLAUDE_PROJECT_DIR": str(tmp_path / "repo")}
    return env, log


def hook(env, *args):
    script = Path(env["CLAUDE_PROJECT_DIR"]) / ".polaris" / "session-start.sh"
    return subprocess.run(["sh", str(script), *args], capture_output=True, text=True, env=env)


def wait_for(cond, seconds=10):
    end = time.time() + seconds
    while time.time() < end and not cond():
        time.sleep(0.1)
    return cond()


def test_session_start_installs_the_pin_in_background_once_an_hour_then_goes_silent(tmp_path):
    team(tmp_path / "repo", "optional")
    env, log = hook_env(tmp_path)
    first = hook(env)
    assert first.returncode == 0
    assert wait_for(lambda: log.exists() and list((tmp_path / "home" / ".polaris").glob("installed-*")))
    assert log.read_text().split("\n")[0] == f"npx -y skills add {SOURCE} -g -y --skill *"
    second = hook(env)
    assert second.returncode == 0 and second.stdout == "" and second.stderr == ""
    time.sleep(0.5)
    assert len(log.read_text().splitlines()) == 1, "throttled: one install per hour"


def test_failed_install_never_blocks_the_session_but_required_blocks_skills(tmp_path):
    team(tmp_path / "repo", "required")
    env, log = hook_env(tmp_path, npx_exit=1)
    start = hook(env)
    assert start.returncode == 0 and "STOP" in start.stdout
    assert wait_for(log.exists)
    check = hook(env, "--check")
    assert check.returncode == 2 and check.stdout == ""  # exit 2: the harness blocks and shows stderr
    assert "npx skills add" in check.stderr


def test_optional_only_nudges_and_check_passes_once_installed(tmp_path):
    team(tmp_path / "repo", "optional")
    env, log = hook_env(tmp_path, npx_exit=1)
    out = hook(env)
    assert out.returncode == 0 and "recommended" in out.stdout and "STOP" not in out.stdout
    team(tmp_path / "repo", "required")
    env, log = hook_env(tmp_path, npx_exit=0)
    hook(env)  # throttled from the run above: no install, so mark it installed by hand
    state = tmp_path / "home" / ".polaris"
    for stamp in state.glob("checked-*"):
        (state / stamp.name.replace("checked-", "installed-")).touch()
    check = hook(env, "--check")
    assert check.returncode == 0 and check.stdout == ""


def test_a_repo_without_a_pin_is_left_alone(tmp_path):
    team(tmp_path / "repo", "required")
    (tmp_path / "repo" / ".polaris" / "team.json").unlink()
    env, log = hook_env(tmp_path)
    for args in ((), ("--check",)):
        out = hook(env, *args)
        assert out.returncode == 0 and out.stdout == ""
    assert not log.exists()


def test_an_installed_pin_is_never_fetched_again(tmp_path):
    team(tmp_path / "repo", "required")
    env, log = hook_env(tmp_path)
    state = tmp_path / "home" / ".polaris"
    hook(env)
    assert wait_for(lambda: list(state.glob("installed-*")))
    for stamp in state.glob("checked-*"):
        stamp.unlink()  # the hour has passed
    log.unlink()
    out = hook(env)
    time.sleep(0.5)
    assert out.stdout == "" and not log.exists(), "a pinned tag never changes: no re-install"


def test_the_package_repo_comes_from_the_caller_never_from_the_script(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "POLARIS_REPO"}
    missing = team(tmp_path / "a", "optional", repo=None, env=env)
    assert missing.returncode == 2 and "--repo" in missing.stderr
    assert not (tmp_path / "a" / ".polaris" / "team.json").exists()
    assert team(tmp_path / "b", "optional", repo=None, env=env | {"POLARIS_REPO": "other/pkg"}).returncode == 0
    assert json.loads((tmp_path / "b" / ".polaris" / "team.json").read_text())["source"] == \
        "https://github.com/other/pkg/tree/v9.9.9/polaris/skills"
    assert team(tmp_path / "c", "optional", repo="not a repo; rm -rf /", env=env).returncode == 2
