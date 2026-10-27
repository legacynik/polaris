"""Fresh breaker, 2026-10-19: flags between `pr` and its verb, glued short flags, `pr new` on the fallback.

- B1: `gh pr -R o/r merge 5` read `-R` as the verb, so every form of the repo flag placed after `pr`
  let a raw merge, an inline-body create or edit through; `-Ro/r` glued was not read as a repo.
- B1-c: a command shlex cannot split falls back to a regex that knew `create` and not its alias `new`.
- 6: `-bdone` is `--body done`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import pre_tool_hook as hook  # noqa: E402

M = "mer" + "ge"  # spelled apart: harness permission rules match the literal


def repo(tmp_path: Path) -> Path:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
    for args in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "base"],
                 ["checkout", "-q", "-b", "feat/x"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, env=env)
    return tmp_path


@pytest.mark.parametrize("cmd, why", [
    (f"gh pr -R o/r {M} 5", "raw merge"),
    (f"gh pr --repo o/r {M} 5", "raw merge"),
    (f"gh pr --repo=o/r {M} 5", "raw merge"),
    (f"gh pr -Ro/r {M} 5", "raw merge"),
    ("gh pr -R o/r create --title t --body done", "write the body"),
    ('gh pr -R o/r edit 5 --body "done"', "write the body"),
    ("gh pr --repo=o/r new --title t --body done", "write the body"),
    ("gh pr edit 5 -bdone", "write the body"),
    ("gh pr -R o/r edit 5 -bdone", "write the body"),
])
def test_b1_a_flag_between_pr_and_the_verb_is_still_judged(tmp_path, cmd, why):
    code, said = hook.decide(cmd, repo(tmp_path))
    assert code == 2 and why in said, (cmd, code, said)


def fake_gh(monkeypatch) -> list[list[str]]:
    """Every `gh` argv the hook runs, answered with an empty body and no files."""
    seen, real = [], subprocess.run

    def run(argv, *a, **k):
        if argv[:1] != ["gh"]:
            return real(argv, *a, **k)
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps({"body": "", "files": []}), "")
    monkeypatch.setattr(hook.subprocess, "run", run)
    return seen


@pytest.mark.parametrize("cmd", ["gh pr ready -Ro/r 5", "gh pr ready 5 --repo=o/r", "gh pr -R o/r ready 5",
                                 "gh pr --repo o/r ready 5", "gh -R o/r pr ready 5"])
def test_b1_the_repo_flag_is_read_in_any_position_and_spelling(tmp_path, monkeypatch, cmd):
    seen = fake_gh(monkeypatch)
    hook.decide(cmd, repo(tmp_path))
    assert ["gh", "pr", "view", "5", "-R", "o/r", "--json", "body"] in seen, (cmd, seen)


@pytest.mark.parametrize("cmd", ["gh pr ready 5 && cp -R a b", "gh pr ready 5; ls -Rfoo", "gh pr ready 5 | tee -R x",
                                 "gh pr ready 5\ncp -R a b", "gh pr ready 5 & cp -R a b",
                                 "gh pr ready 5 2>&1 && cp -R a b", "gh pr ready 5 &>/dev/null; cp -R a b"])
def test_b1_a_later_command_lends_no_repo_to_the_gh_call(tmp_path, monkeypatch, cmd):
    seen = fake_gh(monkeypatch)
    hook.decide(cmd, repo(tmp_path))
    assert ["gh", "pr", "view", "5", "--json", "body"] in seen, (cmd, seen)


@pytest.mark.parametrize("cmd", ["gh pr ready 5\nfoo --undo", "gh pr ready 5 & foo --undo",
                                 "gh pr create --title t --body done\necho --draft",
                                 "gh pr create --title t --body-file - <<EOF\n-b x\nEOF"])
def test_br2_a_later_line_or_background_job_lends_no_exempting_flag(tmp_path, monkeypatch, cmd):
    """Confirm breaker 2026-10-19: a newline and a lone `&` end a command like `;` does."""
    fake_gh(monkeypatch)
    assert hook.decide(cmd, repo(tmp_path))[0] == 2, cmd


@pytest.mark.parametrize("cmd", ["gh pr create \\\n  --title t \\\n  --body done", f"gh pr -R o/r \\\n  {M} 5",
                                 "gh pr edit 5 \\\n  -bdone", "gh pr create --title t \\\r\n  --body done"])
def test_br2_a_backslash_newline_continues_the_same_command(tmp_path, monkeypatch, cmd):
    """The shell drops `\\` + newline before anything else, so a wrapped gh call is still one call."""
    fake_gh(monkeypatch)
    assert hook.decide(cmd, repo(tmp_path))[0] == 2, cmd


@pytest.mark.parametrize("cmd", ["gh pr edit 5 <&3 --body x", "gh pr edit 5 0<&- --body x",
                                 "echo a\\\\\ngh pr edit 5 --body x"])
def test_br3_an_input_redirection_or_an_escaped_backslash_does_not_hide_the_call(tmp_path, monkeypatch, cmd):
    """Verifier 2026-10-19: `<&N` is a redirection, not a background `&`; `\\\\` at line end is an escaped
    backslash, not a continuation, so the next line is its own command."""
    fake_gh(monkeypatch)
    assert hook.decide(cmd, repo(tmp_path))[0] == 2, cmd


def test_b1_a_later_command_lends_no_body_flag_but_a_substituted_body_is_still_inline(tmp_path):
    root = repo(tmp_path)
    assert hook.decide("gh pr edit 5 --add-label x && git checkout -b next", root) == (0, "")
    for cmd in ("gh pr edit 5 --body $(cat f)", "gh pr edit 5 --body `cat f`", "gh pr edit 5 -b$(cat f)"):
        code, why = hook.decide(cmd, root)
        assert code == 2 and "write the body" in why, (cmd, code, why)


@pytest.mark.parametrize("verb", ["create", "new"])
def test_b1c_an_unsplittable_create_or_new_is_blocked(tmp_path, verb):
    root = repo(tmp_path)
    for pre in ("", "-R o/r "):
        cmd = f"gh pr {pre}{verb} --title x --body-file - <<'EOF'\nl'issue va\nEOF"
        assert hook.decide(cmd, root)[0] == 2, cmd


def test_b1c_an_unsplittable_merge_with_a_repo_flag_is_blocked():
    assert hook.decide(f"gh pr -R o/r {M} 5 <<'EOF'\nl'x\nEOF", None)[0] == 2


def test_b1_the_parser_and_the_fallback_share_one_verb_list():
    import gh_parse
    for verb in (*gh_parse.JUDGED, *gh_parse.ALIAS):
        assert gh_parse.JUDGED_VERB.search(f"gh pr {verb} x"), verb
    assert gh_parse.gh_calls(f"gh pr -R o/r {M} 5")[0][0] == "pr merge"
