#!/usr/bin/env python3
"""session_rake.py — bring every day's session log to the default branch the same day.

`session_commit.sh` commits session logs where the panel runs (2026-09-04). Two costs followed: on
a repository's main checkout the checkpoints pile up on the LOCAL default branch until `git pull`
no longer fast-forwards, and on a feature branch the day's log waits days for that branch to merge.
The rake fixes both without touching where a checkpoint lands (founder, 2026-10-26):

  plan   read-only. Commits on ANY local branch, not on origin/<default>, that touch only
         `<root>/team/<login>/{sessions,handoff}/`: per path the newest version (commit, branch),
         the branches that carry them, and every commit that ALSO touches other paths ("mixed").
  apply  the newest version of each path that origin/<default> does not already hold, committed
         pathspec-only in a throwaway worktree on origin/<default>, pushed as
         `chore/sessions-<login>-<date>`, ONE PR opened or updated. Merged only with `--merge`
         AND `session.rake_merge: true` in config.yml (a repo whose hook routes merges through
         /ship keeps the default, false).
  sync   the local default branch only: when every commit it has beyond origin/<default> is a
         session-only commit whose paths are identical upstream, `reset --keep` it there (main
         worktree) or move the ref (`branch -f`, not checked out). Anything else changes nothing.

ROOT and LOGIN resolve as in start/scripts/resume_paths.sh: `<top>/_polaris` when it holds
config.yml, else the top (the repo IS the vault); `git config --local polaris.login`, else gh.
Exit: 0 done or nothing to do · 1 refused, with the reason · 2 usage.
    session_rake.py plan|apply|sync [--no-fetch] [--merge] | --selfcheck
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace


class Refused(Exception):
    pass


def git(*args: str, check: bool = True) -> str:
    done = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and done.returncode:
        raise Refused(f"git {' '.join(args[:3])}: {(done.stderr or done.stdout).strip()}")
    return done.stdout.strip() if done.returncode == 0 else ""


def gh(*args: str, cwd: str) -> str:
    try:
        done = subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True)
    except OSError:
        raise Refused("gh is not available — the branch is pushed, open the PR by hand")
    if done.returncode:
        raise Refused(f"gh {' '.join(args[:2])}: {(done.stderr or done.stdout).strip()}")
    return done.stdout.strip()


def blob_id(rev_path: str) -> str:
    return git("rev-parse", "--verify", "-q", rev_path, check=False)


def files_of(sha: str) -> list[str]:
    out = git("diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "--root", sha)
    return [f for f in out.split("\0") if f]


def default_branch() -> str:
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
    if head.startswith("origin/"):
        return head[len("origin/"):]
    for c in ("main", "master"):
        if blob_id(f"refs/remotes/origin/{c}"):
            return c
    raise Refused("no origin/<default> branch — nothing to rake against")


def context(fetch: bool) -> SimpleNamespace:
    top = Path(git("rev-parse", "--show-toplevel"))
    rel = "_polaris/" if (top / "_polaris" / "config.yml").is_file() else ""
    if not (top / rel / "config.yml").is_file():
        raise Refused(f"no Polaris contract under {top}")
    login = git("config", "--local", "--get", "polaris.login", check=False)
    if not login:
        try:
            login = subprocess.run(["gh", "api", "user", "--jq", ".login"],
                                   capture_output=True, text=True).stdout.strip()
        except OSError:
            login = ""
    if not login:
        raise Refused("cannot resolve login — git config --local polaris.login <login>")
    if fetch:
        git("fetch", "-q", "origin")
    d = default_branch()
    return SimpleNamespace(top=top, rel=rel, config=top / rel / "config.yml", login=login, default=d,
                           base=f"origin/{d}", prefixes=tuple(f"{rel}team/{login}/{k}/"
                                                              for k in ("sessions", "handoff")))


ENTRY = re.compile(r"^## (\d{1,2}):(\d{2}) — ", re.M)
# The contract root's .gitattributes: the merge after a rake (a feature branch whose log already
# reached main) adds both sides' lines instead of conflicting. Relative to the file's directory.
UNION_ATTRS = ("team/*/sessions/*.md merge=union", "team/*/handoff/*.md merge=union")


def text_at(rev_path: str) -> str | None:
    done = subprocess.run(["git", "cat-file", "blob", rev_path], capture_output=True)
    return done.stdout.decode("utf-8", "surrogateescape") if done.returncode == 0 else None


def split(text: str) -> tuple[str, list[str]]:
    """(preamble, entries): a session log is append-only, one `## HH:MM — ` entry at a time."""
    starts = [m.start() for m in ENTRY.finditer(text)]
    if not starts:
        return text, []
    return text[:starts[0]], [text[a:b].rstrip() for a, b in zip(starts, starts[1:] + [len(text)])]


def covered(text: str, upstream: str | None) -> bool:
    """Every entry of `text` is already in `upstream`: nothing of it would be lost."""
    pre, entries = split(text)
    up_pre, up_entries = split(upstream or "")
    return set(entries) <= set(up_entries) and (not pre.strip() or pre.strip() == up_pre.strip())


def union(texts: list[str]) -> str:
    """Every entry once, in time order (a stable sort: on a tie, origin's order first)."""
    pre = next((split(t)[0] for t in texts if split(t)[0].strip()), "")
    entries: list[str] = []
    for t in texts:
        entries += [e for e in split(t)[1] if e not in entries]
    entries.sort(key=lambda e: tuple(int(x) for x in ENTRY.match(e).groups()))
    return (pre.rstrip() + "\n\n" if pre.strip() else "") + "\n\n".join(entries) + "\n"


def scan(ctx) -> tuple[dict, dict, list, list]:
    """(todo {path: (content, [sha])} not yet upstream, session {sha: [branch]}, mixed [sha],
    older [path]). A log made of entries is the union of origin and each branch's newest
    version; any other file, the newest version, never one older than origin's.
    Only commits touching a session path are listed at all: a stale branch costs one rev-list."""
    carriers: dict[str, list[str]] = {}
    for b in git("for-each-ref", "--format=%(refname:short)", "refs/heads/").split():
        for sha in git("rev-list", "--no-merges", b, "--not", ctx.base, "--", *ctx.prefixes).split():
            carriers.setdefault(sha, []).append(b)
    newest, per_branch, mixed, session = {}, {}, [], {}
    for sha, branches in carriers.items():
        files = files_of(sha)
        ours = [f for f in files if f.startswith(ctx.prefixes)]
        if not ours:
            continue
        if len(ours) < len(files):
            mixed.append(sha)
            continue
        session[sha] = branches
        ct = int(git("show", "-s", "--format=%ct", sha))
        for f in ours:
            if f not in newest or ct > newest[f][0]:
                newest[f] = (ct, sha)
            for b in branches:
                if ct > per_branch.setdefault(f, {}).get(b, (0, ""))[0]:
                    per_branch[f][b] = (ct, sha)
    todo, older = {}, []
    for p, (ct, sha) in sorted(newest.items()):
        up = text_at(f"{ctx.base}:{p}")
        tips = sorted(set(per_branch[p].values()))
        versions = [(s, text_at(f"{s}:{p}")) for _, s in tips]
        if any(t and split(t)[1] for _, t in versions):
            new = [(s, t) for s, t in versions if t is not None and not covered(t, up)]
            if new:
                todo[p] = (union([up or ""] + [t for _, t in new]), [s for s, _ in new])
            continue
        if not blob_id(f"{sha}:{p}") or blob_id(f"{sha}:{p}") == blob_id(f"{ctx.base}:{p}"):
            continue  # deleted here, or already upstream byte for byte
        # A kept, squash-merged branch still carries an old version: never rake it over a newer one.
        if int(git("log", "-1", "--format=%ct", ctx.base, "--", p) or 0) >= ct:
            older.append(p)
            continue
        todo[p] = (text_at(f"{sha}:{p}"), [sha])
    return todo, session, mixed, older


def plan(ctx) -> tuple[dict, dict]:
    todo, session, mixed, older = scan(ctx)
    for p, (_, shas) in todo.items():
        print(f"rake: {p} <- {sources(shas, session)}")
    for p in older:
        print(f"older than {ctx.base} — not raked: {p}")
    for sha in mixed:
        subject = git("show", "-s", "--format=%s", sha)
        print(f"mixed — not raked: {sha[:10]} {subject!r} touches session and other paths")
    if session:
        print(f"branches with session commits: {', '.join(sorted({b for v in session.values() for b in v}))}")
    if not todo:
        print(f"nothing to rake — origin/{ctx.default} holds every session path")
    return todo, session


def sources(shas: list[str], session: dict) -> str:
    return ", ".join(f"{s[:10]} ({', '.join(session[s])})" for s in shas)


def rake_merge(config: Path) -> bool:
    """`session.rake_merge` — line-based like review_tier.py: one flat key, no YAML loader."""
    inside = False
    for line in config.read_text(errors="replace").splitlines():
        if re.match(r"^\S", line):
            inside = line.split("#")[0].strip() == "session:"
            continue
        m = re.match(r"^\s+rake_merge:\s*(\S+)", line) if inside else None
        if m:
            return m.group(1).strip("\"'").lower() == "true"
    return False


def apply(ctx, merge: bool) -> int:
    todo, session = plan(ctx)
    if not todo:
        return 0
    today = date.today().isoformat()
    branch = f"chore/sessions-{ctx.login}-{today}"
    start = ctx.base
    if git("ls-remote", "--heads", "origin", branch):  # same day again: the PR's branch grows
        git("fetch", "-q", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
        start = f"origin/{branch}"
    wt = tempfile.mkdtemp(prefix="session-rake-")
    try:
        git("worktree", "add", "-q", "--detach", wt, start)
        for p, (content, _) in todo.items():
            (Path(wt) / p).parent.mkdir(parents=True, exist_ok=True)
            (Path(wt) / p).write_bytes(content.encode("utf-8", "surrogateescape"))
        paths = list(todo)
        attrs = Path(wt) / ctx.rel / ".gitattributes"
        have = attrs.read_text().splitlines() if attrs.is_file() else []
        missing = [line for line in UNION_ATTRS if line not in have]
        if missing:
            attrs.write_text("".join(f"{line}\n" for line in have + missing))
            paths.append(f"{ctx.rel}.gitattributes")
        git("-C", wt, "add", "--", *paths)
        if git("-C", wt, "diff", "--cached", "--name-only", "--", *paths):
            git("-C", wt, "commit", "-q", "-m", f"docs(sessions): @{ctx.login} session logs {today}",
                "--", *paths)
            git("-C", wt, "push", "-q", "origin", f"HEAD:refs/heads/{branch}")
    finally:
        git("worktree", "remove", "--force", wt, check=False)
        shutil.rmtree(wt, ignore_errors=True)
        git("worktree", "prune", check=False)
    body = (f"Session logs of @{ctx.login} raked to `{ctx.default}` by `end` (docs only).\n\n"
            + "\n".join(f"- `{p}` ← {sources(shas, session)}" for p, (_, shas) in todo.items()))
    cwd = str(ctx.top)
    number = gh("pr", "list", "--head", branch, "--state", "open", "--json", "number",
                "--jq", ".[0].number // empty", cwd=cwd)
    if number:
        gh("pr", "edit", number, "--body", body, cwd=cwd)
        print(f"PR #{number} updated: {branch}")
    else:
        print(gh("pr", "create", "--base", ctx.default, "--head", branch,
                 "--title", f"docs(sessions): @{ctx.login} session logs {today}", "--body", body, cwd=cwd))
    if merge and rake_merge(ctx.config):
        gh("pr", "merge", branch, "--squash", "--delete-branch", cwd=cwd)
        print(f"merged: {branch}")
    elif merge:
        print("not merged — session.rake_merge is not true in config.yml; the PR stays open")
    return 0


def upstream_holds(mine: str | None, up: str | None) -> bool:
    """A log whose entries are all upstream counts as upstream — the same rule `apply` rakes by."""
    return bool(mine and up and split(mine)[1] and covered(mine, up))


def sync(ctx) -> int:
    local = f"refs/heads/{ctx.default}"
    extra = git("rev-list", local, "--not", ctx.base).split() if blob_id(local) else []
    if not extra:
        print(f"{ctx.default} has nothing beyond {ctx.base} — nothing to sync")
        return 0
    touched = set()
    for sha in extra:
        if len(git("rev-list", "--parents", "-n1", sha).split()) > 2:
            raise Refused(f"{sha[:10]} is a merge commit on {ctx.default} — nothing changed")
        files = files_of(sha)
        other = [f for f in files if not f.startswith(ctx.prefixes)]
        if other:
            raise Refused(f"{sha[:10]} on {ctx.default} touches {other[0]}, not a session path "
                          "— nothing changed")
        touched.update(files)
    differ = [p for p in sorted(touched) if blob_id(f"{local}:{p}") != blob_id(f"{ctx.base}:{p}")
              and not upstream_holds(text_at(f"{local}:{p}"), text_at(f"{ctx.base}:{p}"))]
    if differ:
        raise Refused(f"differs from {ctx.base}: {', '.join(differ)} — rake it (apply) and merge "
                      "first; nothing changed")
    worktrees = git("worktree", "list", "--porcelain").split("\n\n")
    holders = [w.splitlines()[0][len("worktree "):] for w in worktrees if f"branch {local}" in w]
    if holders and holders[0] == worktrees[0].splitlines()[0][len("worktree "):]:
        git("-C", holders[0], "reset", "--keep", ctx.base)
    elif holders:
        raise Refused(f"{ctx.default} is checked out in {holders[0]} — run sync there; nothing changed")
    else:
        git("branch", "-f", ctx.default, ctx.base)
    print(f"{ctx.default} -> {ctx.base}: {len(extra)} session commit(s) already upstream dropped")
    return 0


def selfcheck() -> int:
    """The three answers sync can give, on a throwaway origin and clone — the real script, run."""
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    log = "team/probe/sessions/2026-10-26-@probe.md"
    with tempfile.TemporaryDirectory() as d:
        def run(cwd, *a, script=False):
            cmd = [sys.executable, __file__, *a] if script else ["git", *a]
            return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)

        def put(repo, path, text, push=False):
            (Path(repo) / path).parent.mkdir(parents=True, exist_ok=True)
            (Path(repo) / path).write_text(text)
            run(repo, "add", "--", path)
            run(repo, "commit", "-qm", path)
            if push:
                run(repo, "push", "-q", "origin", "HEAD:main")
            return run(repo, "rev-parse", "HEAD").stdout.strip()

        run(d, "init", "-q", "--bare", "-b", "main", "o.git")
        run(d, "init", "-q", "-b", "main", "seed")
        run(f"{d}/seed", "remote", "add", "origin", f"{d}/o.git")
        put(f"{d}/seed", "config.yml", "session:\n  rake_merge: false\n", push=True)
        run(d, "clone", "-q", f"{d}/o.git", "w")
        w = f"{d}/w"
        run(w, "config", "--local", "polaris.login", "probe")
        put(w, log, "only here\n")
        cases = [("a local-only log is raked", "rake: " + log in run(w, "plan", script=True).stdout)]
        put(f"{d}/seed", log, "only here\n", push=True)
        pinned = put(w, "README", "local work\n")
        cases.append(("a non-session commit refuses sync",
                      run(w, "sync", script=True).returncode == 1
                      and run(w, "rev-parse", "main").stdout.strip() == pinned))
        run(w, "reset", "-q", "--keep", "HEAD~1")
        done = run(w, "sync", script=True)
        cases.append(("an upstream session log is dropped",
                      done.returncode == 0 and run(w, "rev-parse", "main").stdout
                      == run(w, "rev-parse", "origin/main").stdout))
    for name, ok in cases:
        print(("ok   " if ok else "FAIL ") + name)
    return 0 if all(ok for _, ok in cases) else 1


def main() -> int:
    if sys.argv[1:] == ["--selfcheck"]:
        return selfcheck()
    ap = argparse.ArgumentParser(prog="session_rake.py")
    ap.add_argument("command", choices=("plan", "apply", "sync"))
    ap.add_argument("--no-fetch", action="store_true", help="skip `git fetch origin`")
    ap.add_argument("--merge", action="store_true",
                    help="apply: merge the PR, only where config.yml sets session.rake_merge: true")
    a = ap.parse_args()
    try:
        ctx = context(fetch=not a.no_fetch)
        if a.command == "plan":
            plan(ctx)
            return 0
        return apply(ctx, a.merge) if a.command == "apply" else sync(ctx)
    except Refused as why:
        print(f"session_rake {a.command}: refused — {why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
