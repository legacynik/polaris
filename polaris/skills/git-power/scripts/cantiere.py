#!/usr/bin/env python3
"""git-power — commit boundary, census, and guarded Git cleanup.

    cantiere.py census [--repo PATH ...] [--vault DIR] [--out FILE.json]
    cantiere.py close --target <path-o-branch-o-stash@{N}> --confirm <stesso-target>
                       [--repo PATH] [--prepare-rebase]
    cantiere.py commit-check [--repo PATH] [--base REF]
    cantiere.py --selfcheck

Zero dipendenze esterne (stdlib solo: subprocess/json/argparse/pathlib/dataclasses) —
gira senza installare nulla sui 4 harness. Chiama solo `git`/`gh`, mai un git binding.

Regola strutturale (bypass-eval L1, 2026-08-09): la guardia NON vive solo nei wrapper
(`close_worktree`/`close_branch`/`close_stash`) — vive dentro `git()` stessa, la
primitiva. `--force`/`-D`/`stash clear` sono rifiutati da `git()` per QUALSIASI
chiamante, CLI o `import cantiere; cantiere.git(...)` diretto: non è più vero (e non
lo era mai) che "lo script non sa pronunciare il comando" — sa benissimo pronunciarlo,
ora rifiuta di eseguirlo comunque, ovunque sia chiamato da dentro questo modulo.
`reset --hard` è l'unica eccezione condizionata: permesso solo se `git()` verifica lei
stessa, al momento della chiamata, che il target non è sporco/mid-operazione/con
attività recente — vedi `_guard()` e references/bypass-test.md §4-6 per la prova.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from worktree_verdict import PRInfo, WorktreeInfo, gate_decision, removable, verdict

AGE_LIVE_DAYS = 14      # sotto: "vivo". ponytail: soglia calibrabile, non misurata sul founder
AGE_ORPHAN_DAYS = 30    # sopra, non mergiato, pulito: "orfano"
LOCK_WINDOW_SECONDS = 180  # HEAD toccato più di recente = un altro pannello ci sta scrivendo ORA
GH_TIMEOUT_SECONDS = 20  # breaker FAIL 4 on PR #254: an unbounded gh call could hang forever
# team-lead 2026-09-03: regenerates trivially, never worth blocking a removal over.
# Declared list, not a heuristic — anything else ignored (.env, state/current.md, ...) still blocks.
REGENERABLE_IGNORED = ("__pycache__/", "*.pyc", ".pytest_cache/", ".ruff_cache/",
                       ".mypy_cache/", ".coverage", ".coverage.*", ".DS_Store",
                       ".serena/", ".real-test/verdicts/", ".real-test/evidence/",
                       ".wiki-build-log.md", "wiki-lm-index.jsonl")


class Refused(RuntimeError):
    """git() rifiuta da sé una chiamata distruttiva non sicura — non un wrapper
    sopra di lei. Bypass-eval L1 (2026-08-09) ha dimostrato che chiamare la
    primitiva a mano saltava ogni controllo dei wrapper; ora la guardia è nella
    primitiva stessa, quindi non c'è un percorso — CLI o import diretto — che
    la eviti."""


# ---------------------------------------------------------------- git plumbing

def git(repo: Path, *args: str, check: bool = True) -> str:
    _guard(repo, args)
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} @ {repo}: {r.stderr.strip()}")
    return r.stdout.strip()


def git_dir(repo: Path) -> Path:
    """`git -C <repo> rev-parse --git-dir` torna relativo (es. '.git') quando repo è la
    working tree principale — relativo al cwd del PROCESSO chiamante, non a `repo`. Bug
    reale trovato dal selfcheck (non dedotto): senza il join, mid_operation()/
    recent_activity_lock() guardavano nella cartella sbagliata su ogni chiamata."""
    out = Path(git(repo, "rev-parse", "--git-dir"))
    return out if out.is_absolute() else (repo / out).resolve()


def git_common_dir(repo: Path) -> Path:
    out = Path(git(repo, "rev-parse", "--git-common-dir"))
    return out if out.is_absolute() else (repo / out).resolve()


def default_branch(repo: Path) -> str:
    out = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", check=False)
    if out:
        return out.rsplit("/", 1)[-1]
    for cand in ("main", "master"):
        if git(repo, "show-ref", "--verify", f"refs/heads/{cand}", check=False):
            return cand
    return git(repo, "branch", "--show-current", check=False) or "HEAD"


def age_days(iso: str) -> float:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


# ------------------------------------------------------------- danger detectors

def is_dirty(repo: Path) -> bool:
    return bool(git(repo, "status", "--porcelain", check=False))


def mid_operation(repo: Path) -> str | None:
    """MERGE_HEAD/rebase in corso — mai toccare (bypass-test G8#2)."""
    gd = git_dir(repo)
    for name, marker in (("merge", "MERGE_HEAD"), ("rebase", "rebase-merge"),
                          ("rebase", "rebase-apply"), ("cherry-pick", "CHERRY_PICK_HEAD")):
        if (gd / marker).exists():
            return name
    return None


def recent_activity_lock(repo: Path) -> bool:
    """HEAD scritto <LOCK_WINDOW_SECONDS fa = un altro pannello sta operando ORA.
    Traduzione meccanica di 'ownership per provenienza' (superpowers): qui non
    esiste un registro di chi ha creato cosa, quindi il proxy è l'attività recente —
    limite dichiarato, non provenance vera. Vedi SKILL.md 'Onestà sul meccanismo'."""
    gd = git_dir(repo)
    head = gd / "HEAD"
    if (gd / "index.lock").exists():
        return True
    if head.exists() and (time.time() - head.stat().st_mtime) < LOCK_WINDOW_SECONDS:
        return True
    return False


def lsof_cwds() -> tuple[set[str], bool]:
    """(cwds, available). Missing lsof used to degrade to an empty set with
    NO signal (breaker FAIL 2 on PR #254: every IN_USE row silently became
    CLOSABLE, exit still 0) — now the caller gets told and --apply refuses
    (recent_activity_lock, a different signal, still applies either way)."""
    if not shutil.which("lsof"):
        return set(), False
    r = subprocess.run(["lsof", "-d", "cwd", "-Fn"], capture_output=True, text=True)
    return {ln[1:] for ln in r.stdout.splitlines() if ln.startswith("n")}, True


def is_in_use(path: Path, cwds: set[str]) -> bool:
    """Purely process-cwd based (lsof) — the genuinely NEW guard added for
    #252. recent_activity_lock (HEAD-mtime proxy) stays where it always was,
    inside DIRTY's danger checks: OR-ing it in here made every freshly-built
    test fixture register IN_USE (HEAD just written, <180s old), masking
    every other verdict — found by the fixture itself misreporting CLOSABLE/
    COMMITS_AFTER_MERGE rows as IN_USE."""
    resolved = str(path.resolve()) if path.exists() else str(path)
    prefix = resolved + os.sep
    # breaker FAIL 1 on PR #254: a process in <wt>/sub/deep was invisible to
    # exact-match — a process anywhere UNDER the worktree still counts.
    return any(c == resolved or c.startswith(prefix) for c in cwds)


def _guard(repo: Path, args: tuple[str, ...]) -> None:
    """La guardia reale (bypass-eval L1): vive qui, non nei wrapper, quindi
    scatta anche per una chiamata diretta a git(). `--force`/`-D`/`stash clear`
    non hanno un solo caso d'uso legittimo in questo tool (mai dichiarati,
    docstring del modulo) — rifiutati sempre, senza eccezione. `reset --hard`
    è l'unico condizionato: eseguibile solo se il repo è pulito, non in
    un'operazione a metà, e senza attività concorrente rilevata — controllato
    QUI, al momento della chiamata, non nel chiamante."""
    if "--force" in args or "-D" in args:
        raise Refused(f"'--force'/'-D' non è mai permesso da questo tool, per nessun "
                       f"chiamante (CLI o funzione diretta): git {' '.join(args)} @ {repo}")
    if "stash" in args and "clear" in args:
        raise Refused(f"'stash clear' non è mai permesso: cancella OGNI stash, non solo "
                       f"il target — git {' '.join(args)} @ {repo}")
    if args and args[0] == "clean" and any(a.startswith("-") and "f" in a for a in args[1:]):
        raise Refused(f"git clean con -f non è mai permesso: cancellerebbe file non tracciati "
                       f"— git {' '.join(args)} @ {repo}")
    discards_worktree = (
        (args and args[0] == "checkout" and "--" in args)
        or (args and args[0] == "restore"
            and ("--worktree" in args or "--staged" not in args))
    )
    if discards_worktree and is_dirty(repo):
        raise Refused(f"git {' '.join(args)} su {repo} rifiutato: scarterebbe modifiche "
                       "non committate. Salva prima.")
    if (args and args[0] == "stash" and len(args) > 1
            and args[1] in {"push", "pop", "apply", "drop", "branch"}
            and (is_dirty(repo) or mid_operation(repo))):
        raise Refused(f"git {' '.join(args)} su {repo} rifiutato: tree sporco o operazione "
                       "in corso. Non nascondere o spostare lavoro non attribuito.")
    if "reset" in args and "--hard" in args:
        # niente recent_activity_lock qui apposta: quel proxy esiste per i worktree di UN
        # ALTRO pannello: su reset --hard chi chiama sta quasi sempre agendo sul proprio
        # repo appena usato (es. commit → reset --hard per disfarlo) — includerlo qui
        # produce falsi positivi contro l'uso legittimo immediato (misurato scrivendo il
        # selfcheck: un commit di setup faceva rifiutare il reset 0.1s dopo). is_dirty +
        # mid_operation bastano: sono esattamente lo scenario dell'incidente 2026-08-03
        # (modifiche non committate perse), non un proxy più largo e più fragile.
        op = mid_operation(repo)
        reason = f"{op} in corso" if op else "modifiche non committate" if is_dirty(repo) else None
        if reason:
            raise Refused(f"reset --hard su {repo} rifiutato: {reason}. Salva prima "
                           "(commit o stash fuori da un merge in corso), poi ripeti.")


def _method_ledger_open(wt: Path) -> str | None:
    """Contratto dichiarato da metodologia/SKILL.md ('cantiere drains/removes
    them when the worktree closes') mai implementato (EVAL-cantiere-copertura
    §4). `.method/ledger.md` è git-ignored per design: `git status --porcelain`
    non lo vede (verificato, non assunto — vedi bypass-test.md §6), quindi
    `git worktree remove` senza --force lo cancella comunque senza controllo.
    Ritorna il motivo se un piano risulta ancora aperto (stesso formato letto
    da metodologia/scripts/ledger.py: 'TASK n: stato', l'ultimo per numero
    conta), None se non c'è ledger o è tutto 'complete'."""
    ledger = wt / ".method" / "ledger.md"
    if not ledger.exists():
        return None
    lines = ledger.read_text(errors="replace").splitlines()
    if not lines or not lines[0].startswith("PLAN:"):
        return None
    states: dict[str, str] = {}
    for line in lines[1:]:
        if line.startswith("TASK "):
            num, _, state = line[len("TASK "):].partition(":")
            states[num.strip()] = state.strip()
    open_tasks = [f"TASK {n}: {s}" for n, s in states.items() if s != "complete"]
    if not open_tasks:
        return None
    return f"{lines[0]} — {len(open_tasks)} task non completati ({', '.join(open_tasks[:3])})"


# --------------------------------------------------------------------- records

@dataclass
class Row:
    kind: str            # worktree | branch | stash
    id: str              # path | nome branch | stash@{N}
    classification: str  # mergiato-da-chiudere | vivo | orfano | pericoloso
    age_days: float | None
    note: str
    extra: dict = field(default_factory=dict)


# ------------------------------------------------------------------ census: branches

def merged_branches(repo: Path, default: str) -> set[str]:
    out = git(repo, "for-each-ref", "--merged", default, "--format=%(refname:short)",
              "refs/heads", check=False)
    return set(out.splitlines()) - {default}


def branch_rows(repo: Path, default: str, worktree_branches: set[str],
                 open_prs: dict[str, dict]) -> list[Row]:
    merged = merged_branches(repo, default)
    out = git(repo, "for-each-ref", "refs/heads",
              "--format=%(refname:short)%09%(committerdate:iso-strict)")
    rows = []
    for line in out.splitlines():
        name, when = line.split("\t")
        if name == default:
            continue
        a = age_days(when)
        pr = open_prs.get(name)
        cls = classify_branch(name in merged, a, pr)
        note = f"PR #{pr['number']} aperta {age_days(pr['createdAt']):.0f}gg" if pr else ""
        rows.append(Row("branch", name, cls, round(a, 1), note,
                         {"merged": name in merged, "has_worktree": name in worktree_branches,
                          "pr": pr}))
    return rows


def classify_branch(merged: bool, age: float, pr: dict | None) -> str:
    if merged:
        return "mergiato-da-chiudere"
    if pr or age <= AGE_LIVE_DAYS:
        return "vivo"
    if age > AGE_ORPHAN_DAYS:
        return "orfano"
    return "vivo"  # zona grigia: conservativo, mai orfano per difetto


# ------------------------------------------------------------------ census: worktrees

def _flush_entry(entries: list[dict], cur: dict) -> dict:
    if cur:
        entries.append(cur)
    return {}


def worktree_entries(repo: Path) -> list[dict]:
    """-z (NUL-terminated), not line-based: a worktree path containing a
    literal newline truncates and misclassifies under the line parse (r4
    FAIL-B)."""
    out = git(repo, "worktree", "list", "--porcelain", "-z")
    entries, cur = [], {}
    for field in out.split("\x00") + [""]:
        if not field:
            cur = _flush_entry(entries, cur)
            continue
        key, _, val = field.partition(" ")
        cur[key] = val if val else True
    return entries


def _primary_from_entries(entries: list[dict], repo: Path) -> Path:
    """Git always lists the primary worktree first — ground truth for MAIN,
    never the caller-supplied --repo path (breaker FAIL 7 on PR #254: from
    a subdirectory the primary worktree stopped being recognised)."""
    return Path(entries[0]["worktree"]).resolve() if entries else repo.resolve()


def worktree_rows(repo: Path) -> tuple[list[Row], set[str]]:
    """#252's verdict vocabulary (MAIN·PRUNABLE·IN_USE·DIRTY·ACTIVE·CLOSABLE·
    COMMITS_AFTER_MERGE·?) for worktree rows only — branch/stash rows keep
    the old vivo/orfano/mergiato-da-chiudere/pericoloso vocabulary."""
    cwds, lsof_ok = lsof_cwds()
    if not lsof_ok:
        print("lsof not found on PATH — IN_USE's process-cwd check is "
              "skipped (recent_activity_lock still applies)", file=sys.stderr)
    entries = worktree_entries(repo)
    primary = _primary_from_entries(entries, repo)
    rows, branches = [], set()
    for e in entries:
        branch = e.get("branch", "").removeprefix("refs/heads/") or None
        if branch:
            branches.add(branch)
        rows.append(_worktree_row(primary, e, cwds))
    return rows, branches


def _worktree_row(repo: Path, e: dict, cwds: set[str]) -> Row:
    """breaker r2 FAIL 2 on #254: nothing wrapped this — a bad gh reply
    (malformed/empty JSON) or a broken .git pointer took down the WHOLE
    census with a traceback, zero rows, when the vocabulary already has a
    '?' verdict for exactly 'gh/git failed for THIS worktree only'."""
    wt = Path(e["worktree"])
    branch = e.get("branch", "").removeprefix("refs/heads/") or None
    try:
        return _worktree_row_unsafe(repo, e, cwds)
    except Exception as exc:
        info = WorktreeInfo(path=str(wt), branch=branch,
                             error=f"{type(exc).__name__}: {exc}"[:200])
        return Row("worktree", str(wt), verdict(info), None, info.error, {"branch": branch})


def _worktree_row_unsafe(repo: Path, e: dict, cwds: set[str]) -> Row:
    wt = Path(e["worktree"])
    branch = e.get("branch", "").removeprefix("refs/heads/") or None
    if wt.resolve() == repo.resolve():
        info = WorktreeInfo(path=str(wt), branch=branch, is_main=True)
        return Row("worktree", str(wt), verdict(info), None, "", {"branch": branch})
    if e.get("prunable") or not wt.exists():
        info = WorktreeInfo(path=str(wt), branch=branch, prunable=True)
        return Row("worktree", str(wt), verdict(info), None, "directory assente su disco",
                    {"branch": branch})
    info = _worktree_info(repo, e, cwds)
    return Row("worktree", str(wt), verdict(info), None, _verdict_note(wt, e, info),
               {"branch": branch})


def has_ignored_content(wt: Path) -> bool:
    """`git status --porcelain` never lists ignored files at all — breaker
    FAIL 6 on PR #254: a worktree holding only gitignored content (`.env`,
    `state/current.md` — both gitignored by THIS vault's own rules) reported
    clean and `--apply` destroyed both. `--ignored=matching` lists actual
    files only, never an empty ignored directory, so this cannot over-fire
    on a `.gitignore` rule that currently matches nothing. `.method/` is
    excluded: it is ALSO gitignored by design, but its own lifecycle is
    already governed by _method_ledger_open — this check would otherwise
    block a worktree whose plan is marked complete forever."""
    out = subprocess.run(["git", "-C", str(wt), "status", "--porcelain",
                          "--ignored=matching"], capture_output=True, text=True).stdout
    paths = (line[3:] for line in out.splitlines() if line.startswith("!! "))
    return any(not _is_regenerable(p) for p in paths if not p.startswith(".method/"))


def _pattern_matches(parts: list[str], name: str, pat: str) -> bool:
    """A bare pattern (`*.pyc`) matches the filename; a directory pattern
    (`.real-test/verdicts/`) matches as a contiguous run inside the path's
    own segments, anywhere — multi-segment, not just a bare name."""
    import fnmatch
    if not pat.endswith("/"):
        return fnmatch.fnmatch(name, pat)
    pat_parts = pat[:-1].split("/")
    n = len(pat_parts)
    return any(parts[i:i + n] == pat_parts for i in range(len(parts) - n + 1))


def _is_regenerable(path: str) -> bool:
    name, parts = path.rsplit("/", 1)[-1], path.split("/")
    return any(_pattern_matches(parts, name, pat) for pat in REGENERABLE_IGNORED)


def _worktree_danger(wt: Path, e: dict) -> str | None:
    if recent_activity_lock(wt):
        return (f"attività concorrente rilevata negli ultimi {LOCK_WINDOW_SECONDS}s "
                "— salta, non toccare")
    op = mid_operation(wt)
    if op:
        return f"{op} in corso"
    if is_dirty(wt):
        return "modifiche non committate"
    if has_ignored_content(wt):
        return "contiene file ignorati non vuoti (.gitignore) — mai rimosso senza controllo umano"
    method_open = _method_ledger_open(wt)
    if method_open:
        return f"piano .method/ledger.md aperto: {method_open}"
    if e.get("locked"):
        return "git worktree lock attivo"
    return None


def _worktree_info(repo: Path, e: dict, cwds: set[str]) -> WorktreeInfo:
    """IN_USE checked BEFORE danger/DIRTY, matching worktree_verdict.verdict()'s
    own documented precedence (found via cross-check against the real
    _polaris repo: this file's OWN worktree was both dirty and lsof-active,
    and reported DIRTY — the pure decision table's precedence was silently
    unused because this orchestration decided which flag to set first)."""
    wt = Path(e["worktree"])
    branch = e.get("branch", "").removeprefix("refs/heads/") or None
    if is_in_use(wt, cwds):
        return WorktreeInfo(path=str(wt), branch=branch, in_use=True)
    if _worktree_danger(wt, e):
        return WorktreeInfo(path=str(wt), branch=branch, dirty=True)
    return _pr_backed_info(repo, wt, branch)


def _pr_backed_info(repo: Path, wt: Path, branch: str | None) -> WorktreeInfo:
    if branch is None:
        return WorktreeInfo(path=str(wt), branch=None)  # detached -> ACTIVE
    local_tip = git(wt, "rev-parse", "HEAD", check=False)
    pr, err, locally_merged = _merge_truth(repo, branch, default_branch(repo))
    if locally_merged:
        # same truth close_worktree would accept without ever calling gh —
        # a synthetic PR (number=0) lets verdict()'s existing CLOSABLE
        # branch fire without a second decision table for this case.
        synthetic = PRInfo(number=0, head_ref_oid=local_tip)
        return WorktreeInfo(path=str(wt), branch=branch, local_tip=local_tip, pr=synthetic)
    if pr and pr.get("state") == "MERGED" and local_tip == pr.get("headRefOid"):
        unfetched = _mergecommit_unverifiable(repo, pr, default_branch(repo))
        if unfetched:  # GAP-1: never claim CLOSABLE for a row close_worktree can't close
            return WorktreeInfo(path=str(wt), branch=branch, error=f"UNFETCHED: {unfetched}")
    pr_info = (PRInfo(number=pr.get("number", 0), head_ref_oid=pr.get("headRefOid", ""))
               if pr and pr.get("state") == "MERGED" else None)
    return WorktreeInfo(path=str(wt), branch=branch, local_tip=local_tip, pr=pr_info, error=err)


def _verdict_note(wt: Path, e: dict, info: WorktreeInfo) -> str:
    v = verdict(info)
    if v == "?":
        return info.error or ""
    if v == "IN_USE":
        return "processo o attività recente nel worktree — mai rimosso"
    if v == "DIRTY":
        return _worktree_danger(wt, e) or "modifiche non committate"
    if info.pr and not info.pr.number:
        return "mergiato localmente (nessuna PR)"
    if info.pr and v == "CLOSABLE":
        return f"pr#{info.pr.number}"
    if info.pr and v == "COMMITS_AFTER_MERGE":
        return f"pr#{info.pr.number} tip={info.local_tip} head={info.pr.head_ref_oid}"
    return ""


# ------------------------------------------------------------------ census: stash

def stash_rows(repo: Path, blocked: bool) -> list[Row]:
    out = git(repo, "stash", "list", "--format=%gd%x01%cI%x01%s", check=False)
    rows = []
    for line in out.splitlines():
        ref, when, msg = line.split("\x01", 2)
        a = age_days(when)
        cls = "pericoloso" if blocked else ("vivo" if a <= AGE_LIVE_DAYS else
                                             "orfano" if a > AGE_ORPHAN_DAYS else "vivo")
        note = "merge/rebase in corso nel repo — non toccare" if blocked else msg
        rows.append(Row("stash", ref, cls, round(a, 1), note, {"message": msg}))
    return rows


# ------------------------------------------------------------------ census: PR (gh)

def open_prs(repo: Path) -> tuple[dict[str, dict], bool]:
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json",
             "number,headRefName,createdAt,updatedAt,isDraft,mergeable,url"],
            cwd=repo, capture_output=True, text=True)
    except FileNotFoundError:
        # gh non installato affatto: prima di #252 questo saliva come traceback
        # grezzo, non come il degrado descritto sotto (bug reale, trovato qui).
        return {}, False
    if r.returncode != 0:
        return {}, False  # gh presente ma non autenticato/rate-limited → degrada, non fallisce
    return {p["headRefName"]: p for p in json.loads(r.stdout)}, True


# ------------------------------------------------------------------------ census

def census(repo: Path) -> dict:
    default = default_branch(repo)
    prs, gh_ok = open_prs(repo)
    branches = branch_rows(repo, default, set(), prs)
    worktrees, wt_branches = worktree_rows(repo)
    main_blocked = mid_operation(repo) is not None
    stashes = stash_rows(repo, main_blocked)
    rows = worktrees + branches + stashes
    summary: dict[str, int] = {}
    for r in rows:
        summary[r.classification] = summary.get(r.classification, 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo), "default_branch": default, "gh_available": gh_ok,
        "rows": [asdict(r) for r in rows], "summary": summary,
    }


def find_repos(vault: Path) -> list[Path]:
    return sorted(p.parent for p in vault.glob("*/.git") if p.is_dir())


def cmd_census(args: argparse.Namespace) -> int:
    repos = [Path(r).resolve() for r in (args.repo or [])]
    if args.vault:
        repos += find_repos(Path(args.vault).resolve())
    if not repos:
        repos = [Path.cwd()]
    if args.tsv or args.apply:
        return _cmd_census_tsv(repos, args.apply)
    ledgers = [census(r) for r in repos]
    out = {"repos": ledgers} if len(ledgers) > 1 else ledgers[0]
    text = json.dumps(out, indent=2, ensure_ascii=False)
    Path(args.out).write_text(text + "\n") if args.out else None
    for ledger in ledgers:
        _print_summary(ledger)
    if args.out:
        print(f"\nledger completo → {args.out}")
    return 0


def _census_tsv_preflight(apply: bool) -> int | None:
    """None = go ahead; otherwise the exit code to refuse with. Checked ONCE,
    up front, so a batch --apply never starts acting on a partial read."""
    if shutil.which("gh") is None:
        print("gh not found on PATH — refusing to run (never falls back to "
              "`git branch --merged`, which is squash-merge-blind)", file=sys.stderr)
        return 2
    if apply and shutil.which("lsof") is None:
        # breaker FAIL 2: apply is destructive, so a degraded IN_USE guard
        # must refuse here the same way a missing gh does.
        print("lsof not found on PATH — refusing --apply (IN_USE cannot be "
              "proven safe without it)", file=sys.stderr)
        return 2
    return None


def _cmd_census_tsv(repos: list[Path], apply: bool) -> int:
    """#252's output contract: one `VERDETTO\\tbranch\\tpath\\tnote` line per
    worktree. Exit 0 clean, 1 if any row is '?' or a removal was attempted
    and failed, 2 on _census_tsv_preflight refusal. Never falls back to
    `git branch --merged`/`for-each-ref --merged` (squash-blind)."""
    refused = _census_tsv_preflight(apply)
    if refused is not None:
        return refused
    has_unknown, has_failed = False, False
    for repo in repos:
        unknown, failed = _census_one_repo(repo, apply)
        has_unknown, has_failed = has_unknown or unknown, has_failed or failed
    return 1 if (has_unknown or has_failed) else 0


def _tsv_field(s: str) -> str:
    """r3 FAIL-1: an unescaped literal TAB (legal in a filesystem path) in
    branch/path/note breaks #252's declared 4-field-per-row TSV contract."""
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def _census_one_repo(repo: Path, apply: bool) -> tuple[bool, bool]:
    """(has_unknown, has_failed). breaker r2 FAIL 2: a bad --repo (not a git
    repo at all) used to crash the whole batch — one bad repo must not take
    down the good ones queued behind it."""
    try:
        rows, _ = worktree_rows(repo)
    except Exception as exc:
        print(f"?\t-\t{_tsv_field(str(repo))}\t{_tsv_field(f'{type(exc).__name__}: {exc}'[:400])}")
        return True, False
    has_unknown = False
    for row in rows:
        branch = row.extra.get('branch') or '-'
        print(f"{row.classification}\t{_tsv_field(branch)}\t{_tsv_field(row.id)}\t{_tsv_field(row.note)}")
        has_unknown = has_unknown or row.classification == "?"
    if not apply:
        return has_unknown, False
    _, failed = _apply_removals(repo, rows)
    return has_unknown, failed > 0


def _apply_removals(repo: Path, rows: list[Row]) -> tuple[int, int]:
    """close_worktree/`worktree prune` only. `anchor` resolved before removal (r3 FAIL-4)."""
    anchor = _primary_worktree(repo)
    removed, failed, prune_needed = 0, 0, False
    for row in rows:
        if not removable(row.classification):
            continue
        if row.classification == "PRUNABLE":
            prune_needed = True
            removed += 1
            continue
        if close_worktree(anchor, row.id) == 0:
            removed += 1
        else:
            failed += 1
    if prune_needed:
        git(anchor, "worktree", "prune", check=False)
    print(f"removed={removed}", file=sys.stderr)
    return removed, failed


def cmd_gate(args: argparse.Namespace) -> int:
    """#130's open question 'agisce o propone', domanda 3: refuses a new
    worktree only at/above a DECLARED threshold. #130 has not declared a
    real number (blocked on #127) — default threshold is None, which never
    blocks; do not invent a number here."""
    if shutil.which("gh") is None:
        print("gh not found on PATH — refusing", file=sys.stderr)
        return 2
    repo = Path(args.repo or ".").resolve()
    rows, _ = worktree_rows(repo)
    closable = sum(1 for row in rows if row.classification == "CLOSABLE")
    blocked, msg = gate_decision(closable, args.threshold)
    print(msg)
    return 1 if blocked else 0


def _print_summary(ledger: dict) -> None:
    print(f"\n== {ledger['repo']} (default: {ledger['default_branch']}, gh: "
          f"{'ok' if ledger['gh_available'] else 'non disponibile — PR non censite'}) ==")
    tally = ("pericoloso", "orfano", "vivo", "mergiato-da-chiudere",
             "MAIN", "ACTIVE", "DIRTY", "IN_USE", "PRUNABLE",
             "CLOSABLE", "COMMITS_AFTER_MERGE", "?")
    for cls in tally:
        n = ledger["summary"].get(cls, 0)
        if n:
            print(f"  {cls}: {n}")
    flagged = ("pericoloso", "mergiato-da-chiudere", "DIRTY", "IN_USE",
               "CLOSABLE", "COMMITS_AFTER_MERGE", "?")
    for r in ledger["rows"]:
        if r["classification"] in flagged:
            print(f"    [{r['classification']}] {r['kind']} {r['id']} — {r['note']}")


# --------------------------------------------------------------- commit boundary

def cmd_commit_check(args: argparse.Namespace) -> int:
    """Measure the public Git diff seam; size is a concern signal, not proof of atomicity."""
    repo = Path(args.repo or ".").resolve()
    diff_args = ("diff", "--numstat", f"{args.base}...HEAD") if args.base else (
        "diff", "--numstat", "--cached")
    try:
        rows = git(repo, *diff_args).splitlines()
    except RuntimeError as exc:
        print(f"RIFIUTATO: {exc}")
        return 2
    if not rows:
        print(f"RIFIUTATO: nessuna modifica nel diff {'base=' + args.base if args.base else 'staged'}")
        return 2

    added = deleted = binary = 0
    for row in rows:
        add, remove, _ = row.split("\t", 2)
        if add == "-" or remove == "-":
            binary += 1
            continue
        added += int(add)
        deleted += int(remove)
    files = len(rows)
    lines = added + deleted
    concern = files > args.max_files or lines > args.max_lines or binary > 0
    status = "CONCERN" if concern else "OK"
    scope = f"base={args.base}" if args.base else "staged"
    print(f"{status} files={files} lines={lines} added={added} deleted={deleted} "
          f"binary={binary} scope={scope}")
    if concern:
        print("Split by one behavior before commit, or record why this boundary is indivisible.")
        return 3
    return 0


# ------------------------------------------------------------------------- close

LOG = "polaris-cantiere/removed-log.jsonl"


def _snapshot(repo: Path, ref: str, action: str, target: str, sha: str | None = None) -> None:
    sha = sha or git(repo, "rev-parse", ref, check=False) or "n/a"
    logp = git_common_dir(repo) / LOG
    logp.parent.mkdir(exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "action": action,
             "target": target, "sha": sha}
    with logp.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _worktree_entry(repo: Path, wt: Path) -> dict:
    for e in worktree_entries(repo):
        if Path(e["worktree"]).resolve() == wt.resolve():
            return e
    return {}


def _print_danger_refusal(wt: Path, path: str, reason: str) -> int:
    """`reason` is _worktree_danger's own text. All stderr (r2 FAIL 3):
    --apply's TSV stream is not the place for a git-status dump."""
    op, method_open = mid_operation(wt), _method_ledger_open(wt)
    print(f"RIFIUTATO: {path} non è pulito o è in uso — questo è lo stato reale:", file=sys.stderr)
    print(subprocess.run(["git", "-C", str(wt), "status"], capture_output=True,
                          text=True).stdout, file=sys.stderr)
    if op:
        print(f"{op} in corso: risolvi o `git -C {wt} {op} --abort` PRIMA di ogni altra "
              "azione. NON usare `git stash` qui — durante un merge in conflitto può "
              "scartare MERGE_HEAD silenziosamente (misurato, registro G8#2).", file=sys.stderr)
    elif method_open:
        print(f"piano .method/ledger.md ancora aperto: {method_open} — metodologia "
              "dichiara che git-power lo drena alla chiusura, non lo cancella con lavoro "
              "aperto dentro (git status non lo vede: è git-ignored per design).", file=sys.stderr)
    else:
        print(f"{reason} — Salva prima (commit sul branch proprio o `git stash push -m ...`), "
              "poi ripeti il censimento. Nessun --force disponibile in questo comando.",
              file=sys.stderr)
    return 2


def _refuse_if_in_use(wt: Path, path: str) -> int | None:
    """Sampled fresh right here, not from a census-wide snapshot (r2 FAIL 1
    on #254: close_worktree — the ONE primitive `close` and --apply both
    route through — never checked IN_USE at all)."""
    if not is_in_use(wt, lsof_cwds()[0]):
        return None
    print(f"RIFIUTATO: '{path}' — processo o attività recente nel worktree.", file=sys.stderr)
    return 2


def close_worktree(repo: Path, path: str) -> int:
    """`repo` may be the linked worktree being removed; anchor on PRIMARY (r3 FAIL-4)."""
    wt = Path(path)
    refused = _refuse_if_in_use(wt, path)
    if refused is not None:
        return refused
    danger = _worktree_danger(wt, _worktree_entry(repo, wt))
    if danger:
        return _print_danger_refusal(wt, path, danger)
    branch = git(wt, "branch", "--show-current", check=False)
    if not branch:
        print(f"RIFIUTATO: '{path}' è detached, nessun branch da verificare mergiato.",
              file=sys.stderr)
        return 2
    anchor = _primary_worktree(repo)
    reason = _worktree_removable(anchor, branch, default_branch(anchor))
    if reason:
        print(f"RIFIUTATO: il worktree '{path}' non chiudibile — {reason}.", file=sys.stderr)
        return 2
    return _remove_worktree_or_refuse(anchor, wt, git(wt, "rev-parse", "HEAD"))


def _remove_worktree_or_refuse(repo: Path, wt: Path, sha: str) -> int:
    """Not git()/check=True: an uncaught RuntimeError there used to crash
    the whole run instead of refusing this one row (breaker FAIL 7 on PR
    #254, observed removing the PRIMARY worktree — _worktree_row's MAIN fix
    should prevent reaching here at all now; kept as defense in depth for
    any other reason `worktree remove` can fail: permissions, a race)."""
    path = str(wt)
    r = subprocess.run(["git", "-C", str(repo), "worktree", "remove", path],
                        capture_output=True, text=True)  # niente --force: git rifiuta se sporco
    if r.returncode != 0:
        print(f"RIFIUTATO: '{path}' — {r.stderr.strip()}", file=sys.stderr)
        return 2
    _snapshot(repo, path, "worktree-remove", path, sha)
    if r.stdout.strip():  # breaker r2 FAIL 3: no blank stdout line on the common empty case
        print(r.stdout, file=sys.stderr)
    return 0


def close_branch(repo: Path, name: str) -> int:
    default = default_branch(repo)
    if name not in merged_branches(repo, default):
        print(f"RIFIUTATO: '{name}' non è mergiato in {default} — safe-delete lo rifiuterebbe "
              f"comunque. Ispeziona con: git -C {repo} log {name} ^{default} --oneline")
        return 2
    sha = git(repo, "rev-parse", name)
    out = git(repo, "branch", "-d", name)  # -d (safe), mai -D
    _snapshot(repo, name, "branch-delete", name, sha)
    print(out)
    return 0


def close_stash(repo: Path, ref: str, drop: bool) -> int:
    if mid_operation(repo):
        print(f"RIFIUTATO: merge/rebase in corso in {repo} — {ref} resta intatto "
              "finché non risolvi (bypass-test G8#2).")
        return 2
    print(git(repo, "stash", "show", "-p", ref, check=False))
    sha = git(repo, "rev-parse", ref)
    out = git(repo, "stash", "drop" if drop else "pop", ref)
    _snapshot(repo, ref, "stash-drop" if drop else "stash-pop", ref, sha)
    print(out)
    return 0


def close_reset_hard(repo: Path, ref: str) -> int:
    """Forma guardata di `git reset --hard <ref>` (description: reset --hard,
    hard-rule founder 2026-08-03: 9 file persi con un reset --hard su un tree
    con lavoro altrui). La guardia vive dentro git()/_guard, non qui — anche
    chiamando git() a mano un tree sporco/mid-operazione/con attività recente
    rifiuta comunque, sempre; qui si traduce solo il rifiuto in RIFIUTATO/
    EXIT 2 con `git status` invece di un'eccezione grezza."""
    try:
        out = git(repo, "reset", "--hard", ref)
    except Refused as e:
        print(f"RIFIUTATO: {e}")
        print(subprocess.run(["git", "-C", str(repo), "status"], capture_output=True,
                              text=True).stdout)
        return 2
    _snapshot(repo, "ORIG_HEAD", "reset-hard", ref)  # git la scrive lei stessa dopo il reset
    print(out)
    return 0


def prepare_rebase(repo: Path, branch: str) -> int:
    default = default_branch(repo)
    scratch = repo.parent / f".cantiere-scratch-{branch.replace('/', '-')}"
    git(repo, "worktree", "add", "--detach", str(scratch), branch)
    r = subprocess.run(["git", "-C", str(scratch), "rebase", default],
                        capture_output=True, text=True)
    if r.returncode == 0:
        print(f"rebase pulito su {default} — worktree preparato in {scratch}, "
              f"nulla toccato sull'originale. Se vuoi promuoverlo: branch dal worktree + PR.")
        return 0
    print(f"CONFLITTO reale (non un rifiuto meccanico): {r.stdout}\n{r.stderr}")
    print(f"worktree lasciato in {scratch} per la risoluzione — mai auto-risolto.")
    return 1


def cmd_close(args: argparse.Namespace) -> int:
    repo = Path(args.repo or ".").resolve()
    if args.target != args.confirm:
        print("RIFIUTATO: --confirm deve ripetere esattamente --target "
              "(guardia anti-refuso, mai un flag generico 'yes').")
        return 2
    try:
        if args.prepare_rebase:
            return prepare_rebase(repo, args.target)
        if args.target.startswith("stash@"):
            return close_stash(repo, args.target, args.drop)
        if Path(args.target).is_absolute():
            return close_worktree(repo, args.target)
        # branch names normally contain '/' (feat/x, docs/y): un ref esistente
        # vince sull'euristica di path — il vecchio "'/' ⇒ worktree" instradava
        # OGNI branch con slash a close_worktree (bug reale, batch A 2026-08-21)
        if git(repo, "show-ref", "--verify", f"refs/heads/{args.target}", check=False):
            return close_branch(repo, args.target)
        if "/" in args.target:
            return close_worktree(repo, args.target)
        return close_branch(repo, args.target)
    except RuntimeError as e:
        # bypass-eval L3: un target che esiste come path ma non è un worktree/
        # branch/stash valido faceva risalire un traceback grezzo (git_dir()
        # con check=True); ora è sempre RIFIUTATO/EXIT 2, mai uno stack trace.
        print(f"RIFIUTATO: '{args.target}' non è utilizzabile — {e}")
        return 2


def cmd_reset(args: argparse.Namespace) -> int:
    repo = Path(args.repo or ".").resolve()
    if args.confirm != args.to:
        print("RIFIUTATO: --confirm deve ripetere esattamente --to "
              "(stessa guardia anti-refuso di close).")
        return 2
    try:
        return close_reset_hard(repo, args.to)
    except RuntimeError as e:
        print(f"RIFIUTATO: '{args.to}' non è un ref valido in {repo} — {e}")
        return 2


# ------------------------------------------------------------ lifecycle router

def _run_gh(args: list[str], cwd: Path) -> subprocess.CompletedProcess | str:
    """A CompletedProcess, or an error string for the two ways gh itself can
    fail to even answer (breaker FAIL 4 on PR #254: an uncaught
    TimeoutExpired used to crash the whole run, not just this one row)."""
    try:
        return subprocess.run(["gh", *args], cwd=cwd, capture_output=True, text=True,
                              timeout=GH_TIMEOUT_SECONDS)
    except FileNotFoundError:
        return "gh non è installato"
    except subprocess.TimeoutExpired:
        return f"gh non ha risposto entro {GH_TIMEOUT_SECONDS}s"


def _pr_lookup(repo: Path, branch: str | None = None) -> tuple[dict | None, str | None]:
    """GitHub ground truth for 'merged' (squash-aware, unlike merged_branches
    below). `cwd=repo` works even for a DIFFERENT worktree's branch — all
    worktrees share the same remote via the common .git dir.
    (pr, None) success · (None, None) genuinely no PR · (None, error)."""
    args = ["pr", "view"] + ([branch] if branch else [])
    args += ["--json", "state,mergedAt,headRefName,baseRefName,mergeCommit,headRefOid,number"]
    r = _run_gh(args, repo)
    if isinstance(r, str):
        return None, r
    if r.returncode == 0:
        return _parse_pr_json(r.stdout)
    stderr = (r.stderr or "").lower()
    if "no pull requests found" in stderr or "no git remotes found" in stderr:
        return None, None  # no remote at all -> definite "no PR", not an uncertain failure
    # FAIL 3: multi-line gh stderr broke the one-row-per-line TSV contract —
    # collapsed before it reaches a row. r2 FAIL 4: an empty string here is
    # FALSY (verdict() tests `if info.error`) and silently promotes to ACTIVE.
    msg = " ".join((r.stderr or r.stdout).split())[:200]
    return None, msg or f"gh exited {r.returncode} without output"


def _parse_pr_json(stdout: str) -> tuple[dict | None, str | None]:
    """r2 FAIL 2: gh exit 0 with malformed/empty stdout used to raise
    uncaught — a row-level error, not a crash; also reachable from
    close_worktree/_finalize, which have no per-row try/except of their own."""
    try:
        return json.loads(stdout), None
    except json.JSONDecodeError:
        return None, f"gh returned unparseable JSON: {stdout[:100]!r}"


def _current_pr(repo: Path, branch: str | None = None) -> dict | None:
    """Back-compat wrapper — _finalize and phase post-push only ever need
    the PR-or-None answer, never the error detail (they RIFIUTA either way)."""
    return _pr_lookup(repo, branch)[0]


def _merge_gap_reason(pr: dict | None, local_tip: str) -> str | None:
    """None = the branch is provably safe to remove. Otherwise the reason it
    is not — including the gap the OLD close_worktree/_finalize both had:
    neither ever compared the local tip against the PR's headRefOid, so a
    worktree with COMMITS ADDED AFTER the PR merged would have been silently
    deleted (found while extending this function for #252)."""
    if not pr:
        return "nessuna PR trovata per questo branch"
    if pr.get("state") != "MERGED":
        return f"PR {pr.get('state', 'UNKNOWN')}, non mergiata"
    if pr.get("headRefOid") and local_tip != pr["headRefOid"]:
        return f"branch ha commit dopo il merge (tip={local_tip} head={pr['headRefOid']})"
    return None


def _merge_target(repo: Path, base: str) -> str:
    remote = f"origin/{base}"
    return remote if git(repo, "show-ref", "--verify", f"refs/remotes/{remote}",
                         check=False) else base


def _merge_truth(repo: Path, branch: str, base: str) -> tuple[dict | None, str | None, bool]:
    """(pr, error, locally_merged). The gh-independent ancestor check runs
    FIRST and, on its own, still proves a PLAIN local merge safe (the
    original check close_worktree always had, and the only path a repo with
    no PR/gh at all — or a merge done by hand — can ever take). Only when
    that fails does this fall through to gh PR-truth, which is what proves a
    SQUASH merge safe (never an ancestor locally, by definition)."""
    target = _merge_target(repo, base)
    if _is_ancestor(repo, f"refs/heads/{branch}", target):
        return None, None, True
    pr, err = _pr_lookup(repo, branch)
    return pr, err, False


def _mergecommit_unverifiable(repo: Path, pr: dict, base: str) -> str | None:
    """None = the merge commit is fetched and provably an ancestor of
    origin/<base>. Shared by close_worktree's removal gate AND census's
    CLOSABLE call (breaker r2 GAP-1 on #254: census said CLOSABLE from
    headRefOid==tip alone, --apply then refused forever because the squash
    commit was never fetched — two truths that could disagree)."""
    merge_oid = (pr.get("mergeCommit") or {}).get("oid")
    if not merge_oid:
        return "PR MERGED senza mergeCommit verificabile"
    git(repo, "fetch", "origin", base, check=False)
    target = _merge_target(repo, base)
    if not _is_ancestor(repo, merge_oid, target):
        return f"merge commit {merge_oid} non è contenuto in {target}"
    return None


def _worktree_removable(repo: Path, branch: str, base: str) -> str | None:
    """None = safe to remove. Mirrors _finalize's own proof (gh PR MERGED +
    merge commit ancestor of origin/<base>) for the squash case; a plain
    local merge is still handled by _merge_truth's ancestor check alone."""
    pr, err, locally_merged = _merge_truth(repo, branch, base)
    if locally_merged:
        return None
    if err:
        return f"gh non ha risposto: {err}"
    local_tip = git(repo, "rev-parse", f"refs/heads/{branch}", check=False)
    reason = _merge_gap_reason(pr, local_tip)
    if reason:
        return reason
    return _mergecommit_unverifiable(repo, pr, base)


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True, text=True,
    ).returncode == 0


def _primary_worktree(repo: Path) -> Path:
    return _primary_from_entries(worktree_entries(repo), repo)


def _align_primary(primary: Path, base: str) -> str:
    remote = f"origin/{base}"
    if mid_operation(primary):
        return "MAIN_OPERATION_PRESERVED"
    if is_dirty(primary):
        return "MAIN_DIRTY_PRESERVED"
    if git(primary, "branch", "--show-current", check=False) != base:
        return "MAIN_OTHER_BRANCH_PRESERVED"
    head = git(primary, "rev-parse", "HEAD")
    remote_head = git(primary, "rev-parse", remote, check=False)
    if not remote_head or head == remote_head:
        return "MAIN_ALIGNED"
    if not _is_ancestor(primary, head, remote):
        return "MAIN_DIVERGED_PRESERVED"
    git(primary, "merge", "--ff-only", remote)
    return "MAIN_FAST_FORWARDED"


def _finalize_apply(target: Path, branch: str, base: str) -> int:
    if mid_operation(target) or is_dirty(target) or _method_ledger_open(target):
        print("RIFIUTATO: il worktree corrente contiene lavoro o un'operazione aperta.")
        return 2
    primary = _primary_worktree(target)
    main_state = _align_primary(primary, base)
    branch_sha = git(target, "rev-parse", f"refs/heads/{branch}", check=False)
    git(primary, "worktree", "remove", str(target))
    _snapshot(primary, branch_sha, "worktree-remove-pr-merged", str(target), branch_sha)
    git(primary, "update-ref", "-d", f"refs/heads/{branch}", branch_sha)
    _snapshot(primary, branch_sha, "branch-delete-pr-merged", branch, branch_sha)
    git(primary, "worktree", "prune")
    print(f"FINALIZED: worktree={target} branch={branch} {main_state}")
    return 0


def _finalize_pr_status(target: Path) -> tuple[str, dict | None]:
    """('REFUSED'|'KEEP'|'MERGED', pr) — the only _finalize-specific branch
    (a real but not-yet-merged PR keeps the worktree alive, exit 0)."""
    pr = _current_pr(target)
    if not pr:
        print("RIFIUTATO: nessuna PR verificabile per il branch corrente.")
        return "REFUSED", None
    if pr.get("state") != "MERGED":
        print(f"KEEP: PR {pr.get('state', 'UNKNOWN')} — worktree e branch restano vivi.")
        return "KEEP", None
    return "MERGED", pr


def _finalize(repo: Path, confirm: str | None) -> int:
    """#252 fold: delegates its safety proof to _worktree_removable, the
    same one close_worktree/census --apply use — never two truths."""
    target = repo.resolve()
    confirm_ok = confirm and Path(confirm).resolve() == target and Path.cwd().resolve() == target
    if not confirm_ok:
        print("RIFIUTATO: finalize richiede --confirm uguale al worktree corrente, eseguito da lì.")
        return 2
    branch = git(target, "branch", "--show-current", check=False)
    status, pr = _finalize_pr_status(target)
    if status != "MERGED":
        return 0 if status == "KEEP" else 2
    base = pr.get("baseRefName") or default_branch(target)
    reason = _worktree_removable(target, branch, base)
    if reason:
        print(f"RIFIUTATO: {reason}.")
        return 2
    return _finalize_apply(target, branch, base)


def cmd_phase(args: argparse.Namespace) -> int:
    repo = Path(args.repo or ".").resolve()
    if args.phase == "pre-pr":
        base = f"origin/{default_branch(repo)}"
        return cmd_commit_check(argparse.Namespace(
            repo=str(repo), base=base, max_files=args.max_files, max_lines=args.max_lines))
    if args.phase == "checkpoint":
        branch = git(repo, "branch", "--show-current", check=False)
        if is_dirty(repo):
            print(f"BLOCKED_DIRTY: branch={branch} — /update non è completo finché ogni "
                  "modifica della lane non è committata con pathspec e commit-check.")
            return 2
        print(f"CHECKPOINT: branch={branch} CLEAN")
        return 0
    if args.phase == "push":
        branch = git(repo, "branch", "--show-current", check=False)
        if not branch or branch == default_branch(repo):
            print("RIFIUTATO: phase push richiede un feature branch, mai il default branch.")
            return 2
        upstream = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name",
                       "@{upstream}", check=False)
        expected = f"origin/{branch}"
        try:
            out = (git(repo, "push") if upstream == expected
                   else git(repo, "push", "-u", "origin", branch))
        except RuntimeError as exc:
            print(f"RIFIUTATO: push fallito — {exc}")
            return 2
        print(f"PUSHED: branch={branch} upstream={expected}")
        if out:
            print(out)
        return 0
    if args.phase == "post-push":
        pr = _current_pr(repo)
        if not pr:
            print("RIFIUTATO: push presente ma nessuna PR verificabile.")
            return 2
        if pr.get("state") == "MERGED":
            print(f"READY_FINALIZE: PR MERGED — run phase finalize for {repo}")
        else:
            print(f"KEEP: PR {pr.get('state', 'UNKNOWN')} — worktree e branch restano vivi.")
        return 0
    return _finalize(repo, args.confirm)


# ---------------------------------------------------------------------- selfcheck

def _init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t.t")
    git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("1")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def _selfcheck_merged_branch_closes(root: Path) -> None:
    repo = _init_repo(root)
    git(repo, "checkout", "-q", "-b", "feat/done")
    (repo / "f.txt").write_text("2")
    git(repo, "commit", "-q", "-am", "work")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "feat/done")
    assert classify_branch(True, 99, None) == "mergiato-da-chiudere"
    assert close_branch(repo, "feat/done") == 0
    assert "feat/done" not in git(repo, "branch", "--list")
    # dispatch-level: un branch con '/' deve arrivare a close_branch, non essere
    # scambiato per un path di worktree (bug 2026-08-21, trovato dal batch A)
    git(repo, "checkout", "-q", "-b", "docs/done2")
    (repo / "f.txt").write_text("3")
    git(repo, "commit", "-q", "-am", "work2")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "docs/done2")
    ns = argparse.Namespace(repo=str(repo), target="docs/done2", confirm="docs/done2",
                            prepare_rebase=False, drop=False)
    assert cmd_close(ns) == 0, "dispatch: branch con slash deve chiudersi via cmd_close"
    assert "docs/done2" not in git(repo, "branch", "--list")


def _selfcheck_dirty_worktree_refused(root: Path) -> None:
    """BYPASS-TEST G7#2: deve rifiutare, mai proporre --force."""
    repo = _init_repo(root)
    wt = root / "wt-dirty"
    git(repo, "worktree", "add", "-q", "-b", "feat/dirty", str(wt))
    (wt / "f.txt").write_text("uncommitted")
    assert close_worktree(repo, str(wt)) == 2, "un worktree sporco deve essere rifiutato"
    assert wt.exists(), "il worktree non deve essere rimosso"
    _assert_no_force_call_sites()


def _assert_no_force_call_sites() -> None:
    """Statico via AST (non grep testuale, evita falsi positivi su commenti/docstring che
    PARLANO di --force per spiegare perché è assente): ogni Call a un qualunque entrypoint
    shell nel file, ispezionati gli argomenti stringa letterali — nessuno può essere
    esattamente '--force' o '-D'. Bypass-eval L4 (2026-08-09): la versione precedente
    controllava solo Call di nome letterale 'git'/'run', quindi una futura chiamata con un
    nome diverso (Popen/check_call/os.system/un alias) avrebbe superato il selfcheck con
    EXIT=0 certificando come blindato uno script compromesso — allargata a tutti gli
    entrypoint shell noti. Questo NON sostituisce la guardia runtime in git()/_guard (che
    protegge anche i chiamanti fuori da questo file): è difesa in profondità sulla fonte.
    --hard NON è bandito qui apposta: reset --hard è permesso condizionatamente, guardato
    a runtime da _guard, non vietato per costruzione come --force/-D."""
    import ast
    banned = {"--force", "-D"}
    entrypoints = {"git", "run", "Popen", "call", "check_call", "check_output",
                   "system", "popen"}

    def literal_args(node: ast.Call) -> list[str]:
        vals = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        for a in node.args:
            if isinstance(a, ast.List):
                vals += [e.value for e in a.elts if isinstance(e, ast.Constant)
                         and isinstance(e.value, str)]
        return vals

    tree = ast.parse(Path(__file__).read_text())
    # I selfcheck (_selfcheck_direct_git_call_still_refuses) COSTRUISCONO deliberatamente
    # una chiamata --force/-D come input di test, dentro un try/except Refused, per provare
    # che git()/_guard la rifiuta — non sono un sito vulnerabile, sono la prova che non lo è.
    # Esclusi per intervallo di riga, non per nome libero: un vero sito vulnerabile altrove
    # nel file resta rilevato.
    selfcheck_ranges = [(n.lineno, n.end_lineno) for n in ast.walk(tree)
                         if isinstance(n, ast.FunctionDef)
                         and (n.name.startswith("_selfcheck") or n.name == "selfcheck")]

    def in_selfcheck(lineno: int) -> bool:
        return any(lo <= lineno <= hi for lo, hi in selfcheck_ranges)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or in_selfcheck(node.lineno):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        if name not in entrypoints:
            continue
        hit = banned & set(literal_args(node))
        assert not hit, f"riga {node.lineno}: {hit} passato a una chiamata shell reale ({name})"


def _selfcheck_stash_blocked_during_merge(root: Path) -> None:
    """BYPASS-TEST G8#2: merge in corso con conflitto reale → stash esistente intoccabile.
    Lo stash è creato PRIMA del merge (non durante): il fixture non usa esso stesso
    'git stash push' mid-conflitto, perché quello è proprio il comando che il registro
    misura scartare MERGE_HEAD silenziosamente — non lo si riproduce per costruire il test."""
    repo = _init_repo(root)
    (repo / "g.txt").write_text("x")
    git(repo, "add", "g.txt")
    git(repo, "commit", "-q", "-m", "g")
    (repo / "g.txt").write_text("y")
    subprocess.run(["git", "-C", str(repo), "stash", "push", "-q", "-m", "unrelated"],
                   check=True)
    assert "stash@{0}" in git(repo, "stash", "list")

    git(repo, "checkout", "-q", "-b", "a")
    (repo / "f.txt").write_text("A\n")
    git(repo, "commit", "-q", "-am", "a")
    git(repo, "checkout", "-q", "main")
    (repo / "f.txt").write_text("M\n")
    git(repo, "commit", "-q", "-am", "m")
    subprocess.run(["git", "-C", str(repo), "merge", "a"], capture_output=True, text=True)
    assert mid_operation(repo) == "merge", "il conflitto deve lasciare MERGE_HEAD presente"

    rows = stash_rows(repo, blocked=True)
    assert rows and rows[0].classification == "pericoloso"
    assert close_stash(repo, "stash@{0}", drop=False) == 2, \
        "close deve rifiutare uno stash mentre un merge è in corso, anche se lo stash è estraneo"
    assert (git_dir(repo) / "MERGE_HEAD").exists(), "il merge in corso deve sopravvivere intatto"
    assert "stash@{0}" in git(repo, "stash", "list"), "lo stash rifiutato non va toccato"


def _age_head(repo: Path) -> None:
    """Backdata HEAD oltre LOCK_WINDOW_SECONDS — isola un test da
    recent_activity_lock quando quel gate non è ciò che si vuole provare."""
    import os
    head = git_dir(repo) / "HEAD"
    head.touch()
    old = time.time() - LOCK_WINDOW_SECONDS - 10
    os.utime(head, (old, old))


def _selfcheck_recent_activity_lock(root: Path) -> None:
    repo = _init_repo(root)
    assert recent_activity_lock(repo) is True, "HEAD appena scritto = lock attivo"
    _age_head(repo)
    assert recent_activity_lock(repo) is False


def _selfcheck_orphan_branch_never_force_deleted(root: Path) -> None:
    repo = _init_repo(root)
    git(repo, "checkout", "-q", "-b", "feat/orphan")
    (repo / "f.txt").write_text("orphan-only")
    git(repo, "commit", "-q", "-am", "orphan work")
    git(repo, "checkout", "-q", "main")
    assert close_branch(repo, "feat/orphan") == 2, "non mergiato → rifiutato, mai -D"
    assert "feat/orphan" in git(repo, "branch", "--list")


def _selfcheck_direct_git_call_still_refuses(root: Path) -> None:
    """BYPASS-TEST L1 (EVAL-cantiere-bypass §3): chiamare git() DIRETTAMENTE,
    non tramite close_worktree/close_branch/cmd_close/main(), con esattamente
    gli argomenti che l'incidente misurato usa — deve rifiutare comunque. È
    la prova che la guardia è nella primitiva, non solo nel dispatcher CLI."""
    repo = _init_repo(root)
    wt = root / "wt-dirty-direct"
    git(repo, "worktree", "add", "-q", "-b", "feat/dirty-direct", str(wt))
    (wt / "f.txt").write_text("uncommitted")
    try:
        git(repo, "worktree", "remove", "--force", str(wt))
        assert False, "git() doveva rifiutare --force, non eseguirlo"
    except Refused:
        pass
    assert wt.exists(), "il worktree deve sopravvivere a una chiamata diretta con --force"

    git(repo, "checkout", "-q", "-b", "feat/unmerged-direct")
    (repo / "f.txt").write_text("unmerged-work")
    git(repo, "commit", "-q", "-am", "unmerged")
    git(repo, "checkout", "-q", "main")
    try:
        git(repo, "branch", "-D", "feat/unmerged-direct")
        assert False, "git() doveva rifiutare -D, non eseguirlo"
    except Refused:
        pass
    assert "feat/unmerged-direct" in git(repo, "branch", "--list")

    (repo / "f.txt").write_text("dirty-for-reset")
    try:
        git(repo, "reset", "--hard", "HEAD")
        assert False, "git() doveva rifiutare reset --hard su un tree sporco"
    except Refused:
        pass
    assert is_dirty(repo), "le modifiche non committate devono sopravvivere al tentativo"

    subprocess.run(["git", "-C", str(repo), "stash", "push", "-q", "-m", "x"], check=True)
    try:
        git(repo, "stash", "clear")
        assert False, "git() doveva rifiutare stash clear"
    except Refused:
        pass
    assert "stash@{0}" in git(repo, "stash", "list")

    (repo / "untracked.txt").write_text("must survive")
    try:
        git(repo, "clean", "-fd")
        assert False, "git() doveva rifiutare clean -fd"
    except Refused:
        pass
    assert (repo / "untracked.txt").exists()

    (repo / "f.txt").write_text("dirty-checkout")
    try:
        git(repo, "checkout", "--", "f.txt")
        assert False, "git() doveva rifiutare checkout -- su tree sporco"
    except Refused:
        pass
    assert (repo / "f.txt").read_text() == "dirty-checkout"

    try:
        git(repo, "restore", "--worktree", "f.txt")
        assert False, "git() doveva rifiutare restore --worktree su tree sporco"
    except Refused:
        pass
    assert (repo / "f.txt").read_text() == "dirty-checkout"

    try:
        git(repo, "stash", "push", "-m", "must-not-hide")
        assert False, "git() doveva rifiutare stash su tree sporco"
    except Refused:
        pass
    assert (repo / "f.txt").read_text() == "dirty-checkout"
    _assert_no_force_call_sites()


def _selfcheck_reset_hard_guarded(root: Path) -> None:
    """BYPASS-TEST reset --hard (description: coperto — grep vuoto prima di
    questo fix, EVAL-cantiere-copertura §3): sporco → rifiutato senza
    perdere nulla; pulito → eseguito e loggato in removed-log.jsonl."""
    repo = _init_repo(root)
    (repo / "f.txt").write_text("uncommitted-before-reset")
    assert close_reset_hard(repo, "HEAD") == 2, "reset --hard su tree sporco deve rifiutare"
    assert is_dirty(repo), "le modifiche non committate devono sopravvivere al rifiuto"

    git(repo, "checkout", "-q", "-b", "feat/to-reset")
    (repo / "f.txt").write_text("committed-then-reset")
    git(repo, "commit", "-q", "-am", "work-to-lose")
    base = git(repo, "rev-parse", "HEAD~1")
    assert close_reset_hard(repo, base) == 0, "reset --hard su tree pulito deve procedere"
    assert git(repo, "rev-parse", "HEAD") == base
    log = (git_common_dir(repo) / LOG).read_text()
    assert '"action": "reset-hard"' in log, "il reset deve finire nel removed-log append-only"


def _selfcheck_method_ledger_blocks_close(root: Path) -> None:
    """EVAL-cantiere-copertura §4: contratto dichiarato da metodologia mai
    implementato. `.method/` è git-ignored per design — verificato qui che
    is_dirty() da solo NON lo vede (il gap reale), quindi la guardia deve
    stare in un check dedicato, non riusare quello esistente per magia."""
    repo = _init_repo(root)
    (repo / ".git" / "info" / "exclude").write_text(".method/\n")
    wt = root / "wt-method"
    git(repo, "worktree", "add", "-q", "-b", "feat/method", str(wt))
    _age_head(wt)  # isola il test dal recent_activity_lock (altro gate, non questo)
    (wt / ".method").mkdir()
    (wt / ".method" / "ledger.md").write_text("PLAN: test-plan\nTASK 1: started\n")
    assert not is_dirty(wt), "il gap reale: git status non vede .method/ ignorato"
    assert close_worktree(repo, str(wt)) == 2, "piano .method aperto deve rifiutare la chiusura"
    assert wt.exists(), "il worktree con piano .method aperto non va rimosso"
    (wt / ".method" / "ledger.md").write_text("PLAN: test-plan\nTASK 1: complete\n")
    git(repo, "merge", "-q", "feat/method")
    assert close_worktree(repo, str(wt)) == 0, "piano .method completo non deve bloccare"
    assert not wt.exists()


def _selfcheck_invalid_target_refused_not_crashed(root: Path) -> None:
    """BYPASS-TEST L3 (EVAL-cantiere-bypass §3): un path che esiste ma non è
    un worktree/branch/stash valido deve tornare RIFIUTATO/EXIT 2 dal
    dispatcher CLI, mai un traceback grezzo (git_dir() con check=True)."""
    repo = _init_repo(root)
    not_a_worktree = root / "not-a-worktree"
    not_a_worktree.mkdir()
    args = argparse.Namespace(repo=str(repo), target=str(not_a_worktree),
                               confirm=str(not_a_worktree), prepare_rebase=False, drop=False)
    assert cmd_close(args) == 2, "un path non-worktree deve tornare EXIT 2, non un traceback"


def _selfcheck_worktree_row_closable_via_local_merge(root: Path) -> None:
    """#252: the census worktree vocabulary, dependency-free (a LOCAL merge
    needs no gh/fake-gh — _merge_truth's ancestor check alone proves it,
    same truth close_worktree accepts). Covers CLOSABLE end to end: verdict,
    then --apply's own removal path (never -D/--force — _apply_removals
    routes through close_worktree, the same guarded primitive as `close`)."""
    repo = _init_repo(root)
    git(repo, "checkout", "-q", "-b", "feat/local-merge")
    (repo / "f.txt").write_text("2")
    git(repo, "commit", "-q", "-am", "work")
    git(repo, "checkout", "-q", "main")
    wt = root / "wt-local-merge"
    git(repo, "worktree", "add", "-q", str(wt), "feat/local-merge")
    git(repo, "merge", "-q", "feat/local-merge")
    _age_head(wt)
    rows, _ = worktree_rows(repo)
    row = next(r for r in rows if r.extra.get("branch") == "feat/local-merge")
    assert row.classification == "CLOSABLE", row.classification
    _apply_removals(repo, rows)
    assert not wt.exists(), "CLOSABLE deve essere rimosso da --apply"


def _selfcheck_worktree_row_dirty_never_apply_removed(root: Path) -> None:
    repo = _init_repo(root)
    wt = root / "wt-dirty-row"
    git(repo, "worktree", "add", "-q", "-b", "feat/dirty-row", str(wt))
    (wt / "f.txt").write_text("uncommitted")
    rows, _ = worktree_rows(repo)
    row = next(r for r in rows if r.extra.get("branch") == "feat/dirty-row")
    assert row.classification == "DIRTY", row.classification
    _apply_removals(repo, rows)
    assert wt.exists(), "DIRTY non deve mai essere rimosso da --apply"


def _selfcheck_census_tsv_refuses_without_gh(root: Path) -> None:
    """--apply/--tsv must exit 2 with zero rows when gh is entirely missing
    from PATH — never fall back to git branch --merged (squash-blind). A
    hardcoded "safe" PATH like /usr/bin:/bin is NOT gh-free everywhere: CI
    runners ship gh system-wide (found live on GitHub Actions) — build a
    PATH holding only git's own directory instead of guessing one."""
    import os
    repo = _init_repo(root)
    binonly = root / "bin-only-git"
    binonly.mkdir()
    (binonly / "git").symlink_to(shutil.which("git"))
    saved = os.environ.get("PATH")
    os.environ["PATH"] = str(binonly)
    try:
        assert shutil.which("gh") is None, "test invalido: gh e' comunque su PATH"
        rc = _cmd_census_tsv([repo], apply=True)
    finally:
        os.environ["PATH"] = saved
    assert rc == 2, f"gh assente deve dare exit 2, non {rc}"


def _selfcheck_apply_never_destroys_gitignored_content(root: Path) -> None:
    """Breaker FAIL 6 on PR #254: git status --porcelain never sees ignored
    files, so a merged worktree holding only .env-like content reported
    clean and was destroyed."""
    repo = _init_repo(root)
    git(repo, "checkout", "-q", "-b", "feat/ignored")
    (repo / ".gitignore").write_text(".env\n")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-q", "-am", "gitignore")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "feat/ignored")
    wt = root / "wt-ignored"
    git(repo, "worktree", "add", "-q", str(wt), "feat/ignored")
    _age_head(wt)
    (wt / ".env").write_text("SECRET=1\n")
    assert not is_dirty(wt), "il gap reale: git status non vede .env ignorato"
    assert close_worktree(repo, str(wt)) == 2, "contenuto ignorato non vuoto deve rifiutare"
    assert (wt / ".env").exists()


def _selfcheck_main_worktree_recognised_from_subdirectory(root: Path) -> None:
    """Breaker FAIL 7 on PR #254: MAIN was decided by comparing to the
    --repo ARGUMENT (subprocess.run "census --repo ." from a subdirectory
    stopped seeing the primary worktree as MAIN)."""
    repo = _init_repo(root)
    (repo / "sub").mkdir()
    rows, _ = worktree_rows(repo / "sub")
    main_rows = [r for r in rows if r.classification == "MAIN"]
    assert len(main_rows) == 1, "il worktree primario deve restare riconoscibile da una sottocartella"


def selfcheck() -> int:
    import tempfile
    checks = [_selfcheck_merged_branch_closes, _selfcheck_dirty_worktree_refused,
              _selfcheck_stash_blocked_during_merge, _selfcheck_recent_activity_lock,
              _selfcheck_orphan_branch_never_force_deleted,
              _selfcheck_direct_git_call_still_refuses, _selfcheck_reset_hard_guarded,
              _selfcheck_method_ledger_blocks_close,
              _selfcheck_invalid_target_refused_not_crashed,
              _selfcheck_worktree_row_closable_via_local_merge,
              _selfcheck_worktree_row_dirty_never_apply_removed,
              _selfcheck_census_tsv_refuses_without_gh,
              _selfcheck_apply_never_destroys_gitignored_content,
              _selfcheck_main_worktree_recognised_from_subdirectory]
    for fn in checks:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"ok  {fn.__name__}")
    print(f"SELFCHECK OK — {len(checks)} rami provati su fixture temporanee reali")
    return 0


# ------------------------------------------------------------------------------

def _add_census_parser(sub: argparse._SubParsersAction) -> None:
    c = sub.add_parser("census")
    c.add_argument("--repo", action="append")
    c.add_argument("--vault")
    c.add_argument("--out")
    c.add_argument("--tsv", action="store_true",
                    help="#252 output contract: one VERDETTO\\tbranch\\tpath\\tnote line "
                         "per worktree row, exit 0/1/2 (see _cmd_census_tsv docstring)")
    c.add_argument("--apply", action="store_true",
                    help="remove only CLOSABLE/PRUNABLE worktrees, via the same guarded "
                         "close_worktree() a human `close` call uses — never DIRTY/IN_USE, "
                         "never -D/--force. Implies --tsv's exit-code contract.")
    c.set_defaults(func=cmd_census)


def _add_gate_parser(sub: argparse._SubParsersAction) -> None:
    g = sub.add_parser("gate")
    g.add_argument("--repo")
    g.add_argument("--threshold", type=int, default=None)
    g.set_defaults(func=cmd_gate)


def _add_close_parser(sub: argparse._SubParsersAction) -> None:
    cl = sub.add_parser("close")
    cl.add_argument("--repo")
    cl.add_argument("--target", required=True)
    cl.add_argument("--confirm", required=True)
    cl.add_argument("--drop", action="store_true")
    cl.add_argument("--prepare-rebase", action="store_true")
    cl.set_defaults(func=cmd_close)


def _add_reset_parser(sub: argparse._SubParsersAction) -> None:
    rh = sub.add_parser("reset-hard")
    rh.add_argument("--repo")
    rh.add_argument("--to", required=True)
    rh.add_argument("--confirm", required=True)
    rh.set_defaults(func=cmd_reset)


def _add_commit_check_parser(sub: argparse._SubParsersAction) -> None:
    cc = sub.add_parser("commit-check")
    cc.add_argument("--repo")
    cc.add_argument("--base")
    cc.add_argument("--max-files", type=int, default=5)
    cc.add_argument("--max-lines", type=int, default=200)
    cc.set_defaults(func=cmd_commit_check)


def _add_phase_parser(sub: argparse._SubParsersAction) -> None:
    ph = sub.add_parser("phase")
    ph.add_argument("phase", choices=("checkpoint", "pre-pr", "push", "post-push", "finalize"))
    ph.add_argument("--repo")
    ph.add_argument("--confirm")
    ph.add_argument("--max-files", type=int, default=5)
    ph.add_argument("--max-lines", type=int, default=200)
    ph.set_defaults(func=cmd_phase)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="git-power")
    p.add_argument("--selfcheck", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    for add_parser in (_add_census_parser, _add_gate_parser, _add_close_parser,
                       _add_reset_parser, _add_commit_check_parser, _add_phase_parser):
        add_parser(sub)

    a = p.parse_args(argv)
    if a.selfcheck:
        return selfcheck()
    if not getattr(a, "func", None):
        p.print_help()
        return 1
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
