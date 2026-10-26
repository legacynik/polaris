"""session_rake.py — the day's session logs reach the default branch, and the local default branch
stays fast-forwardable (founder, 2026-10-26).

Every test builds a bare origin and clones of it, runs the script from its public entry point and
looks at the exit code, the output and the git state. `gh` is a stub on PATH that logs its calls.

    pytest -q skills-suite/end/tests/test_session_rake.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "session_rake.py"
LOGIN = "acme-dev"
LOG23 = f"team/{LOGIN}/sessions/2026-10-23-@{LOGIN}.md"
LOG24 = f"team/{LOGIN}/sessions/2026-10-24-@{LOGIN}.md"
HANDOFF = f"team/{LOGIN}/handoff/2026-10-24.md"
RAKE = f"chore/sessions-{LOGIN}-{date.today().isoformat()}"
GH = """#!/bin/sh
echo "$*" >> "$GH_LOG"
case "$1 $2" in
  "pr list") [ -f "$GH_LOG.pr" ] && cat "$GH_LOG.pr" ;;
  "pr create") echo 7 > "$GH_LOG.pr"; echo "https://example.test/pull/7" ;;
esac
exit 0
"""
_clock = [1_790_000_000]


def _git_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return env


def _env(tmp: Path) -> dict:
    stub = tmp / "bin"
    if not stub.exists():
        stub.mkdir()
        (stub / "gh").write_text(GH)
        (stub / "gh").chmod(0o755)
    env = _git_env()
    env.update(PATH=f"{stub}{os.pathsep}{env['PATH']}", GH_LOG=str(tmp / "gh.log"))
    return env


def git(repo: Path, *args: str) -> str:
    _clock[0] += 60  # every commit one minute later: "newest" is never a tie
    env = _git_env()
    env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{_clock[0]} +0000"
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def commit(repo: Path, files: dict[str, str], msg: str = "change") -> str:
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(text)
    git(repo, "add", "--", *files)
    git(repo, "commit", "-qm", msg)
    return git(repo, "rev-parse", "HEAD")


def world(tmp: Path, config: str = "tracker:\n  github_repo: o/r\n") -> tuple[Path, Path]:
    """A bare origin on `main` holding a vault-shaped repo (config.yml at the root), and two
    clones: `work` is the contributor's checkout, `other` is everybody else pushing to origin."""
    git(tmp, "init", "-q", "--bare", "-b", "main", "origin.git")
    seed = tmp / "seed"
    git(tmp, "init", "-q", "-b", "main", "seed")
    commit(seed, {"config.yml": config, "README": "init\n", "NOTES": "notes\n"}, "init")
    git(seed, "push", "-q", str(tmp / "origin.git"), "main")
    for name in ("work", "other"):
        git(tmp, "clone", "-q", str(tmp / "origin.git"), name)
    git(tmp / "work", "config", "--local", "polaris.login", LOGIN)
    return tmp / "work", tmp / "other"


def upstream(other: Path, files: dict[str, str]) -> str:
    sha = commit(other, files, "upstream")
    git(other, "push", "-q", "origin", "main")
    return sha


def rake(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo,
                          env=_env(repo.parent), capture_output=True, text=True)


def _lines_with(out: str, needle: str) -> list[str]:
    return [line for line in out.splitlines() if needle in line]


# (a) ------------------------------------------------------------------------------------------

def test_plan_finds_session_commits_on_default_and_feature_branch_newest_wins(tmp_path):
    work, _ = world(tmp_path)
    old = commit(work, {LOG23: "v1\n"})
    git(work, "checkout", "-qb", "feat")
    new = commit(work, {LOG23: "v1\nv2\n"})
    other = commit(work, {LOG24: "x\n", HANDOFF: "h\n"})
    git(work, "checkout", "-q", "main")
    done = rake(work, "plan", "--no-fetch")
    assert done.returncode == 0, done.stdout + done.stderr
    on23 = _lines_with(done.stdout, LOG23)
    assert on23 and new[:10] in on23[0] and old[:10] not in on23[0], done.stdout
    assert other[:10] in _lines_with(done.stdout, LOG24)[0], done.stdout
    assert other[:10] in _lines_with(done.stdout, HANDOFF)[0], done.stdout
    carriers = _lines_with(done.stdout, "branches")
    assert carriers and "main" in carriers[0] and "feat" in carriers[0], done.stdout
    assert git(work, "rev-parse", "HEAD") == old, "plan is read-only"


# (b) ------------------------------------------------------------------------------------------

def test_a_mixed_commit_is_reported_and_not_raked(tmp_path):
    work, _ = world(tmp_path)
    git(work, "checkout", "-qb", "feat")
    mixed = commit(work, {LOG24: "x\n", "README": "feature\n"})
    done = rake(work, "plan", "--no-fetch")
    assert done.returncode == 0, done.stdout + done.stderr
    flagged = _lines_with(done.stdout, mixed[:10])
    assert flagged and "mixed" in flagged[0], done.stdout
    assert not _lines_with(done.stdout, LOG24), f"a mixed commit's session path was raked:\n{done.stdout}"


# (c) ------------------------------------------------------------------------------------------

def _remote(tmp: Path, *args: str) -> str:
    return git(tmp, "--git-dir", str(tmp / "origin.git"), *args)


def test_apply_pushes_one_branch_of_session_paths_on_origin_default(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    git(work, "checkout", "-qb", "feat")
    commit(work, {LOG23: "v1\nv2\n", "app.py": "feature\n"}, "mixed")
    commit(work, {LOG24: "x\n"})
    commit(work, {"app.py": "more feature\n"}, "feature only")
    git(work, "checkout", "-q", "main")
    tip = upstream(other, {"README": "moved on\n"})
    done = rake(work, "apply")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _remote(tmp_path, "rev-parse", f"{RAKE}^") == tip, "the rake branch is not based on origin/main"
    changed = _remote(tmp_path, "diff", "--name-only", tip, RAKE).split()
    assert sorted(changed) == sorted([LOG23, LOG24, ".gitattributes"]), changed  # + the union driver
    assert _remote(tmp_path, "show", f"{RAKE}:{LOG23}") == "v1", "the mixed commit's version was raked"
    calls = (tmp_path / "gh.log").read_text()
    assert calls.count("pr create") == 1 and "pr merge" not in calls, calls
    assert len(git(work, "worktree", "list").splitlines()) == 1, "the throwaway worktree was left"


def test_a_second_apply_the_same_day_updates_the_same_pr(tmp_path):
    work, _ = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    first = rake(work, "apply")
    assert first.returncode == 0, first.stdout + first.stderr
    pushed = _remote(tmp_path, "rev-parse", RAKE)
    commit(work, {LOG23: "v1\nv2\n"})
    second = rake(work, "apply")
    assert second.returncode == 0, second.stdout + second.stderr
    assert _remote(tmp_path, "merge-base", "--is-ancestor", pushed, RAKE) == "", "not a fast-forward"
    assert _remote(tmp_path, "show", f"{RAKE}:{LOG23}") == "v1\nv2"
    calls = (tmp_path / "gh.log").read_text()
    assert calls.count("pr create") == 1 and calls.count("pr edit") == 1, calls


def test_apply_merges_only_with_the_flag_and_the_config_key(tmp_path):
    for config, flag, merged in (("session:\n  rake_merge: true\n", [], False),
                                 ("tracker:\n  github_repo: o/r\n", ["--merge"], False),
                                 ("session:\n  rake_merge: true\n", ["--merge"], True)):
        tmp = tmp_path / f"{len(flag)}{merged}"
        tmp.mkdir()
        work, _ = world(tmp, config)
        commit(work, {LOG23: "v1\n"})
        done = rake(work, "apply", *flag)
        assert done.returncode == 0, done.stdout + done.stderr
        calls = (tmp / "gh.log").read_text()
        assert ("pr merge" in calls) is merged, f"{config!r} {flag}: {calls}"


def test_apply_with_nothing_to_rake_pushes_nothing(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    upstream(other, {LOG23: "v1\n"})
    done = rake(work, "apply")
    assert done.returncode == 0, done.stdout + done.stderr
    assert RAKE not in _remote(tmp_path, "branch", "--list"), "pushed a branch with nothing in it"
    assert not (tmp_path / "gh.log").exists(), "opened a PR with nothing in it"


# (d) ------------------------------------------------------------------------------------------

def test_sync_resets_a_default_branch_whose_extra_commits_are_upstream_session_logs(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    commit(work, {HANDOFF: "h\n"})
    upstream(other, {LOG23: "v1\n", HANDOFF: "h\n"})
    tip = upstream(other, {"README": "moved on\n"})
    done = rake(work, "sync")
    assert done.returncode == 0, done.stdout + done.stderr
    assert git(work, "rev-parse", "main") == tip
    assert (work / "README").read_text() == "moved on\n", "the working tree did not follow"


def test_sync_moves_the_ref_when_the_default_branch_is_not_checked_out(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    git(work, "checkout", "-qb", "feat")
    tip = upstream(other, {LOG23: "v1\n"})
    done = rake(work, "sync")
    assert done.returncode == 0, done.stdout + done.stderr
    assert git(work, "rev-parse", "main") == tip
    assert git(work, "rev-parse", "--abbrev-ref", "HEAD") == "feat"


def test_sync_refuses_when_the_default_branch_carries_a_non_session_commit(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    local = commit(work, {"README": "local work\n"})
    upstream(other, {LOG23: "v1\n"})
    done = rake(work, "sync")
    assert done.returncode == 1, done.stdout + done.stderr
    assert local[:10] in done.stdout + done.stderr, "the refusal does not name the commit"
    assert git(work, "rev-parse", "main") == local, "sync changed a branch it refused"


def test_sync_refuses_when_a_session_log_differs_upstream(tmp_path):
    work, other = world(tmp_path)
    local = commit(work, {LOG23: "v1\nonly here\n"})
    upstream(other, {LOG23: "v1\n"})
    done = rake(work, "sync")
    assert done.returncode == 1, done.stdout + done.stderr
    assert LOG23 in done.stdout + done.stderr, "the refusal does not name the path"
    assert git(work, "rev-parse", "main") == local
    assert (work / LOG23).read_text() == "v1\nonly here\n"


# (e) ------------------------------------------------------------------------------------------

def test_sync_never_discards_an_uncommitted_change(tmp_path):
    work, other = world(tmp_path)
    local = commit(work, {LOG23: "v1\n"})
    upstream(other, {LOG23: "v1\n"})
    upstream(other, {"README": "moved on\n"})
    (work / "README").write_text("mine, uncommitted\n")
    done = rake(work, "sync")
    assert done.returncode == 1, done.stdout + done.stderr
    assert (work / "README").read_text() == "mine, uncommitted\n", "an uncommitted change was lost"
    assert git(work, "rev-parse", "main") == local


def test_sync_keeps_an_uncommitted_change_the_reset_does_not_touch(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: "v1\n"})
    upstream(other, {LOG23: "v1\n"})
    tip = upstream(other, {"README": "moved on\n"})
    (work / "NOTES").write_text("mine, uncommitted\n")
    done = rake(work, "sync")
    assert done.returncode == 0, done.stdout + done.stderr
    assert git(work, "rev-parse", "main") == tip
    assert (work / "NOTES").read_text() == "mine, uncommitted\n"


# usage ----------------------------------------------------------------------------------------

def test_an_unknown_command_is_a_usage_error(tmp_path):
    work, _ = world(tmp_path)
    assert rake(work, "plan", "--no-fetch").returncode == 0, "fixture: a valid call must not be 2"
    assert rake(work, "rake-everything").returncode == 2


def test_a_stale_branch_never_rakes_an_older_version_over_origin(tmp_path):
    """A squash-merged branch kept around still carries yesterday's v1: origin holds v1+v2."""
    work, other = world(tmp_path)
    git(work, "checkout", "-qb", "stale")
    commit(work, {LOG23: "v1\n"})
    git(work, "checkout", "-q", "main")
    upstream(other, {LOG23: "v1\nv2\n"})
    done = rake(work, "plan")
    assert done.returncode == 0, done.stdout + done.stderr
    assert not [l for l in _lines_with(done.stdout, LOG23) if l.startswith("rake:")], done.stdout
    assert rake(work, "apply").returncode == 0
    assert RAKE not in _remote(tmp_path, "branch", "--list"), "raked an older log over origin's"
