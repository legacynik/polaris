#!/usr/bin/env python3
"""red_break_copy.py — the throwaway copy `red_check.py break` runs in, and nothing else.

The working tree as it is (tracked and untracked, never ignored), with the ignored tool folders
(`venv`, `.venv`, `node_modules`) linked so the repository's own commands start. Writing the
break into the copy also throws away the bytecode the unbroken run left there: CPython trusts a
`.pyc` whose source has the same size and mtime second, so `RATE = 10` → `RATE = 11` written in
the same second ran the unbroken code (found 2026-10-14). The walk never follows a link, so the
real tool folders are never written. An editable install (a `.pth` line in a linked tool folder
that names a folder of the real tree) is pointed at the same folder in the copy, through
PYTHONPATH, which comes before site-packages; what still imports from the real tree the probe
reports, and the break is inconclusive. The command is the user's, and it can still write outside
the copy (`uv run` synced the linked `.venv` to the copy, round 5): `snapshot` and `changed` read
the real tree's files and its tool folders' top entries before and after, so a write is seen.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = {"venv", ".venv", "node_modules"}


def git(root: Path, *args: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return [p for p in out.stdout.split("\0") if p] if out.returncode == 0 else []


def tools(root: Path) -> list[str]:
    """The ignored tool folders (`venv`, `.venv`, `node_modules`), repository-relative."""
    rels = (r.rstrip("/") for r in git(root, "ls-files", "-z", "-oi", "--exclude-standard", "--directory"))
    return [r for r in rels if Path(r).name in TOOLS]


def copy(root: Path, dest: Path) -> list[str]:
    """The working tree as it is, then a link to every ignored tool folder (returned)."""
    for rel in git(root, "ls-files", "-z", "-co", "--exclude-standard"):
        src, dst = root / rel, dest / rel
        if not (src.is_file() or src.is_symlink()):
            continue  # deleted in the working tree
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(os.readlink(src), dst) if src.is_symlink() else shutil.copy2(src, dst)
    linked = []
    for rel in tools(root):
        if not (dest / rel).exists():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(root / rel, dest / rel)
            linked.append(rel)
    return linked


def pythonpath(root: Path, dest: Path, linked: list[str]) -> list[str]:
    """The copy's twin of every real-tree folder a linked tool folder's `.pth` file names."""
    lines = (x.strip() for rel in linked for pth in (root / rel).glob("lib/python*/site-packages/*.pth")
             for x in pth.read_text(encoding="utf-8", errors="replace").splitlines())
    real = [Path(x).resolve() for x in lines if x.startswith("/")]
    return [str(dest / p.relative_to(root)) for p in real if p.is_relative_to(root)]


def snapshot(root: Path) -> dict[str, int]:
    """Every file of the working tree, and the top entries of each tool folder (its `bin`, its
    site-packages), with their modification time: what a run must leave as it found it."""
    files = [root / r for r in git(root, "ls-files", "-z", "-co", "--exclude-standard")]
    for rel in tools(root):
        files += [p for pat in ("*", "bin/*", "lib/python*/site-packages/*") for p in (root / rel).glob(pat)]
    return {str(p.relative_to(root)): p.lstat().st_mtime_ns for p in files if p.is_symlink() or p.exists()}


def changed(root: Path, before: dict[str, int]) -> list[str]:
    after = snapshot(root)
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def write(base: Path, dest: Path, text: str) -> None:
    """The broken text into the copy, after dropping every bytecode cache the copy holds."""
    for folder, dirs, _files in os.walk(base):  # followlinks=False: linked tool folders untouched
        if "__pycache__" in dirs:
            shutil.rmtree(Path(folder) / "__pycache__")
            dirs.remove("__pycache__")
    dest.write_bytes(text.encode("utf-8"))
    later = dest.stat().st_mtime + 2  # past the unbroken run's second, without reading the clock
    os.utime(dest, (later, later))


def _selfcheck() -> int:
    """A tracked file, an untracked one, an ignored venv linked, the real venv left alone."""
    with tempfile.TemporaryDirectory() as d:
        root, dest = Path(d) / "r", Path(d) / "c"
        (root / "venv" / "__pycache__").mkdir(parents=True)
        (root / ".gitignore").write_text("venv/\n")
        (root / "a.py").write_text("A = 1\n")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "a.py", ".gitignore"], check=True)
        (root / "b.py").write_text("B = 1\n")
        dest.mkdir()
        copy(root, dest)
        write(dest, dest / "a.py", "A = 2\n")
        ok = ((dest / "b.py").is_file() and (dest / "venv").is_symlink()
              and (root / "venv" / "__pycache__").is_dir() and (root / "a.py").read_text() == "A = 1\n")
    print("SELFCHECK OK" if ok else "SELFCHECK ROSSO")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck() if sys.argv[1:] == ["--selfcheck"] else 2)
