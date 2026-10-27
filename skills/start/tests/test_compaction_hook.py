"""The compaction hook `install_settings.py` installs: silent where the repository has no
reinserter, and a reinserter that fails is VISIBLE — a non-zero exit, never `|| true`.

    python3 -m pytest skills-suite/start/tests/test_compaction_hook.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "start" / "scripts"))
import install_settings  # noqa: E402


def _hook(tmp: Path, repo: Path) -> subprocess.CompletedProcess:
    """Install into `repo`, then RUN the installed command the way the host does."""
    install_settings.install(repo)
    plugin = tmp / "plugin"
    plugin.mkdir(exist_ok=True)
    if not (plugin / "skills").exists():
        (plugin / "skills").symlink_to(SKILLS)   # `$CLAUDE_PLUGIN_ROOT/skills/start/...`
    return subprocess.run(["sh", "-c", install_settings._hook_command(repo)], cwd=repo,
                          capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo),
                               "CLAUDE_PLUGIN_ROOT": str(plugin)})


def _reinserter(repo: Path, body: str) -> None:
    scripts = repo / "_polaris" / "scripts"
    scripts.mkdir(parents=True)
    (repo / "_polaris" / "config.yml").write_text("areas: []\n")
    (scripts / "contextpack_reinsert.py").write_text(body)


def test_no_reinserter_is_silent_and_exit_0(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    done = _hook(tmp_path, repo)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_a_failing_reinserter_is_visible_and_non_zero(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _reinserter(repo, "import sys\nsys.stderr.write('RECEIPT_UNREADABLE: x\\n')\nsys.exit(2)\n")
    done = _hook(tmp_path, repo)
    assert done.returncode != 0, f"the hook swallowed a failing reinserter:\n{done.stderr}"
    assert "RECEIPT_UNREADABLE" in done.stderr
