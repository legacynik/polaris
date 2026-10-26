"""session_rake.py — a session log is append-only, so its versions are combined by entry, never
chosen: every `## HH:MM — ` entry from origin and from each branch survives, once, in time order.
And the merge that follows the rake (a feature branch whose log was raked to main) never
conflicts: the rake carries `merge=union` for session logs and handoffs in the contract root.

    pytest -q skills-suite/end/tests/test_session_rake_union.py
"""
from __future__ import annotations

import subprocess

from test_session_rake import LOG23, LOGIN, RAKE, _remote, commit, git, rake, upstream, world


def entry(hhmm: str, what: str) -> str:
    return f"## {hhmm} — {what} · wt: x · branch: y\n- Done: {what}\n"


def log(*entries: str) -> str:
    return "# session log\n\n" + "\n".join(entries)


def test_two_branches_appending_to_one_log_both_survive_the_rake(tmp_path):
    work, other = world(tmp_path)
    upstream(other, {LOG23: log(entry("08:00", "upstream"))})
    git(work, "fetch", "-q", "origin")
    git(work, "checkout", "-qb", "feat", "origin/main")
    commit(work, {LOG23: log(entry("08:00", "upstream"), entry("11:00", "feature"))})
    git(work, "checkout", "-q", "main")
    git(work, "merge", "-q", "--ff-only", "origin/main")
    commit(work, {LOG23: log(entry("08:00", "upstream"), entry("09:30", "main"))})
    done = rake(work, "apply")
    assert done.returncode == 0, done.stdout + done.stderr
    raked = _remote(tmp_path, "show", f"{RAKE}:{LOG23}")
    heads = [line[3:8] for line in raked.splitlines() if line.startswith("## ")]
    assert heads == ["08:00", "09:30", "11:00"], f"entries lost, doubled or out of order:\n{raked}"


def test_a_local_log_whose_entries_are_all_upstream_is_not_raked(tmp_path):
    work, other = world(tmp_path)
    upstream(other, {LOG23: log(entry("09:00", "a"), entry("10:00", "b"))})
    commit(work, {LOG23: log(entry("09:00", "a"))})  # committed AFTER origin's, and a subset of it
    done = rake(work, "plan")
    assert done.returncode == 0, done.stdout + done.stderr
    assert not [l for l in done.stdout.splitlines() if l.startswith("rake:")], done.stdout


def test_sync_counts_a_log_whose_entries_are_all_upstream_as_upstream(tmp_path):
    work, other = world(tmp_path)
    commit(work, {LOG23: log(entry("09:00", "a"))})
    tip = upstream(other, {LOG23: log(entry("09:00", "a"), entry("10:00", "b"))})
    done = rake(work, "sync")
    assert done.returncode == 0, done.stdout + done.stderr
    assert git(work, "rev-parse", "main") == tip


def test_a_feature_branch_merges_cleanly_after_its_log_was_raked(tmp_path):
    work, other = world(tmp_path)
    git(work, "checkout", "-qb", "feat")
    commit(work, {LOG23: log(entry("09:00", "feature"))})
    assert rake(work, "apply").returncode == 0
    git(other, "pull", "-q", "--no-rebase", "origin", RAKE)            # the rake PR merges
    commit(other, {LOG23: git(other, "show", f"HEAD:{LOG23}") + "\n\n" + entry("10:00", "main")})
    git(other, "push", "-q", "origin", "main")
    commit(work, {LOG23: log(entry("09:00", "feature"), entry("11:00", "feature again"))})
    git(work, "push", "-q", "origin", "feat")
    git(other, "fetch", "-q", "origin")
    merged = subprocess.run(["git", "merge", "--no-edit", "origin/feat"], cwd=other,
                            capture_output=True, text=True)
    assert merged.returncode == 0, f"the feature merge conflicted:\n{merged.stdout}{merged.stderr}"
    text = (other / LOG23).read_text()
    for what in ("feature", "main", "feature again"):
        assert text.count(f"— {what} ·") == 1, f"{what!r} lost or doubled:\n{text}"


def test_the_union_attribute_lands_in_a_nested_contract_root(tmp_path):
    work, _ = world(tmp_path)
    (work / "_polaris").mkdir()
    git(work, "mv", "config.yml", "_polaris/config.yml")
    git(work, "commit", "-qm", "contract under _polaris")
    git(work, "push", "-q", "origin", "main")
    nested = f"_polaris/{LOG23}"
    commit(work, {nested: log(entry("09:00", "a"))})
    assert rake(work, "apply").returncode == 0
    git(work, "fetch", "-q", "origin")
    git(work, "checkout", "-q", f"origin/{RAKE}")
    attr = git(work, "check-attr", "merge", "--", nested, f"_polaris/team/{LOGIN}/handoff/2026-10-23.md")
    assert attr.count("merge: union") == 2, attr
