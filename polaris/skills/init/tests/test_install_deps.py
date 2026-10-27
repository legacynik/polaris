"""scripts/install_deps.py: the dependencies each harness needs, through its own command.

The seam is the CLI. Every harness binary is a stub on PATH that logs its argv, so the tests see
exactly which native command would run, and a throwaway HOME holds the configs. Nothing here
touches the real HOME.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "install_deps.py"
STUBS = ["claude", "codex", "hermes", "pi", "omo", "ai-memory", "bd", "npx", "serena",
         "browser-harness", "gh", "git"]


def skill(root, name, description):
    (root / name).mkdir(parents=True)
    (root / name / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n", encoding="utf-8")


def world(tmp_path, stubs=STUBS):
    home, bin_, src = tmp_path / "home", tmp_path / "bin", tmp_path / "skills"
    for d in (home, bin_, src):
        d.mkdir(parents=True)
    log = tmp_path / "argv.log"
    for name in stubs:
        stub = bin_ / name
        stub.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\nexit 0\n')
        stub.chmod(0o755)
    skill(src, "alpha", "◇ Polaris — do alpha. Requires bd (Beads).")
    skill(src, "beta", "someone else's skill. Requires bd.")
    env = {"HOME": str(home), "PATH": f"{bin_}:/usr/bin:/bin", "LANG": "C.UTF-8"}
    return home, src, log, env


def run(env, *args, cli=CLI):
    return subprocess.run([sys.executable, "-B", str(cli), *map(str, args)],
                          capture_output=True, text=True, env=env)


def logged(log):
    return log.read_text().splitlines() if log.exists() else []


def tree(root):
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None)
            for p in sorted(root.rglob("*"))}


def test_deps_dry_run_names_each_native_command_and_runs_none(tmp_path):
    home, src, log, env = world(tmp_path)
    before = tree(home)
    out = run(env, "deps", "--src", src)
    assert out.returncode == 0, out.stderr
    for line in [
        "claude mcp add -s user serena -- serena start-mcp-server --context=claude-code --project-from-cwd",
        "codex mcp add context7 -- npx -y @upstash/context7-mcp",
        "pi mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking",
        "hermes mcp add serena --command serena --args start-mcp-server --context=agent --project-from-cwd",
        "ai-memory install-mcp --client claude-code --apply",
        "ai-memory install-hooks --agent codex --apply",
        "bd setup claude --global",
    ]:
        assert line in out.stdout, line
    assert "DRY-RUN" in out.stdout
    assert logged(log) == []  # a dry-run runs no harness command at all
    assert tree(home) == before


def test_deps_apply_runs_native_commands_and_skips_what_is_present(tmp_path):
    home, src, log, env = world(tmp_path)
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"serena": {"command": "serena"}}}))
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text('[mcp_servers.context7]\ncommand = "npx"\n')
    out = run(env, "deps", "--src", src, "--apply")
    assert out.returncode == 0, out.stderr
    calls = logged(log)
    assert "claude mcp add -s user context7 -- npx -y @upstash/context7-mcp" in calls
    assert not any(c.startswith("claude mcp add -s user serena") for c in calls)
    assert not any(c.startswith("codex mcp add context7") for c in calls)
    assert "ai-memory install-mcp --client pi --apply" in calls
    assert not any(c.startswith("hermes mcp add") for c in calls), "hermes add is interactive: print only"
    assert "serena: present" in out.stdout


def test_omo_has_no_mcp_command_so_its_json_is_merged_once(tmp_path):
    home, src, log, env = world(tmp_path)
    cfg = home / ".omo" / "agent" / "mcp.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"mcpServers": {"mine": {"command": "x"}}}))
    run(env, "deps", "--src", src, "--apply")
    first = json.loads(cfg.read_text())["mcpServers"]
    assert set(first) == {"mine", "serena", "context7", "sequential-thinking"}
    assert first["serena"]["args"] == ["start-mcp-server", "--context=agent", "--project-from-cwd"]
    again = run(env, "deps", "--src", src, "--apply")
    assert json.loads(cfg.read_text())["mcpServers"] == first
    assert "[omo] mcp serena: present" in again.stdout


def test_missing_harness_is_skipped_not_planned(tmp_path):
    home, src, log, env = world(tmp_path, stubs=["claude", "npx", "serena", "ai-memory", "bd"])
    out = run(env, "deps", "--src", src)
    assert "[codex] not installed, skipped" in out.stdout
    assert "codex mcp add" not in out.stdout


def test_a_missing_installer_is_reported_not_fatal(tmp_path):
    home, src, log, env = world(tmp_path, stubs=["claude", "npx", "serena", "ai-memory"])
    out = run(env, "deps", "--src", src, "--apply")  # bd and browser-harness missing, no brew/uv
    assert out.returncode == 0, out.stderr
    assert "not on PATH" in out.stdout


def test_nothing_secret_is_ever_printed(tmp_path):
    home, src, log, env = world(tmp_path)
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {
        "remote": {"type": "http", "url": "https://x", "headers": {"Authorization": "Bearer FAKESECRET1"}},
        "local": {"command": "x", "env": {"X_API_KEY": "FAKESECRET2"}}}}))
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text(
        '[mcp_servers.remote]\nurl = "https://x"\n'
        'http_headers = { Authorization = "Bearer FAKESECRET3" }\n')
    (home / ".hermes").mkdir()
    (home / ".hermes" / "config.yaml").write_text(
        "mcp_servers:\n  remote:\n    url: https://x\n    headers:\n      Authorization: Bearer FAKESECRET4\n")
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
        {"type": "command", "command": "SLACK_TOKEN=FAKESECRET7 /old/notify.sh"}]}]}}))
    env = {**env, "OPENROUTER_API_KEY": "FAKESECRET5", "TYPESAFE_API_KEY": "FAKESECRET6"}
    for args in (("deps", "--src", src), ("deps", "--src", src, "--apply"), ("doctor", "--src", src)):
        out = run(env, *args)
        assert "FAKESECRET" not in out.stdout + out.stderr, args
    assert "/old/notify.sh" in run(env, "doctor", "--src", src).stdout


def test_without_a_hook_flag_hooks_are_never_written(tmp_path):
    """The public copy owns no hook: a dead one is reported by doctor, never pruned or added."""
    home, src, log, env = world(tmp_path)
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
        {"type": "command", "command": f'python3 "{tmp_path}/old/skills/alpha/gone.py"'}]}]}}))
    before = settings.read_text()
    out = run(env, "deps", "--src", src, "--apply")
    assert out.returncode == 0, out.stderr
    assert settings.read_text() == before, out.stdout


def test_doctor_reports_polaris_skills_only_and_writes_nothing(tmp_path):
    home, src, log, env = world(tmp_path, stubs=["claude", "codex"])  # no bd on PATH
    for root in (".claude/skills", ".agents/skills"):
        skill(home / root, "twin", "x")
    skill(home / ".agents" / "skills", "same", "x")
    (home / ".claude" / "skills" / "same").symlink_to(home / ".agents" / "skills" / "same")
    (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"Stop": [
        {"hooks": [{"type": "command", "command": "bash /nowhere/dead.sh"}]}]}}))
    env = {**env, "OPENROUTER_API_KEY": "x"}
    before = tree(home)
    out = run(env, "doctor", "--src", src)
    assert out.returncode == 0, out.stderr
    assert f"{home}/.claude/skills: 2 skills" in out.stdout
    assert "alpha: missing bd" in out.stdout
    assert "beta" not in out.stdout  # not a Polaris skill: its deps are not ours to report
    assert "homonym  twin" in out.stdout and "homonym  same" not in out.stdout
    assert "dead hook  Stop  /nowhere/dead.sh" in out.stdout
    assert "OPENROUTER_API_KEY: set" in out.stdout and "TYPESAFE_API_KEY: unset" in out.stdout
    assert tree(home) == before


def test_default_source_is_the_skills_root_the_script_is_installed_in(tmp_path):
    home, _, _, env = world(tmp_path, stubs=["claude"])
    root = home / ".agents" / "skills"
    skill(root, "alpha", "◇ Polaris — do alpha. Requires bd (Beads).")
    (root / "init" / "scripts").mkdir(parents=True)
    installed = root / "init" / "scripts" / "install_deps.py"
    shutil.copy(CLI, installed)
    out = run(env, "doctor", cli=installed)
    assert out.returncode == 0, out.stderr
    assert "alpha: missing bd" in out.stdout


def test_pi_ai_memory_comes_from_its_extension(tmp_path):
    home, src, log, env = world(tmp_path)
    ext = home / ".pi" / "agent" / "extensions" / "ai-memory-pi.ts"
    ext.parent.mkdir(parents=True)
    ext.write_text("// ai-memory bridge\n")
    out = run(env, "deps", "--src", src)
    assert "[pi] mcp ai-memory: present" in out.stdout


def test_selfcheck_exercises_both_modes_and_leaves_home_alone(tmp_path):
    home, src, log, env = world(tmp_path)
    before = tree(home)
    out = run(env, "--selfcheck")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "SELFCHECK OK" in out.stdout
    assert tree(home) == before and logged(log) == []
