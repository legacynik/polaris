"""session_commit.sh — a refused or aborted commit never leaves the session's paths staged
silently: they are unstaged, or named on stderr as STILL staged.

    python3 -m pytest skills-suite/end/tests/test_session_commit_index.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "scripts" / "session_commit.sh"
LOG = "team/acme-dev/sessions/2026-07-19.md"
# Both ways back out of the index fail: an index lock, a broken git — the cases `|| true` hid.
NO_UNSTAGE = 'git() { case "$1" in restore|reset) return 1 ;; esac; command git "$@"; }; '


def _repo(tmp: Path) -> Path:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp, check=True, capture_output=True)
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp / "README").write_text("init\n")
    git("add", "README")
    git("commit", "-qm", "init")
    (tmp / LOG).parent.mkdir(parents=True)
    (tmp / LOG).write_text("## checkpoint\n")
    return tmp


def _run(repo: Path, body: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'SESSION_COMMIT_LIB=1 . "{LIB}"; {body}'],
                          cwd=repo, capture_output=True, text=True)


def _staged(repo: Path) -> str:
    return subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()


def _hook_refuses(repo: Path) -> None:
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'the hook says no' >&2\nexit 1\n")
    hook.chmod(0o755)


def test_a_refused_commit_that_cannot_unstage_names_what_stays_staged(tmp_path):
    repo = _repo(tmp_path)
    _hook_refuses(repo)
    done = _run(repo, NO_UNSTAGE + f'commit_checkpoint "{LOG}"')
    assert done.returncode == 1, done.stderr
    assert LOG in _staged(repo), "fixture: the shim did not keep the path staged"
    assert "index restored" not in done.stderr, f"claimed a restore that never happened:\n{done.stderr}"
    assert "STILL STAGED" in done.stderr and LOG in done.stderr.split("STILL STAGED", 1)[1], \
        f"the staged paths were not named:\n{done.stderr}"


def test_a_forbidden_abort_leaves_none_of_the_session_paths_staged(tmp_path):
    repo = _repo(tmp_path)
    (repo / "cfg").mkdir()
    (repo / "cfg" / ".env.local").write_text("SECRET=x\n")
    done = _run(repo, f'commit_checkpoint "{LOG}" cfg')
    assert done.returncode == 2, done.stderr
    assert "forbidden file staged" in done.stderr
    assert _staged(repo) == "", f"the abort left paths staged for the next commit:\n{_staged(repo)}"


def test_a_forbidden_abort_that_cannot_unstage_names_what_stays_staged(tmp_path):
    repo = _repo(tmp_path)
    (repo / "cfg").mkdir()
    (repo / "cfg" / ".env.local").write_text("SECRET=x\n")
    done = _run(repo, NO_UNSTAGE + f'commit_checkpoint "{LOG}" cfg')
    assert done.returncode == 2, done.stderr
    tail = done.stderr.split("STILL STAGED", 1)
    assert len(tail) == 2 and "cfg/.env.local" in tail[1], \
        f"the forbidden file stayed staged without a word:\n{done.stderr}"


# The index cannot even be READ after the refused commit: an empty answer is not "nothing staged".
BLIND_INDEX = ('git() { case "$1" in restore|reset) return 1 ;; '
               'commit) command git "$@"; local r=$?; : > .diff-broken; return $r ;; '
               'diff) [ -f .diff-broken ] && return 128 ;; esac; command git "$@"; }; ')


def test_an_unreadable_index_is_never_reported_as_restored(tmp_path):
    repo = _repo(tmp_path)
    _hook_refuses(repo)
    done = _run(repo, BLIND_INDEX + f'commit_checkpoint "{LOG}"')
    assert done.returncode == 1, done.stderr
    assert "index restored" not in done.stderr, f"claimed a restore it could not check:\n{done.stderr}"
    assert "cannot read the index" in done.stderr, done.stderr


LESSON = "records/lessons/2026-10-24-a-lesson-abc123.md"
OCCURRENCES = "records/occurrences.jsonl"


def _records(repo: Path) -> None:
    (repo / "records" / "lessons").mkdir(parents=True)
    (repo / LESSON).write_text("---\ntitle: a lesson\n---\nbody\n")
    (repo / OCCURRENCES).write_text('{"lesson": "x"}\n')


def test_end_commits_the_lesson_records_lesson_record_writes(tmp_path):
    """Operating model §7: lessons are `records/lessons/*.md` + `records/occurrences.jsonl`."""
    repo = _repo(tmp_path)
    _records(repo)
    done = _run(repo, f'commit_end "{LOG}" "{repo / LESSON}" {OCCURRENCES}')
    assert done.returncode == 0, done.stderr
    shown = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=repo,
                           capture_output=True, text=True).stdout.split()
    assert {LOG, LESSON, OCCURRENCES} <= set(shown), shown


def test_a_foreign_staged_occurrences_ledger_is_refused_like_decisions(tmp_path):
    """The occurrences ledger is shared like `decisions.md`: pre-staged, it is another panel's."""
    repo = _repo(tmp_path)
    _records(repo)
    subprocess.run(["git", "add", OCCURRENCES], cwd=repo, check=True)
    done = _run(repo, f'commit_end "{LOG}" {OCCURRENCES}')
    assert done.returncode == 2, f"absorbed another panel's staged ledger:\n{done.stdout}{done.stderr}"
    assert OCCURRENCES in _staged(repo), "the foreign ledger was unstaged"
