#!/usr/bin/env python3
"""PreToolUse hook in front of `gh`: a tripwire on the default spelling, not a security boundary.

A raw merge (`gh pr merge` in any spelling, or the merge API) is always blocked: `merge_gate.py execute`
requeries first and never retries blind. `gh pr create` passes the redaction scan, the version and
changelog checks the repo's ship: contract declares, and a fresh real-test verdict (drafts skip the
verdict and need no body); `create`, `ready` and `edit` with a body pass the pr skill's checker. Any
internal failure blocks: in Claude Code only exit 2 blocks, an error exit lets the command run.

    pre_tool_hook.py            reads Claude Code's PreToolUse JSON from stdin
    pre_tool_hook.py --selfcheck
"""
from __future__ import annotations
import sys, os, json, re, shlex, subprocess, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import redact_scan, version_bump, realtest_gate  # sibling scripts, same dir
from gh_parse import JUDGED, JUDGED_VERB, MERGE_API, RAW_MERGE, cd_target, flag_value, gh_calls, pr_ref

BYPASS_ENV = "SHIP_BYPASS_GATE"


def checker():
    """The pr skill's checker, a sibling folder; absent means nobody can judge a body: block."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pol-pr" / "scripts"))
    import controlla_pr
    return controlla_pr


def default_branch(root: Path) -> str:
    r = subprocess.run(["git", "-C", str(root), "symbolic-ref", "refs/remotes/origin/HEAD"], capture_output=True, text=True)
    return r.stdout.strip().rsplit("/", 1)[-1] if r.returncode == 0 and r.stdout.strip() else "main"


def declared(root: Path, key: str) -> bool:
    """Version and changelog are asked only of a repo whose ship: contract names them."""
    for cfg in (root / "_polaris" / "config.yml", root / "config.yml"):
        if cfg.is_file():
            text = "\n" + cfg.read_text(encoding="utf-8")
            if "\nship:" not in text:
                return False
            block = re.split(r"(?m)^\S", text.split("\nship:", 1)[1])[0]
            return bool(re.search(rf"(?m)^\s+{key}:\s*\S", block))
    return False


def phase_a_check(root: Path, draft: bool) -> tuple[bool, str]:
    r = subprocess.run(["git", "-C", str(root), "diff", f"{default_branch(root)}...HEAD"], capture_output=True, text=True)
    diff = r.stdout if r.returncode == 0 else ""
    if any(f.severity == "HIGH" for f in redact_scan.scan_text(diff)):
        return False, "redaction: a HIGH-severity secret is in this diff, run redact_scan.py"
    vb = version_bump.decide(root)
    if declared(root, "version_file") and vb["exit"] != 0:
        return False, f"version-bump: {vb['state']} unresolved, run version_bump.py"
    if declared(root, "changelog") and "CHANGELOG.md" not in diff:
        return False, "changelog: the contract declares one and this diff does not touch it"
    rt = realtest_gate.decide(root)
    if not draft and rt["action"] == "BLOCKED":
        return False, f"real-test: {rt['why']}"
    return True, ""


def body_check(call: tuple[str, list[str]], root: Path) -> tuple[bool, str]:
    verb, args = call
    cp, ref = checker(), pr_ref(args) if verb != "pr create" else []
    path = flag_value(args, "--body-file", "-F")
    if path is None and (flag_value(args, "--body", "-b") is not None or "--fill" in args or verb == "pr create"):
        return False, "write the body with /pr into a file and pass --body-file (a draft needs none)"
    if path is None and verb == "pr ready":
        r = subprocess.run(["gh", "pr", "view", *ref, "--json", "body"], capture_output=True, text=True)
        corpo = json.loads(r.stdout)["body"] if r.returncode == 0 else None
    else:
        corpo = Path(path).read_text(encoding="utf-8") if path and Path(path).is_file() else None
    if corpo is None:
        return path is None and verb == "pr edit", "PR body unreadable"
    try:
        repo = ref[ref.index("-R") + 1] if "-R" in ref else None
        issues = {n: criteri_di(n, cp.repo_di(corpo, n) or repo) for n in cp.riferimenti(corpo)[0]}
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        return False, f"issue unreadable ({e}): a body is not judged without its criteria"
    errors = cp.controlla(corpo, issues, visible(cp, ref, root))
    return (not errors), "PR body (/pr): " + "; ".join(errors)


def visible(cp, ref: list[str], root: Path):
    """From the PR's own files when it names one, else from the branch's diff; None when unknown."""
    if ref:
        r = subprocess.run(["gh", "pr", "view", *ref, "--json", "files"], capture_output=True, text=True)
        if r.returncode == 0:
            return cp.ui_da_file([f["path"] for f in json.loads(r.stdout)["files"]])
    try:
        return cp.tocca_ui(root)
    except cp.NonSo:
        return None


def criteri_di(n: int, repo: str | None) -> list[str]:
    return checker().leggi_issue(n, repo)


def decide(cmd: str, root: Path | None) -> tuple[int, str]:
    if not re.search(r"\bgh\b", cmd):
        return 0, ""
    if RAW_MERGE.search(cmd):
        return 2, "a raw merge skips the requery and the never-retry rule: run merge_gate.py execute --pr <N>"
    try:
        calls = gh_calls(cmd)
    except ValueError:
        return (2, "unreadable gh command: write the body to a file") if JUDGED_VERB.search(cmd) else (0, "")
    for verb, args in calls:
        if verb == "pr merge" or (verb == "api" and any(MERGE_API.search(a) for a in args)):
            return 2, "a raw merge skips the requery and the never-retry rule: run merge_gate.py execute --pr <N>"
    verb, args = next(((v, a) for v, a in calls if v in [f"pr {j}" for j in JUDGED]), ("", []))
    if root is None or not verb or (verb == "pr ready" and "--undo" in args):
        return 0, ""
    root = cd_target(cmd) or root
    draft = "--draft" in args or "-d" in args
    if verb == "pr create":
        ok, why = phase_a_check(root, draft)
        if not ok or draft:
            return (0, "") if ok else (2, why)
    ok, why = body_check((verb, args), root)
    return (0, "") if ok else (2, why)


def log_bypass(cmd: str) -> None:
    log = Path(os.environ.get("SHIP_BYPASS_LOG", Path.home() / ".claude" / "ship-bypass.log"))
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{os.getcwd()}\t{cmd}\n")


def main(argv: list[str]) -> int:
    """Any failure blocks (exit 2): a PreToolUse hook that errors with 1 lets the command run."""
    if "--selfcheck" in argv:
        return selfcheck()
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") != "Bash":
            return 0
        cmd = payload.get("tool_input", {}).get("command", "")
        if os.environ.get(BYPASS_ENV) == "1":
            log_bypass(cmd)
            return 0
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        root = Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
        code, why = decide(cmd, root)
    except Exception as e:  # noqa: BLE001 - the gate never fails open
        code, why = 2, f"the gate could not read this command ({type(e).__name__}: {e})"
    if code:
        print(f"ship: gate BLOCKED, {why}", file=sys.stderr)
        print(f"Emergency bypass, logged: {BYPASS_ENV}=1", file=sys.stderr)
    return code


def _git(root: Path, *args: str) -> None:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    (root / "config.yml").write_text("ship:\n  version_file: VERSION\n  changelog: CHANGELOG.md\n")
    (root / "VERSION").write_text("0.1.0\n")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-01-01\n- initial\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: initial")
    _git(root, "tag", "v0.1.0")
    _git(root, "checkout", "-q", "-b", "feat/x")


def selfcheck() -> int:
    assert decide("ls -la", None) == (0, "")
    assert decide("gh pr " + "merge 42 --squash", None)[0] == 2

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _init_repo(root)
        bf = root / "body.md"
        bf.write_text("## In breve\n**Decisione richiesta:** merge sì\n\nNessuna issue.\n\n## Cosa cambia\nx\n"
                      "## Decisioni\nx\n## Prove\nx\n## Cosa resta aperto\nniente\n## Rischio del merge\nx\n")

        code, why = decide(f"gh pr create --title x --body-file {bf}", root)
        assert code == 2 and "changelog" in why, (code, why)  # no CHANGELOG.md touched yet

        (root / "CHANGELOG.md").write_text(
            (root / "CHANGELOG.md").read_text().replace("## [Unreleased]", "## [Unreleased]\n- did a thing (#1)"))
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "fix: thing")
        code2, why2 = decide(f"gh pr create --title x --body-file {bf}", root)
        assert code2 == 0, (code2, why2)  # clean diff, version FRESH, changelog touched, real-test opted-out

        (root / "leak.py").write_text('AWS_KEY="AKIAABCDEFGHIJKLMNOP"\n')
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "chore: oops")
        code3, why3 = decide(f"gh pr create --title x --body-file {bf}", root)
        assert code3 == 2 and "redaction" in why3, (code3, why3)

    # end-to-end via real stdin/env, proving the JSON extraction itself (not just decide()).
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "gh pr " + "merge 9"}})
    r1 = subprocess.run([sys.executable, __file__], input=payload, capture_output=True, text=True)
    assert r1.returncode == 2, r1
    r2 = subprocess.run([sys.executable, __file__], input=payload, capture_output=True, text=True,
                         env={**os.environ, BYPASS_ENV: "1", "SHIP_BYPASS_LOG": os.devnull})
    assert r2.returncode == 0, r2

    assert decide('gh pr create --title x --body "y"', Path("."))[0] == 2
    print("SELFCHECK OK — 7 branches: pass-through, merge-always-blocked, changelog-missing-blocks, "
          "clean-diff-passes, secret-in-diff-blocks, end-to-end stdin (block + bypass-env), inline-body-refused")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
