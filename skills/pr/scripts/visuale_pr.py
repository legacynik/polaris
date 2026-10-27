"""visuale_pr — does a PR touch the interface? (used by controlla_pr, which re-exports it)."""
from __future__ import annotations

import re
import subprocess

UI = re.compile(r"\.(tsx|jsx|vue|svelte|css|scss|html)$")


class NonSo(Exception):
    """The script cannot decide."""


def ui_da_file(files: list[str]) -> bool:  # noqa: D103
    return any(UI.search(f) for f in files)


def tocca_ui(root: str = ".") -> bool:
    """Does the branch of the repo at `root` change a visible file? NonSo when base or diff is unreadable."""
    git = ["git", "-C", str(root)]
    ref = subprocess.run([*git, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"], capture_output=True, text=True)
    base = ref.stdout.strip() or next((b for b in ("origin/main", "origin/master") if subprocess.run(
        [*git, "rev-parse", "-q", "--verify", b], capture_output=True).returncode == 0), "")
    out = subprocess.run([*git, "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True)
    if not base or out.returncode:
        raise NonSo("base del ramo illeggibile: passa --visuale o --no-visuale")
    return any(UI.search(f) for f in out.stdout.split())


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        ok = ui_da_file(["web/Panel.tsx"]) and not ui_da_file(["api/app.py"])
        print(f"visuale_pr selfcheck: {'ok' if ok else 'FAIL'} (tocca_ui is exercised by test_controlla_pr)")
        sys.exit(0 if ok else 1)
