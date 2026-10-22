"""gh_parse — which `gh` call a shell command makes, whatever the global flags or spacing."""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

GLOBAL_WITH_VALUE = {"-R", "--repo", "--hostname"}
GLUED = ("-R", "-b", "-F")  # short flags whose value may be glued on: `-Ro/r`, `-bdone`
JUDGED = ("create", "ready", "edit")  # the verbs whose body is judged
ALIAS = {"new": "create"}  # gh's own alias of `pr create`
# `pr`, then any flags with or without a value, then the verb: the regexes for a command shlex cannot split
PR_THEN = r"\bpr\s+(?:-\S+(?:[ \t]+[^\s-]\S*)?\s+)*?"
JUDGED_VERB = re.compile(PR_THEN + "(?:" + "|".join([*JUDGED, *ALIAS]) + r")\b")
RAW_MERGE = re.compile(PR_THEN + r"merge\b|/pulls/[^/\s]+/merge\b|/merges\b|mergePullRequest|enablePullRequestAutoMerge")
MERGE_API = re.compile(r"/pulls/[^/\s]+/merge\b")  # $PR, {number}: any segment
SEP = re.compile(r"&&|\|\||;|\||\r?\n|(?<![<>&])&(?![>&])|(\$\(|`)")  # what ends one shell command


def unglue(words: list[str]) -> list[str]:
    """`-Ro/r` is `-R o/r`, `-bdone` is `-b done`."""
    out = []
    for w in words:
        out += [w[:2], w[2:]] if len(w) > 2 and w[:2] in GLUED else [w]
    return out


def leading_flags(words: list[str]) -> tuple[list[str], list[str]]:
    """The flags before the first word that is not one, and the rest."""
    j = 0
    while j < len(words) and words[j].startswith("-"):
        j += 2 if words[j] in GLOBAL_WITH_VALUE else 1
    return words[:j], words[j:]


def gh_calls(cmd: str) -> list[tuple[str, list[str]]]:
    """Every `gh` call in the command: ('pr <verb>' or 'api', its flags and the words up to the next `;`).
    Flags are read before `pr` and again between `pr` and the verb, so `-R` is never taken for a verb; a
    later command lends no flag: a newline and a lone `&` end a command too (`2>&1`, `&>` do not). `$(` and a
    backtick stay a word: `--body $(cat f)` is still an inline body."""
    # the shell drops an unescaped `\` + newline first: a wrapped call is one call; `\\` at line end is not one
    joined = re.sub(r"(?<!\\)((?:\\\\)*)\\\r?\n", r"\1 ", cmd)
    words = shlex.split(re.sub(SEP, lambda m: " $( " if m.group(1) else " ; ", joined))
    calls = []
    for i, w in enumerate(words):
        if os.path.basename(w) != "gh":
            continue
        own = words[i + 1:] + [";"]
        pre, rest = leading_flags(unglue(own[:own.index(";")]))
        mid, after = leading_flags(rest[1:])
        if rest[:1] == ["api"]:
            calls.append(("api", pre + rest[1:]))
        elif rest[:1] == ["pr"] and after:
            calls.append((f"pr {ALIAS.get(after[0], after[0])}", pre + mid + after[1:]))
    return calls


def gh_call(cmd: str) -> tuple[str, list[str]]:
    """The first `gh` call, kept for callers that need only one."""
    return (gh_calls(cmd) or [("", [])])[0]


def flag_value(args: list[str], *names: str) -> str | None:
    for i, a in enumerate(args):
        for n in names:
            if a == n and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(n + "="):
                return a.split("=", 1)[1]
    return None


def pr_ref(args: list[str]) -> list[str]:
    """`<number|url> [-R owner/repo]` for `gh pr view`, from this call's own flags: [] when it names no PR."""
    sel = [a for a in args if re.fullmatch(r"\d+|https://\S+", a)][:1]
    repo = flag_value(args, "-R", "--repo")
    return sel + (["-R", repo] if repo else []) if sel else []


def cd_target(cmd: str) -> Path | None:
    """A leading `cd <path> &&` moves where the PR's diff is read."""
    m = re.match(r"\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)\s*(&&|;)", cmd)
    path = Path(m.group(1).strip("\"'")).expanduser() if m else None
    return path if path and path.is_dir() else None


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        cases = [gh_call("gh -R o/r pr " + "merge 5")[0] == "pr merge", gh_call("gh pr -Ro/r " + "merge 5")[0] == "pr merge", gh_call("ls && gh  pr create -t x")[0] == "pr create",
                 gh_call("gh api -X PUT repos/o/r/pulls/5/" + "merge")[0] == "api", gh_call("echo gh")[0] == "",
                 flag_value(["--body=x"], "--body", "-b") == "x"]
        print(f"gh_parse selfcheck: {sum(cases)}/{len(cases)}")
        sys.exit(0 if all(cases) else 1)
