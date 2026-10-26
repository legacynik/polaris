"""Third fresh critic and the founder's ruling, 2026-10-18: the hook is a tripwire, not a boundary.

Covered here: `gh pr ready` judged at all (finding 4); `-R/--repo` and `owner/repo#N` read the PR and
its issues from the repository they name (finding 5); `gh pr new` is `gh pr create`; a merge endpoint
with a non-numeric PR segment is a raw merge. And one declared limit kept declared: a `gh` call inside
a shell wrapper is not judged, and the bypass-test reference says so.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import pre_tool_hook as hook  # noqa: E402

FIX = HERE.parents[2] / "pr" / "tests" / "fixtures"
REFUSED = (FIX / "no-skill.md").read_text(encoding="utf-8")
CODA = ("## Cosa cambia\nx\n## Decisioni\nx\n## Prove\n![a](https://x/b/c.png?raw=true)\n"
        "## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")
GOOD = ("## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\n{close}\n## Criteri delle issue\n"
        "### #7 t\n| # | Criterio | Esito | Prova |\n|---|---|---|---|\n| 1 | a | ✅ | log |\n" + CODA)


def repo(tmp_path: Path) -> Path:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
    for args in (["init", "-q", "-b", "main"], ["commit", "-q", "--allow-empty", "-m", "base"],
                 ["checkout", "-q", "-b", "feat/x"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, env=env)
    return tmp_path


def fake_gh(monkeypatch, body: str) -> list[list[str]]:
    """Every `gh` argv the hook runs; `pr view` answers with `body` and no files."""
    seen, real = [], subprocess.run

    def run(argv, *a, **k):
        if argv[:1] != ["gh"]:
            return real(argv, *a, **k)
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps({"body": body, "files": []}), "")
    monkeypatch.setattr(hook.subprocess, "run", run)
    return seen


def issue_reads(monkeypatch) -> list[tuple[int, str | None]]:
    reads = []
    monkeypatch.setattr(hook.checker(), "leggi_issue", lambda n, r: reads.append((n, r)) or ["a"])
    return reads


def test_f4_ready_without_a_body_file_judges_the_published_body(tmp_path, monkeypatch):
    fake_gh(monkeypatch, REFUSED)
    monkeypatch.setattr(hook, "criteri_di", lambda n, *_: ["c"] * 9)
    code, why = hook.decide("gh pr ready 5", repo(tmp_path))
    assert code == 2 and "PR body" in why, why


def test_f5_ready_with_repo_flag_before_the_number_views_that_pr_in_that_repo(tmp_path, monkeypatch):
    seen = fake_gh(monkeypatch, GOOD.format(close="Closes #7"))
    issue_reads(monkeypatch)
    hook.decide("gh pr ready -R o/r 5", repo(tmp_path))
    assert ["gh", "pr", "view", "5", "-R", "o/r", "--json", "body"] in seen, seen


def test_f5_issues_are_read_from_the_named_repo(tmp_path, monkeypatch):
    fake_gh(monkeypatch, "")
    reads, root = issue_reads(monkeypatch), repo(tmp_path)
    for close, cmd, atteso in (("Closes #7", "gh pr edit 5 -R other/repo --body-file {f}", "other/repo"),
                               ("Closes other/repo#7", "gh pr edit 5 --body-file {f}", "other/repo"),
                               ("Closes x/y#7", "gh pr edit 5 -R o/r --body-file {f}", "x/y")):
        body = tmp_path / "b.md"
        body.write_text(GOOD.format(close=close), encoding="utf-8")
        reads.clear()
        hook.decide(cmd.format(f=shlex.quote(str(body))), root)
        assert reads == [(7, atteso)], (close, cmd, reads)


def test_b_pr_new_is_pr_create(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "criteri_di", lambda n, *_: ["c"] * 9)
    code, _ = hook.decide(f"gh pr new --title t --body-file {shlex.quote(str(FIX / 'no-skill.md'))}",
                          repo(tmp_path))
    assert code == 2


def test_b_a_merge_endpoint_with_a_non_numeric_pr_segment_is_a_raw_merge():
    for cmd in ("gh api -X PUT repos/o/r/pulls/$PR/" + "merge", "gh api -X PUT 'repos/o/r/pulls/{number}/" + "merge'"):
        assert hook.decide(cmd, None)[0] == 2, cmd


def test_declared_limit_a_wrapped_create_passes_and_is_documented(tmp_path):
    assert hook.decide('bash -c "gh pr create --title t --body done"', repo(tmp_path))[0] == 0
    ref = (HERE.parents[1] / "references" / "bypass-test.md").read_text(encoding="utf-8")
    for said in ("not a security boundary", "bash -c", "gh api", "babysit"):
        assert said in ref, said
