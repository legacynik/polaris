#!/usr/bin/env python3
"""perimeter.py — deriva il perimetro reale del cambiamento da git, meccanicamente.

Risponde a F6/F7/G2.6 (il real-test prova lo SHA, non il flusso): il perimetro
non e' quello che l'agente DICE di aver guardato, e' quello che `git diff`
mostra, ricalcolato ad ogni chiamata. Rilevamento rami nuovi (G1.6) delegato a
`branches.py`.

Uso:
    perimeter.py --repo R [--base REF] [--head REF|STAGED] --hash-only
    perimeter.py --repo R [--base REF] [--head REF|STAGED]      # JSON completo
    perimeter.py --selfcheck

`--head STAGED` (default) usa l'albero che verrebbe creato da `git commit` ora
(`git write-tree`) — cosi' l'hash cattura anche le modifiche non ancora
committate, non solo l'ultimo commit. Per un branch/PR gia' committato passa
`--head <sha-o-ref>`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from branches import detect_new_branches  # noqa: E402


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _default_branch(repo: Path) -> str | None:
    """Il ref REMOTO per intero, non il suo ultimo segmento.

    `rsplit("/", 1)[-1]` su `refs/remotes/origin/HEAD` restituiva `"main"`, cioe'
    esattamente il nome locale che la docstring di resolve_base vieta: la base
    finiva sul branch `main` del checkout, che in un repo multi-worktree e'
    regolarmente decine di commit indietro rispetto a origin/main. Misurato su
    Acme-quotes il 2026-08-30: merge-base con `main` = 6d8cf38f e 237 file di
    perimetro, merge-base con `origin/main` = b45e443b e 59 — 178 file di lavoro
    altrui pretesi come propri, in silenzio. Il selfcheck non lo vedeva perche'
    la sua fixture non ha nessun origin/HEAD e cadeva sul ripiego HEAD~1.
    """
    try:
        ref = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        return None  # nessun origin/HEAD: NON indovinare un nome (dottrina: mai assumere main)
    prefix = "refs/remotes/"
    return ref[len(prefix):] if ref.startswith(prefix) else ref


def resolve_base(repo: Path, explicit: str | None) -> str:
    """Base reale: esplicita > merge-base col VERO default branch > HEAD~1 dichiarato.
    Mai il nome letterale 'main'/'master': un branch stale con quel nome produce un
    perimetro sbagliato in silenzio — falso verde (rosso R1, fusione 2026-08-16)."""
    if explicit:
        return git(repo, "rev-parse", explicit)
    default = _default_branch(repo)
    if default:
        try:
            return git(repo, "merge-base", "HEAD", default)
        except subprocess.CalledProcessError:
            pass
    print("perimeter: base non determinabile (nessuna --base, nessun origin/HEAD) — "
          "uso HEAD~1 come RIPIEGO DICHIARATO; per una PR passa --base", file=sys.stderr)
    try:
        return git(repo, "rev-parse", "HEAD~1")
    except subprocess.CalledProcessError:
        return git(repo, "rev-parse", "HEAD")  # repo a UN commit: la base e' HEAD stesso


def head_tree_hash(repo: Path, head: str) -> str:
    """L'hash-albero e' la chiave di contenuto: cambia se cambia UNA riga."""
    if head == "STAGED":
        return git(repo, "write-tree")
    return git(repo, "rev-parse", f"{head}^{{tree}}")


def build_perimeter(repo: Path, base_ref: str | None, head_ref: str) -> dict:
    base = resolve_base(repo, base_ref)
    head_tree = head_tree_hash(repo, head_ref)
    diff_text = git(repo, "diff", base, head_tree)
    files = [l for l in git(repo, "diff", "--name-only", base, head_tree).splitlines() if l]
    return {
        "base": base,
        "head_tree": head_tree,
        "content_hash": head_tree,
        "files": files,
        "new_branches": detect_new_branches(diff_text),
    }


def _fixture_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")


def _commit_all(repo: Path, msg: str) -> None:
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", msg)


def _selfcheck() -> int:
    """Materializza un repo git usa-e-getta e prova ogni ramo di questo script."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _fixture_repo(repo)
        f = repo / "a.py"
        f.write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
        _commit_all(repo, "base")
        base_sha = git(repo, "rev-parse", "HEAD")

        f.write_text(
            "def f(x):\n    if x:\n        return 1\n    else:\n        return -1\n    return 0\n"
        )
        git(repo, "add", ".")
        p = build_perimeter(repo, base_sha, "STAGED")
        assert p["files"] == ["a.py"], f"file non rilevato: {p['files']}"
        branches = [b["snippet"] for b in p["new_branches"]]
        assert any("else" in b for b in branches), f"else nuovo non rilevato: {branches}"
        h_staged = p["content_hash"]

        _commit_all(repo, "fix")
        h_commit = git(repo, "rev-parse", "HEAD^{tree}")
        assert h_staged == h_commit, "hash STAGED e hash del commit risultante devono coincidere"

        f.write_text(f.read_text() + "# rumore\n")
        git(repo, "add", ".")
        h_noise = build_perimeter(repo, base_sha, "STAGED")["content_hash"]
        assert h_noise != h_commit, "una riga in piu' deve cambiare l'hash (chiave = contenuto)"

    # R1 (fusione 2026-08-16): un branch 'main' STALE non deve mai diventare la base in
    # silenzio. Tre commit: 'main' resta al primo, HEAD~1 e' il secondo — se la base
    # fosse 'main' (comportamento vecchio) i due sha differirebbero.
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        subprocess.run(["git", "init", "-q", "-b", "develop", str(repo)], check=True)
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (repo / "f.txt").write_text("a\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "one")
        git(repo, "branch", "main")
        (repo / "f.txt").write_text("a\nb\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "two")
        (repo / "f.txt").write_text("a\nb\nc\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "three")
        base = resolve_base(repo, None)
        assert base == git(repo, "rev-parse", "HEAD~1") != git(repo, "rev-parse", "main"), \
            "R1: senza origin/HEAD la base e' il ripiego dichiarato HEAD~1, mai il nome 'main'"
    # R1b (2026-08-30): il caso che R1 non tocca. R1 prova un repo SENZA origin/HEAD,
    # quindi cade sul ripiego e non esercita mai _default_branch. Con origin/HEAD
    # presente, il vecchio rsplit("/",1)[-1] restituiva "main" e la merge-base finiva
    # sul branch LOCALE con quel nome — che in un checkout multi-worktree e' stale.
    with tempfile.TemporaryDirectory() as td:
        up, repo = Path(td) / "up", Path(td) / "clone"
        subprocess.run(["git", "init", "-q", "-b", "main", str(up)], check=True)
        git(up, "config", "user.email", "t@t"); git(up, "config", "user.name", "t")
        (up / "f.txt").write_text("a\n"); git(up, "add", "."); git(up, "commit", "-qm", "one")
        subprocess.run(["git", "clone", "-q", str(up), str(repo)], check=True)
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (up / "f.txt").write_text("a\nb\n"); git(up, "add", "."); git(up, "commit", "-qm", "two")
        git(repo, "fetch", "-q", "origin")
        git(repo, "checkout", "-q", "-b", "feature", "origin/main")
        (repo / "g.txt").write_text("x\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "feature work")
        stale_local = git(repo, "rev-parse", "main")
        assert stale_local != git(repo, "rev-parse", "origin/main"), "fixture: il main locale deve essere stale"
        base = resolve_base(repo, None)
        assert base == git(repo, "rev-parse", "origin/main"), \
            f"R1b: la base deve venire da origin/main, non dal main locale stale (base={base})"
        assert base != stale_local, "R1b: la base non deve MAI essere il main locale"

    print("SELFCHECK OK — file/rami/hash su repo usa-e-getta + R1 base-mai-indovinata "
          "+ R1b origin/HEAD-non-e-il-main-locale, 8 asserzioni")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path)
    ap.add_argument("--base")
    ap.add_argument("--head", default="STAGED")
    ap.add_argument("--hash-only", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return _selfcheck()
    if not a.repo:
        ap.error("--repo richiesto")
    perim = build_perimeter(a.repo, a.base, a.head)
    if a.hash_only:
        print(perim["content_hash"])
    else:
        print(json.dumps(perim, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
