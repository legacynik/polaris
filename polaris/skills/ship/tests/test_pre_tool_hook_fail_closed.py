"""A broken sibling script blocks the command instead of letting it run.

2026-10-26 (a product repository): the sibling imports ran at module load, outside main()'s try. A broken
sibling exited 1, which Claude Code treats as non-blocking, so a raw `gh pr merge` went through.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_a_broken_sibling_blocks_with_exit_2(tmp_path):
    copy = tmp_path / "scripts"
    shutil.copytree(SCRIPTS, copy, ignore=shutil.ignore_patterns("__pycache__"))
    (copy / "redact_scan.py").write_text("raise ImportError('broken on purpose')\n")
    payload = {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 9 --squash"}}
    done = subprocess.run([sys.executable, str(copy / "pre_tool_hook.py")], input=json.dumps(payload),
                          capture_output=True, text=True)
    assert done.returncode == 2, (done.returncode, done.stderr)
