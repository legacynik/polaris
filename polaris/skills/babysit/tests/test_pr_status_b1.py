"""Fresh breaker, 2026-10-19: the signing environment and the bypass-test nobody ran.

- `--env LOCAL` was not `local` (a case-sensitive compare next to a lowercasing `signs()`).
- `--env ""` signed any receipt whose `ambiente:` was empty: `"" == ""`. Fail closed.
- `ambiente:` with the word on the next line signed: `\\s*` ate the newline.
- The first word of `ambiente:` is the environment, free text may follow (real-testing step 8).
- references/bypass-test.md crashed with a TypeError and no CI ran it.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
SCRIPTS = HERE.parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import pr_status as ps  # noqa: E402
import receipt  # noqa: E402

HEAD = "a" * 40
PR = {"state": "OPEN", "headRefOid": HEAD, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
      "statusCheckRollup": []}


def run(ambiente: str, env: str) -> dict:
    me = {"user": {"login": "me"}, "body": f"<!-- real-test v1 sha={HEAD} verdict=MERGEABLE -->\nambiente:{ambiente}"}
    return ps.summarize(pr=PR, threads=[], comments=[me], reviews=[], viewer="me", now="2026-02-01T00:00:00Z",
                        ignore={}, label=None, body_errors=[], changed_since={}, inert=[], env=env)


def test_b1_env_is_case_insensitive_everywhere():
    assert run(" local", "LOCAL")["verdict"] == "READY"


@pytest.mark.parametrize("env", ["", " "])
def test_b2_a_blank_env_never_signs(env):
    assert not receipt.signs("", env)
    assert run("", env)["verdict"] != "READY"


@pytest.mark.parametrize("env", ["", "  "])
def test_b2_a_blank_env_is_refused_before_any_network(monkeypatch, capsys, env):
    monkeypatch.setattr(sys, "argv", ["pr_status.py", "5", "--env", env])
    monkeypatch.setitem(sys.modules, "pr_fetch", None)  # any fetch attempt raises ImportError
    assert ps.main() == 2
    assert "--env" in capsys.readouterr().err


def test_b3_the_environment_word_must_sit_on_the_ambiente_line():
    assert run("\nlocal", "local")["verdict"] != "READY"
    assert run(" \t\nlocal", "local")["verdict"] != "READY"


def test_b8_the_first_word_is_the_environment_free_text_may_follow():
    assert run(" local — su questo Mac", "local")["verdict"] == "READY"
    assert run(" locale — su questo Mac", "local")["verdict"] != "READY"


def test_b2_the_bypass_test_reference_runs_and_holds(tmp_path):
    md = (HERE.parents[1] / "references" / "bypass-test.md").read_text(encoding="utf-8")
    block = re.search(r"```bash\n(.*?)```", md, re.S).group(1)
    (tmp_path / "references").mkdir()
    (tmp_path / "scripts").symlink_to(SCRIPTS)
    script = tmp_path / "references" / "bypass.sh"
    script.write_text(block, encoding="utf-8")
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, cwd=tmp_path,
                       env={**os.environ, "GH_CONFIG_DIR": str(tmp_path)}, timeout=60)
    assert r.returncode == 0 and "BYPASS" not in r.stdout + r.stderr, r.stdout + r.stderr
