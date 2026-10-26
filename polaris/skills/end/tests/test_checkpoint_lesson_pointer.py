"""checkpoint.sh verify — a `- Lesson:` pointer names a lesson RECORD (operating model §7), never a
heading in the retired `lessons.md`: `records/lessons/<id>.md` committed and clean, or a committed
line of `records/occurrences.jsonl` naming `<id>` — in this repository, then in the declared vault.

    python3 -m pytest skills-suite/end/tests/test_checkpoint_lesson_pointer.py
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "checkpoint.sh"
TODAY = f"{date.today():%Y-%m-%d}"
LESSON_ID = "2026-10-24-a-gate-that-cannot-fail-is-a-wish-abc123"
ENV = {**{k: v for k, v in os.environ.items() if k != "POLARIS_VAULT"},
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "POLARIS_SID": ""}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=ENV)


def _init(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", ".")
    for key, value in (("polaris.login", "probe"), ("user.email", "p@x.test"), ("user.name", "P")):
        _git(repo, "config", "--local", key, value)


def _commit(repo: Path, *paths: Path) -> None:
    _git(repo, "add", "--", *map(str, paths))
    _git(repo, "commit", "-qm", "x")


def _checkout(tmp: Path, entry: str) -> Path:
    """A checkout whose only open gate is the lesson pointer of `entry`."""
    _init(tmp)
    root = tmp / "_polaris"
    (root / "state").mkdir(parents=True)
    (root / "config.yml").write_text("")
    log = root / "team" / "probe" / "sessions" / f"{TODAY}-@probe.md"
    log.parent.mkdir(parents=True)
    log.write_text(f"## 10:00 — probe entry\n- Key context: x\n- Files: y\n{entry}")
    _commit(tmp, log)
    (root / "state" / "current.md").write_text(f"Updated: {TODAY} — @probe\n")
    return root


def _record(root: Path, lesson_id: str = LESSON_ID) -> Path:
    path = root / "records" / "lessons" / f"{lesson_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\ntitle: a gate that cannot fail is a wish\n---\nbody\n")
    return path


def _verify(tmp: Path) -> tuple[int, str]:
    done = subprocess.run(["bash", str(SCRIPT), "verify"], cwd=tmp, capture_output=True,
                          text=True, env=ENV)
    return done.returncode, done.stdout + done.stderr


def test_a_committed_record_id_passes(tmp_path):
    root = _checkout(tmp_path, f"- Lesson: {LESSON_ID}\n")
    _commit(tmp_path, _record(root))
    code, out = _verify(tmp_path)
    assert code == 0 and "checkpoint: verified" in out, out


def test_an_uncommitted_record_fails_naming_the_id(tmp_path):
    root = _checkout(tmp_path, f"- Lesson: {LESSON_ID}\n")
    _record(root)
    code, out = _verify(tmp_path)
    assert code == 1 and f"FAIL: Lesson record '{LESSON_ID}'" in out, out


def test_an_occurrence_id_passes(tmp_path):
    root = _checkout(tmp_path, f"- Lesson: {LESSON_ID}\n")
    ledger = root / "records" / "occurrences.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"record": LESSON_ID, "family": "x", "date": TODAY}) + "\n")
    _commit(tmp_path, ledger)
    code, out = _verify(tmp_path)
    assert code == 0 and "checkpoint: verified" in out, out


def test_an_unknown_id_fails_naming_it(tmp_path):
    _checkout(tmp_path, "- Lesson: never-recorded\n")
    code, out = _verify(tmp_path)
    assert code == 1 and "FAIL: Lesson record 'never-recorded'" in out, out


def test_a_heading_in_lessons_md_no_longer_satisfies_it(tmp_path):
    root = _checkout(tmp_path, "#lezione\n- Lesson: a retired heading\n")
    legacy = root / "lessons.md"
    legacy.write_text(f"## {TODAY} — a retired heading (probe)\nbody\n")
    _commit(tmp_path, legacy)
    code, out = _verify(tmp_path)
    assert code == 1 and "FAIL: Lesson record 'a retired heading'" in out, out


def test_a_tag_with_no_pointer_still_fails(tmp_path):
    _checkout(tmp_path, "#lezione learned something\n")
    code, out = _verify(tmp_path)
    assert code == 1 and "#lezione has no Lesson record pointer" in out, out


def test_a_record_committed_in_the_declared_vault_passes(tmp_path):
    repo, vault = tmp_path / "repo", tmp_path / "vault"
    _checkout(repo, f"- Lesson: {LESSON_ID}\n")
    _init(vault)
    _commit(vault, _record(vault))
    _git(repo, "config", "--local", "polaris.vault", str(vault))
    code, out = _verify(repo)
    assert code == 0 and "checkpoint: verified" in out, out
