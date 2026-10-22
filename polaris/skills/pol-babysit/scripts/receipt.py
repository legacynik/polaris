"""receipt — which heads a real-test receipt signs, read from the PR's comments (used by pr_status)."""
from __future__ import annotations

import fnmatch
import re

RECEIPT = re.compile(r"<!-- real-test v1 sha=([0-9a-f]{40}) verdict=(MERGEABLE|MERGEABLE-CON-GAP) -->")


def signs(first: str, env: str) -> bool:
    """The first word of `ambiente:` names the environment: the bare word, or a host one of whose labels
    is it or carries it hyphenated (`api-staging.<host>`). `non-staging` or `local-staging-db` do not.
    ponytail: a host named `non-staging.<host>` signs; a host is trusted to name what it serves."""
    word, env = first.strip(",;:()").lower(), env.strip().lower()
    if not (word and env):  # a blank environment or a blank word signs nothing: `"" == ""` is not a match
        return False
    return word == env or ("." in word and any(env in label.split("-") for label in word.split(".")))


def receipts(comments: list[dict], viewer: str, env: str) -> list[str]:
    """Heads signed by the viewer whose `ambiente:` line names the signing environment."""
    out = []
    for c in comments:
        body = c.get("body") or ""
        m, amb = RECEIPT.search(body), re.search(r"(?im)^ambiente:[ \t]*(.+)$", body)  # never the next line
        first = amb.group(1).split()[0] if amb and amb.group(1).split() else ""
        if (c.get("user") or {}).get("login") == viewer and m and signs(first, env):
            out.append(m.group(1))
    return out


def receipt_ok(head: str, signed: list[str], changed_since: dict[str, list[str]], inert: list[str]) -> bool:
    """The head is signed, or an older signed head differs from it only in inert files."""
    return any(sha == head or (sha in changed_since and all(
        any(fnmatch.fnmatch(f, g) for g in inert) for f in changed_since[sha])) for sha in signed)


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        ok = signs("api-staging.example.com", "staging") and signs("staging,", "staging") and not any(
            signs(w, "staging") for w in ("non-staging", "local-staging-db", "locale")) and not signs("", "")
        print(f"receipt selfcheck: {'ok' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)
