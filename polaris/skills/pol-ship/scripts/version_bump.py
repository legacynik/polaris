#!/usr/bin/env python3
"""Version-bump state machine — auto-detect manifest, classify commits, decide.

States: FRESH (baseline untouched, bump proposed) · ALREADY_BUMPED (file
already matches the expected bump — nothing to do) · DRIFT_STALE_PKG (two+
version files disagree with each other) · DRIFT_UNEXPECTED (file changed but
matches neither the old baseline nor the expected bump) · NO_VERSION_FILE.
DRIFT_* and NO_VERSION_FILE exit non-zero — ship's Phase A stops and asks a
human instead of guessing which version is right.

    version_bump.py [--root PATH]   decide, print JSON, exit per state
    version_bump.py --selfcheck     prove each state fires on a real temp repo
"""
from __future__ import annotations
import re, sys, json, argparse, subprocess, tempfile
from pathlib import Path

# path glob (relative to root) -> regex with one capture group = the version string
VERSION_FILES: dict[str, re.Pattern] = {
    "VERSION": re.compile(r"^\s*(\d+\.\d+\.\d+)\s*$"),
    "package.json": re.compile(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"'),
    "pyproject.toml": re.compile(r'(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"'),
    "Cargo.toml": re.compile(r'(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"'),
}

CONVENTIONAL = re.compile(r"^(feat|fix|perf|refactor|docs|chore|test|build|ci|style)(\([^)]*\))?(!)?:")


def find_version_files(root: Path) -> list[tuple[Path, str]]:
    found = []
    for name, pattern in VERSION_FILES.items():
        p = root / name
        if p.exists():
            m = pattern.search(p.read_text(errors="replace"))
            if m:
                found.append((p, m.group(1)))
    return found


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def last_tag(root: Path) -> str | None:
    out = _git(root, "describe", "--tags", "--abbrev=0")
    return out or None


def version_at_tag(root: Path, tag: str, relpath: str, pattern: re.Pattern) -> str | None:
    text = _git(root, "show", f"{tag}:{relpath}")
    if not text:
        return None
    m = pattern.search(text)
    return m.group(1) if m else None


def commits_since(root: Path, tag: str | None) -> list[str]:
    rng = f"{tag}..HEAD" if tag else "HEAD"
    out = _git(root, "log", rng, "--format=%s%n%b%x1e")
    return [c for c in out.split("\x1e") if c.strip()]


def classify_commits(commit_blocks: list[str]) -> str:
    """conventional-commit subjects -> bump level. breaking > feat > fix/perf > none."""
    level = "none"
    for block in commit_blocks:
        stripped = block.strip()
        subject = stripped.splitlines()[0] if stripped else ""
        m = CONVENTIONAL.match(subject)
        if "BREAKING CHANGE" in block or "BREAKING-CHANGE" in block or (m and m.group(3)):
            return "major"
        if m and m.group(1) == "feat" and level != "major":
            level = "minor"
        elif m and m.group(1) in ("fix", "perf") and level not in ("major", "minor"):
            level = "patch"
    return level


def bump(version: str, level: str) -> str:
    if level == "none":
        return version
    major, minor, patch = (int(x) for x in version.split("."))
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def decide(root: Path) -> dict:
    files = find_version_files(root)
    if not files:
        return {"state": "NO_VERSION_FILE", "files": [], "exit": 2}

    values = {str(p): v for p, v in files}
    if len(set(values.values())) > 1:
        return {"state": "DRIFT_STALE_PKG", "files": values, "exit": 1,
                "why": "version files disagree with each other — pick one source of truth"}

    canonical_path, current = files[0]
    relpath = canonical_path.name
    pattern = VERSION_FILES[relpath]
    tag = last_tag(root)
    commits = commits_since(root, tag)
    level = classify_commits(commits)

    baseline = version_at_tag(root, tag, relpath, pattern) if tag else None
    if baseline is None:
        return {"state": "FRESH", "files": values, "level": level, "baseline": None,
                "proposed": current, "exit": 0, "why": "no prior tag — first release"}

    proposed = bump(baseline, level)
    if current == baseline:
        return {"state": "FRESH", "files": values, "level": level, "baseline": baseline,
                "proposed": proposed, "exit": 0}
    if current == proposed:
        return {"state": "ALREADY_BUMPED", "files": values, "level": level, "baseline": baseline,
                "proposed": proposed, "exit": 0}
    return {"state": "DRIFT_UNEXPECTED", "files": values, "level": level, "baseline": baseline,
            "proposed": proposed, "exit": 1,
            "why": f"current {current} matches neither baseline {baseline} nor expected {proposed}"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    result = decide(Path(args.root))
    print(json.dumps(result, indent=2))
    return result["exit"]


def _commit(root: Path, msg: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", msg], check=True, capture_output=True,
                    env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.t",
                         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.t", "PATH": "/usr/bin:/bin"})


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        (root / "VERSION").write_text("0.1.0\n")
        _commit(root, "chore: initial")
        subprocess.run(["git", "-C", str(root), "tag", "v0.1.0"], check=True, capture_output=True)

        (root / "src.py").write_text("# fix\n")
        _commit(root, "fix: off-by-one")
        r = decide(root)
        assert r["state"] == "FRESH" and r["proposed"] == "0.1.1", r

        (root / "VERSION").write_text("0.1.1\n")
        _commit(root, "chore: bump version")
        r = decide(root)
        assert r["state"] == "ALREADY_BUMPED", r

        (root / "VERSION").write_text("5.0.0\n")
        _commit(root, "feat: add widget")
        r = decide(root)
        assert r["state"] == "DRIFT_UNEXPECTED" and r["exit"] == 1, r

        (root / "package.json").write_text('{"version": "9.9.9"}')
        r = decide(root)
        assert r["state"] == "DRIFT_STALE_PKG" and r["exit"] == 1, r
        (root / "package.json").unlink()

    with tempfile.TemporaryDirectory() as td2:
        root2 = Path(td2)
        r = decide(root2)
        assert r["state"] == "NO_VERSION_FILE" and r["exit"] == 2, r

    assert bump("1.2.3", "major") == "2.0.0"
    assert bump("1.2.3", "minor") == "1.3.0"
    assert bump("1.2.3", "patch") == "1.2.4"
    assert classify_commits(["feat!: breaking\n"]) == "major"
    assert classify_commits(["fix: x\n", "docs: y\n"]) == "patch"

    print("SELFCHECK OK — 5 states (FRESH/ALREADY_BUMPED/DRIFT_STALE_PKG/DRIFT_UNEXPECTED/NO_VERSION_FILE) + bump math, all as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
