"""The hook reads whether a new PR touches the interface from the PR's own repository.

2026-10-19: `tocca_ui` diffed the process's working directory, not the repo the hook was judging.
The hook's own selfcheck turned red the day the vault it runs from committed an `.html` file: a
throwaway repo with no interface change was told it needed screenshots.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pre_tool_hook as hook  # noqa: E402

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
BODY = ("## In breve\nCambia x.\n\n**Decisione richiesta:** merge sì\n\nNessuna issue.\n\n## Cosa cambia\nx\n"
        "## Decisioni\nx\n## Prove\ntest verdi\n## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=ENV)


def repo(root: Path, ui_file: str | None) -> Path:
    """A repo on a feature branch whose base is origin/main; `ui_file` is the branch's one change."""
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "commit", "-q", "--allow-empty", "-m", "base")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(root, "checkout", "-q", "-b", "feat/x")
    (root / (ui_file or "notes.txt")).write_text("x\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")
    return root


def test_a_create_is_judged_on_the_target_repos_diff_not_the_working_directorys(tmp_path, monkeypatch):
    monkeypatch.chdir(repo(tmp_path / "elsewhere", "page.html"))
    target = repo(tmp_path / "target", None)
    (target / "body.md").write_text(BODY, encoding="utf-8")
    code, why = hook.decide(f"gh pr create --title t --body-file {target / 'body.md'}", target)
    assert code == 0, why


def test_an_interface_change_in_the_target_still_asks_for_screenshots(tmp_path, monkeypatch):
    monkeypatch.chdir(repo(tmp_path / "elsewhere", None))
    target = repo(tmp_path / "target", "page.html")
    (target / "body.md").write_text(BODY, encoding="utf-8")
    code, why = hook.decide(f"gh pr create --title t --body-file {target / 'body.md'}", target)
    assert code == 2 and "foto" in why, why
