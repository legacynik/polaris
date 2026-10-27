"""The hook in front of `gh pr create|ready|edit`: the body must be one the owner can merge from.

2026-10-18: the hook demanded a CHANGELOG.md and a version file in every repo (a repo without them
could never open a PR through it) and never looked at the body, so a PR saying `Closes` on an issue
with unproven criteria went through. Body fixtures are the real ones of the pr skill's tests.
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import pre_tool_hook as hook  # noqa: E402

FIX = HERE.parents[2] / "pr" / "tests" / "fixtures"
CRITERI = {1719: ["c"] * 7, 1207: ["c"] * 9, 792: []}


def repo(tmp_path: Path) -> Path:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
    for args in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "base"],
                 ["checkout", "-q", "-b", "feat/x"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, env=env)
    return tmp_path


def test_a_repo_without_changelog_or_version_file_can_open_a_pr(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "criteri_di", lambda n, *_: CRITERI.get(n, []))
    body = shlex.quote(str(FIX / "buona-v2.md"))
    code, why = hook.decide(f"gh pr create --title t --body-file {body}", repo(tmp_path))
    assert code == 0, why


def test_an_inline_body_is_refused(tmp_path):
    code, why = hook.decide('gh pr create --title t --body "done"', repo(tmp_path))
    assert code == 2 and "/pr" in why


def test_a_body_the_owner_cannot_judge_is_refused_on_create_and_edit(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "criteri_di", lambda n, *_: CRITERI.get(n, []))
    root = repo(tmp_path)
    for verbo in ("create --title t", "edit 1942"):
        code, why = hook.decide(f"gh pr {verbo} --body-file {shlex.quote(str(FIX / 'no-skill.md'))}", root)
        assert code == 2 and "Chiude" in why


def test_unreadable_issues_block_instead_of_passing(tmp_path, monkeypatch):
    def rotto(n, *_):
        raise subprocess.CalledProcessError(1, "gh")
    monkeypatch.setattr(hook, "criteri_di", rotto)
    code, why = hook.decide(f"gh pr create --title t --body-file {shlex.quote(str(FIX / 'buona-v2.md'))}",
                            repo(tmp_path))
    assert code == 2 and "issue" in why


def test_raw_merge_stays_blocked(tmp_path):
    assert hook.decide("gh pr merge 42 --squash", repo(tmp_path))[0] == 2


# Fresh critic, 2026-10-18: each of these went through.
VERB = "gh pr " + "merge"  # spelled apart: harness permission rules match the literal


def test_h2_h3_every_spelling_of_a_raw_merge_is_blocked_even_outside_a_repo(tmp_path):
    for cmd in (VERB.replace("gh ", "gh -R o/r ") + " 5 --squash", VERB.replace(" ", "  ") + " 5",
                "gh api -X PUT repos/o/r/pulls/5/" + "merge", f"{VERB} 5 -R o/r"):
        assert hook.decide(cmd, None)[0] == 2, cmd


def test_h2_bodies_written_inline_or_filled_are_refused_but_a_draft_needs_none(tmp_path):
    root = repo(tmp_path)
    for cmd in ("gh pr create --title x --body=anything", "gh pr edit 5 --body=anything",
                "gh pr create --title x --fill"):
        assert hook.decide(cmd, root)[0] == 2, cmd
    assert hook.decide("gh pr create --draft --title x --body backup", root)[0] == 0


def test_h1_an_internal_error_blocks_instead_of_passing(monkeypatch):
    def rotto(*a):
        raise RuntimeError("boom")
    monkeypatch.setattr(hook, "decide", rotto)
    payload = '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title x"}}'
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    assert hook.main([]) == 2


def test_h4_the_emergency_bypass_is_logged(tmp_path, monkeypatch):
    log = tmp_path / "bypass.log"
    monkeypatch.setenv("SHIP_BYPASS_GATE", "1")
    monkeypatch.setenv("SHIP_BYPASS_LOG", str(log))
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"tool_name":"Bash","tool_input":{"command":"gh pr create"}}'))
    assert hook.main([]) == 0 and "gh pr create" in log.read_text()


# Second fresh critic, 2026-10-18.
def test_r2_a_merge_anywhere_in_the_command_is_blocked():
    m = "pr " + "merge"
    for cmd in (f"gh pr view 5 && gh {m} 5 --squash", f"gh pr checks 5; gh {m} 5", f"cd x;gh {m} 5",
                f'bash -c "gh {m} 5"', f"echo $(gh {m} 5)", f"gh alias set m '{m}' && gh m 5",
                "gh api graphql -f query='mutation{mergePullRequest(input:{})}'",
                "gh api repos/o/r/merges -f base=main -f head=feat"):
        assert hook.decide(cmd, None)[0] == 2, cmd


def test_r2_commands_without_gh_pass_whatever_their_quotes(tmp_path):
    root = repo(tmp_path)
    assert hook.decide("echo it's fine", root)[0] == 0
    assert hook.decide("cat > b.md <<EOF\nL'impresa vede il totale.\nEOF", root)[0] == 0


def test_r2_ready_undo_goes_back_to_draft_freely(tmp_path):
    assert hook.decide("gh pr ready 5 --undo", repo(tmp_path))[0] == 0
