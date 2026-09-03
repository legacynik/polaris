---
name: end
description: Polaris skill — close a repository-first team session with a handoff, decisions/lessons written to the ledgers, a plan tick and a pathspec-only commit. Trigger when stopping work, before a multi-day pause, or on "wrap up / end session / /end".
user-invocable: true
version: 1.11.0
invokes: [git-power]
---

# /end — close without losing the handoff

Use the same root and contributor resolver as `/start`. Before writing anything, read the ground
truth:

```bash
git rev-parse --abbrev-ref HEAD   # confirm the branch (shared checkouts)
git status --short                 # what actually changed this session
```


## One home (write-target for ALL session-state)

Every write in this skill — session log, handoff file, plan tick, `current.md`,
decisions/lessons appends — lands in the **MAIN worktree**, whichever worktree/branch this panel
sits in. One home = appends from every panel land in one file, in time order; per-worktree copies
diverge on N branches and lose data at merge. Provenance lives in the block header (`wt:`/`branch:`).

```bash
eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"
```

One resolver, shared with `/start`: `MAIN_WT`, `ROOT`, `LOGIN`, `CURRENT` and `RADAR`. It exits
non-zero rather than guessing — not a git checkout, no contract, no resolvable login all stop here
instead of writing to an invented path. Three copies of this rule used to live in the package.


`$CURRENT` is THE cockpit of this repo — one per repo, whatever path the resolver hands back. Write
`$CURRENT`, never a cwd-relative `state/current.md`: inside a worktree that path is gitignored and
never comes back. There is no second cockpit to keep in step, and nothing here writes one.

## State hygiene (every run — the skills are the writers AND the janitors)

Before writing, sweep the CURRENT repo's Polaris root for strays (multi-panel machines drift:
older sessions write with pre-patch instructions):

1. Session files in the LEGACY top-level `<root>/sessions/` (not `team/<login>/sessions/`):
   `git mv` (or mv, if untracked) each into `team/<login>/sessions/`, adding a `-legacy` suffix
   on filename collision. Note the move in one line of this run's checkpoint — never silently.
2. Cockpits stranded in OTHER worktrees (`<worktree>/_polaris/state/current.md`): report them and
   name the one command that brings them home without merging or overwriting —
   `python3 "$ROOT/scripts/state_home.py" migrate`, which refuses loudly on an occupied
   destination and collects into `team/<login>/handoff/strays/<worktree>-<date>.md`. Never move
   them silently.
3. Non-canonical `current` variants in `<root>/state/` (anything beyond `current.md`, `todos.md`,
   `goals.md`, `backlog*.md`): FLAG them in your output with their mtime and first heading; fold
   their still-live content into the cockpit only on explicit confirmation. A repo that still
   carries an older dense cockpit beside `current.md` is exactly this case, not an exception.
4. **Branch state** — classify only the current lane before writing the handoff:

   ```bash
   GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
   python3 "$GP" phase post-push --repo "$PWD"
   ```

   `KEEP` means the worktree stays in the handoff. `READY_FINALIZE` means it may close only after
   the handoff commit. Unknown or unverifiable PR state is never cleanup permission.
Skip silently when the repo is already clean. Never delete anything in steps 1–3.

## Step 1 — Write the handoff

Append to `team/<login>/sessions/YYYY-MM-DD-@<github-login>.md`:

**Stesso formato di `/update`** — è lo stesso file, letto dalla stessa persona tre settimane dopo:
due grammatiche nello stesso log costringono a leggere due volte e rendono il log non contabile.
`/end` cambia solo la parola dopo l'orario (`session end`) e chiude con `Next session`.

```md
## HH:MM — session end · <titolo: cosa lascia questa sessione> · wt: <worktree> · branch: <branch>
- Done: <risultato verificato, con la prova>
- In progress: <cosa resta a metà, e dove sta>
- Next session: <primo comando da eseguire>
- Blocker: <esatto, oppure none>
- Key context: <decisione e perché · scelta architetturale · scoperta che ribalta una conclusione ·
  errore e regola che ne segue · decisione superata e cosa la supera>
  — tag: #decisione #architettura #scoperta #errore #superata #incidente
- Files: <path · simbolo toccato · perché>
```

`Key context` e `Files` valgono qui più che altrove: la sessione finisce, e quello che non è scritto
adesso non esiste più. `Files` come `path · simbolo · perché` è ciò che permette a Serena e a questo
log di incontrarsi sullo stesso simbolo mesi dopo. SHA e numeri si leggono da `git log`, non si
ricordano.

Then feed the repository memory with the same handoff, one machine-readable line — the offline
distill decides later what is durable, so never skip this because the session felt routine.

**Check the repo owns a journal BEFORE you call `remember` — the binary resolving is not the test:**

```bash
test -d .wiki/journal || echo "NOT memory-wired — skip the remember line"
```

This matters more than it looks. `polmem` may be installed **globally** yet wired to a different
repository: run `remember` in a repo without its own `.wiki/journal/` and it does not fail — it
silently lands in **someone else's** journal, carrying this session out of this repo (observed).
`command -v polmem` passes in exactly that state, which is why the wiring test is the repo's
directory, never the binary.

```bash
polmem remember "session YYYY-MM-DD @<login>" "<shipped/verified, one clause> — next: <first step>"
```

The line is **written to this repo's committed journal** — shared history. Same privacy boundary as
the contract README: no secrets, credentials, customer data or personal information, ever. Failure
branches: no `.wiki/journal/` → skip the line, say once that the repo is not memory-wired, continue
the handoff (tell the repo owner; do **not** wire it yourself); `command not found: polmem` → run the
plugin installer once, then re-check the wiring above. Never run `polmem init` yourself.

### Step 1b — Structured handoff → `$ROOT/team/<login>/handoff/YYYY-MM-DD.md`

The contract's `handoff/` directory is for handoffs RICHER than a checkpoint — write it on every
/end (main worktree, append if the file exists):

```md
# Handoff YYYY-MM-DD HH:MM — @<login>
Repo: <repo> · wt: <worktree name or main> · branch: <branch> · commits: <shas this session>
## Shipped (verified)
## Open threads (with exact state)
## Next session: first command to run
## Risks / do-not-touch
```

This file is committed shared history (Step 5 includes it). The cockpit carries the thin index and
the capped summary; THIS is the structured one a teammate (or you in 3 days) resumes from.

### Step 1c — `## Recent Context` (the session summary, capped at five)

The repo has ONE cockpit, `$CURRENT`, and inside it ONE place for session summaries. `/end` is the
only writer of that section — `/update` never touches it — and it is a ring: five entries, newest
first, exactly the donor's cap. There is no second per-repo cockpit to append to: a dense file that
only grows is the surface that died at 188 KB while everyone kept reading `current.md`.

```bash
RC="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/recent_context.py"
python3 "$RC" "$CURRENT" --entry "### $(date +%F) — <cosa lascia questa sessione, una riga>"
```

Three surfaces, three jobs: `Updated:` carries date and owner, THIS section carries the summary,
the session log carries the full handoff. Exit 2 means the cockpit has no `## Recent Context`
section — add the heading the contract declares (`templates/repo-contract/state/current.md`), never
let the entry land at EOF.

Additionally, if this repo DECLARES a vault and it is not the current root, put the SAME one-line
entry in the vault's own ring, so work done here is visible from there without growing a second
everything-file anywhere:

```bash
VAULT="$(git config --get polaris.vault_root || true)"   # declared per repo, never guessed
[ -n "$VAULT" ] && [ -d "$VAULT" ] && [ "$VAULT" != "$ROOT" ] || VAULT=""
```

```bash
RC="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/recent_context.py"
[ -n "$VAULT" ] && python3 "$RC" "$VAULT/state/current.md" \
  --entry "### $(date +%F) — <repo>: <cosa lascia questa sessione> · branch <branch>"
```

No declaration, or a declared path that is not there → no copy, and this repo's cockpit is the only
record. A literal path used to live here, which meant every install looked for a directory that
exists on one machine and the public package carried a home directory. Set it once per repo:
`git config polaris.vault_root <path>`, the same mechanism `polaris.login` already uses.

Three surfaces carry a session and no fourth exists: the thread line in `current.md` (thin index),
the `## Recent Context` entry (summary, capped), the committed session log (full handoff). The
richer per-session document is `handoff/YYYY-MM-DD.md` from Step 1b, which is committed history.

## Step 2 — Tick the plan

Update the matching row in `team/<login>/weeks/$(date +%G-W%V).md` only when its state or proof
changed. Do not rewrite the plan.

## Step 3 — Capture durable decisions and lessons (WRITE them — a proposal that dies with the session is data loss)

/end WRITES qualifying decisions and lessons directly — append-only, One home, attributed
`(@<login>)` — and lists what it wrote in the closing summary (git history protects; a proposal
that dies with the session protects nothing). Only the genuinely durable qualifies.

**A decision** qualifies only if it either **supersedes a past decision** (name which, and align it)
**or** sets an **architectural direction** whose impact runs from today out to 30 days–years on the
product/development. → `<root>/decisions.md`:

```md
## YYYY-MM-DD — <decision title> (@<login>)
Chose <X> over <Y> because <evidence>. Supersedes: <past decision, or —>. Impact: <area, horizon>.
```

**A lesson** = a real mistake — usually a loop or blocker you overcame — plus the one rule that
prevents its recurrence. → `<root>/lessons.md`.

**ADR — backstop audit (the ADR is born AT DECISION TIME, per the apex rule — not here).**
Sweep this session for qualifying decisions: each must ALREADY have its `docs/adr/NNNN-<slug>.md`.
One missing = a miss to repair NOW, and say so in the closing summary (the rule slipped once —
name it so it doesn't become a habit). Scaffold the missing ADR exactly as the apex rule
prescribes:

1. Resolve every referenced file/symbol with **Serena** (`find_symbol`) — exact paths from the
   tree, never inferred from prose (the 12-wrong-path lesson).
2. Put them in `code_refs:` frontmatter — **symbols (qualified names) are the primary key**
   (`ClassName.method`, module-level names); file paths only as context; **line numbers never**
   (they drift on every edit — false-positive machine). The ADR file's frontmatter IS the store:
   git-versioned, scanner-validated, CI-gated — no service, no separate index. Serena resolves
   symbols live for drift checks (`find_symbol` still exists? signature changed?
   `find_referencing_symbols` for impact).
3. The decisions.md entry gets `→ ADR: docs/adr/NNNN-<slug>.md` appended; the ADR body states
   decision, alternatives weighed, and consequences — content per domain-modeling.
4. Include the ADR file in the Step 5 commit pathspec.

If nothing durable happened, say so. Do not log routine progress as either.

## Step 4 — Prune the live pointer (the only step allowed to close a thread)

Path per the **One home** rule: `$CURRENT` — the handoff lands where the next
session opens. **Reconcile** it: read it first, never blind-overwrite, same rules as `/update` Step 3 (threads keyed
by branch, nothing open lost, other panels' threads and `Next` lines untouched) — with one
difference. **`/end` is the only Team OS command with closing authority**, and it spends it against
ground truth rather than impression.

Prima di potare, **elenca i candidati e decidi a mano quali sono chiusi davvero**. La rimozione
AUTOMATICA è parcheggiata su `polaris-os#268`, ramo `task/T6-prune-parked`: `merge_truth` risponde `None` quando il ref locale
del branch non esiste più, che è il caso NORMALE dopo un merge con `--delete-branch` — un rimotore
così riporterebbe successo senza togliere nulla. Quindi il comando elenca, e la verifica resta tua:

```bash
CL="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/state_close.py"
python3 "$CL" candidates "$CURRENT"
```

Ogni `CANDIDATE=` è un thread che cita una issue o una PR: controllane lo stato su GitHub con i tre
comandi più sotto. Per ognuno **provato mergiato**, e solo per quelli, chiudilo — la chiusura è un
atto esplicito, uno per riga, mai un giro in blocco:

```bash
python3 "$CL" close "$CURRENT" --key "<branch>" --todos "$ROOT/state/todos.md" \
  --owner "$LOGIN" --now "$(date +%F)"
```

Toglie la riga da `## Open`, sposta la sua riga di `state/todos.md` da `## Active` a `## Completed`
con la data di oggi, e riduce `Updated:` a **data e owner**. `Active` non si azzera mai e `Added:`
non si ri-timbra: le altre righe tornano byte-identiche. Una chiave che non nomina un thread solo
esce `2` e non tocca niente — meglio un rerun che la lane sbagliata cancellata. Senza
`state/todos.md` il passo funziona lo stesso e lo dice (`"todo": "skipped"`).

**Closing means REMOVING, not annotating.** A thread proven landed comes **out** of the file; a
`~~struck~~` line that stays is still tokens the next session reads and reconciles. Donor: marvin
`end.md` step 5, `Update State (MANDATORY)` — *«Mark completed items as done or remove them»*,
*«Ensure open threads reflect reality (remove resolved, add new)»*. Same pass:
collapse the state line to **one** `Updated:` — date and login, nothing else: the clause on what
changed belongs to `## Recent Context`, and the full story to the session log. Target after pruning: under 2,000 tokens; `checkpoint.sh verify`
fails on a second `Updated:` line and warns above the size.

### Il censimento del cantiere entra nell'handoff

```bash
CT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
[ -f "$CT" ] || CT="$HOME/.agents/skills/git-power/scripts/cantiere.py"
if [ ! -f "$CT" ]; then
  echo "NOTA: git-power non installato — handoff senza censimento del cantiere"
else
  OUT="$(python3 "$CT" census --tsv --repo "$MAIN_WT" 2>&1)"; CENSUS_RC=$?
  if [ "$CENSUS_RC" = "2" ]; then   # solo "unknown flag": exit 1 significa "c'è da agire"
    echo "NOTA: git-power precede il contratto TSV — censimento in prosa"
    python3 "$CT" census --repo "$MAIN_WT"
  else
    printf '%s\n' "$OUT"
  fi
fi
```

Righe TSV `VERDETTO\tbranch\tpath\tnote`, exit 0 pulito / 1 c'è da agire / 2 errore (contratto
T13, `polaris-os#254`). Copia nell'handoff, verbatim, sotto una riga `**Cantiere**`, ogni riga il
cui verdetto non è `MAIN`: `CLOSABLE` è ciò che si può chiudere, `DIRTY` ciò che ha lavoro non
committato o file ignorati non vuoti. Sono le due cose che chi riprende deve sapere senza rileggere
il grafo. `/end` **non chiude nulla** — elenca, e la chiusura resta un atto esplicito.

`git-power` non viaggia in questo pacchetto: se non si risolve, l'handoff lo **dichiara** e prosegue
senza la sezione cantiere. Il fallback scatta **solo su exit 2**, che è «flag sconosciuto»: exit 1
vuol dire «c'è da agire» ed è un risultato valido, non un errore da ripetere in prosa. Una copia
più vecchia del contratto rifiuta `--tsv` e il fallback stampa la stessa
cosa in prosa italiana, un elemento per riga col verdetto fra parentesi quadre. In entrambi i casi
vale la stessa regola: **leggi i verdetti che il comando stampa**, non quelli che questa riga
ricorda. Il vocabolario è del tool, e questa prosa invecchia prima di lui.

**`state/goals.md` is NOT touched here.** Goals change by explicit decision, never by session
inertia. If it is empty or untouched for more than 30 days, say so in the closing summary and ask
once — do not write it.

**The thread line is the handoff that survives.** A session log committed on a branch is
INVISIBLE to `/start` until that branch merges — for a paused worktree that can be days. So the
thread line in `current.md` must carry the resume-essence on its own, written as if it is the only
survivor (it is): `- \`branch\` — <done in 1 clause; next concrete step; blocker or none> ·
wt: <worktree path if not main> · since YYYY-MM-DD`. Pausing WITHOUT a PR is normal: keep the
worktree alive, record its path in the line, and the next session reopens that same worktree from
`/start` — never feel forced to PR early just to make work visible.

**Branch discipline (`git-power`).** Live GitHub state decides branch fate: an OPEN PR stays in
the handoff; a paused branch without a merged PR stays alive; only `READY_FINALIZE` may close after
the handoff has landed. Session end is not automatically branch end.

**A thread closes only when its work actually landed.** Ask git and the tracker; never infer death
from "nothing moved lately". Work parked on a live branch while its owner spent the week elsewhere
is the normal shape of parallel development — several panels, several worktrees, several branches
open for days — and dropping that thread is precisely the loss this file exists to prevent:

```bash
git worktree list                                        # a worktree still holds the branch → live, stop
git branch --merged origin/main | grep -qx "  <branch>"  # merged into the base?
gh pr list --head "<branch>" --state all --limit 1 --json number,state,mergedAt
```

Close the thread when its branch is **merged** (or its PR reports `MERGED`), and cite that evidence
in the session log you just wrote. Otherwise it stays: an open PR is not a closed thread, a green
real-test is not a merge, "the code is done" is not a merge, and a branch with no recent commits is
parked, not dead. The other exit is **promotion** — a thread that became an issue/plan leaves one
pointer line (`→ #123`), never a silent delete. A thread with no branch closes only against named
evidence in the log.

On a clean handoff the `Next` line is the first step for the next session; leave other panels' `Next`
lines alone. Closed threads leave the pointer — their story lives in the session log you just wrote,
not here.

## Step 5 — Land the handoff in git (same guard as `/update`, in code)

If `git status --short` shows changes, land what you wrote through **the same script `/update` uses**
— pathspec-only, and it commits ONLY from the default branch of the MAIN worktree. A handoff
committed on a feature branch is stranded: invisible to `/start` until that branch merges, which for
a paused worktree is days or never (observed loss). Off the default branch the script defers: the
files stay on disk as the single copy and the next main-tree session lands them — say so, do not
hand-commit around the guard. The Step 1 `polmem remember` line lands in `.wiki/journal/`: it is
committed shared history, so it belongs here or it never reaches the team.

```bash
cd "$MAIN_WT"
SC="${CLAUDE_PLUGIN_ROOT:-}/skills/update/scripts/session_commit.sh"          # plugin install
[ -x "$SC" ] || SC="$HOME/.agents/skills/update/scripts/session_commit.sh"    # skills-CLI install (npx)
"$SC" --end "$ROOT/team/$LOGIN/sessions/<file>" "$ROOT/team/$LOGIN/handoff/$(date +%F).md" \
            "$ROOT/team/$LOGIN/weeks/<file>" "$ROOT/decisions.md" "$ROOT/lessons.md" \
            ".wiki/journal/<file-from-step-1>"   # ONLY the files you wrote this session
```

`--end` is the mode that may commit `decisions.md` / `lessons.md` (they are this command's vetted
promotion); it still refuses `state/current.md` and `.env*`, and never pushes. On a **deferred** run
say plainly that the handoff is on disk and not yet committed — the dense copy in the cockpit is what
the next panel resumes from meanwhile. If a later `git checkout <default>` in that tree is refused
because of the deferred file, git is protecting the append: copy aside, switch, re-append, re-run. **Both resolver
candidates missing** (say which you tried): on the default branch only, `git add --` those exact
paths and `git commit -m "chore(polaris): session handoff $(date +%F) @$LOGIN"` — never `git add -A`;
on any other branch commit nothing and report the handoff as deferred on disk.

Never commit or push without an explicit request. After committing, if the branch is ahead of its
remote, remind the contributor there is unpushed work:

```bash
git status -sb | head -1   # e.g. "## main...origin/main [ahead 1]"
```

## Finish

After the handoff commit, close only the current lane when it is already remote-merged:

```bash
GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
python3 "$GP" phase post-push --repo "$PWD"
# only after READY_FINALIZE:
python3 "$GP" phase finalize --repo "$PWD" --confirm "$PWD"
```

`finalize` preserves dirty/divergent main and removes only the current clean merged feature
worktree plus its exact branch ref.

Summarize the handoff in three bullets (shipped, open, next). This command never writes outside the
current repository and never mutates the tracker.
