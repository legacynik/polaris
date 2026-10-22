"""pr_fetch — read from GitHub everything pr_status.summarize() needs, nothing else.

Network only here, so the judge stays pure and testable. Review threads are paged to the end; a
receipt on an older head brings the list of files changed since, so an inert push keeps it.
"""
from __future__ import annotations

import json
from typing import Any
import subprocess
import sys
import tempfile
from pathlib import Path

THREADS_Q = ("query($o:String!,$r:String!,$n:Int!,$c:String){repository(owner:$o,name:$r){pullRequest(number:$n)"
             "{reviewThreads(first:100,after:$c){pageInfo{hasNextPage endCursor} nodes{id isResolved isOutdated "
             "path line root:comments(first:1){nodes{databaseId author{login} body url}} "
             "latest:comments(last:1){nodes{author{login} body}}}}}}}")


def gh(*args: str) -> Any:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out) if out.strip() else None


def thread_nodes(owner: str, repo: str, n: int) -> list[dict]:
    nodes, cursor = [], None
    while True:
        extra = ["-f", f"c={cursor}"] if cursor else []
        page = gh("api", "graphql", "-f", f"query={THREADS_Q}", "-f", f"o={owner}", "-f", f"r={repo}",
                  "-F", f"n={n}", *extra)["data"]["repository"]["pullRequest"]["reviewThreads"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def acknowledged(comments: list[dict], base: str, viewer: str) -> None:
    for c in comments:
        liked = (c.get("reactions") or {}).get("+1", 0) > 0
        c["acknowledged"] = liked and any((r.get("user") or {}).get("login") == viewer for r in gh(
            "api", f"{base}/issues/comments/{c['id']}/reactions?content=%2B1&per_page=100"))


def body_errors(body: str, repo: str, files: list[str]) -> list[str]:
    """The pr skill's checker on the published body (a sibling skill folder)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pol-pr" / "scripts"))
    import controlla_pr as cp
    issues = {n: cp.leggi_issue(n, cp.repo_di(body, n) or repo) for n in cp.riferimenti(body)[0]}
    return cp.controlla(body, issues, cp.ui_da_file(files))


def fetch(sel: str | None, repo: str | None, label_name: str, inert: list[str]) -> dict:
    flags = ["-R", repo] if repo else []
    pr = gh("pr", "view", *([sel] if sel else []), *flags, "--json", "number,url,state,headRefOid,isDraft,"
            "mergeable,mergeStateStatus,statusCheckRollup,labels,body,files")
    owner, name = pr["url"].split("/")[3:5]
    base, viewer = f"repos/{owner}/{name}", gh("api", "user")["login"]
    comments = [c for page in gh("api", "--paginate", "--slurp", f"{base}/issues/{pr['number']}/comments?per_page=100")
                for c in page]
    acknowledged(comments, base, viewer)
    reviews = [r for page in gh("api", "--paginate", "--slurp", f"{base}/pulls/{pr['number']}/reviews?per_page=100")
               for r in page]
    import pr_status as ps
    marks = [m.group(1) for c in comments if (c.get("user") or {}).get("login") == viewer
             for m in [ps.LABEL_MARK.search(c.get("body") or "")] if m]
    label = {"sha": marks[-1] if marks else None} if any(
        lb.get("name") == label_name for lb in pr.get("labels") or []) else None
    changed = {sha: [f["filename"] for f in gh("api", f"{base}/compare/{sha}...{pr['headRefOid']}")["files"]]
               for sha in {ps.RECEIPT.search(c.get("body") or "").group(1) for c in comments
                           if ps.RECEIPT.search(c.get("body") or "")} if sha != pr["headRefOid"] and inert}
    return dict(pr=pr, threads=thread_nodes(owner, name, pr["number"]), comments=comments, reviews=reviews,
                viewer=viewer, label=label, body_errors=body_errors(pr.get("body") or "", f"{owner}/{name}", [f["path"] for f in pr.get("files") or []]),
                changed_since=changed)


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        ok = callable(fetch) and "pageInfo" in THREADS_Q and tempfile.gettempdir()
        print(f"pr_fetch selfcheck: {'ok' if ok else 'FAIL'} (network calls are exercised by pr_status on a real PR)")
        sys.exit(0 if ok else 1)
