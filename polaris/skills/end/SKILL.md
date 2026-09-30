---
name: end
description: Polaris skill — close a repository-first team session with a handoff, decisions/lessons written to the ledgers, a plan tick and a pathspec-only commit. Trigger when stopping work, before a multi-day pause, or on "wrap up / end session / /end".
user-invocable: true
version: 1.23.0
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

Il log vive e si committa dove gira il pannello; il cockpit vive nel worktree principale. Session
log, handoff file, plan tick e append a decisions/lessons stanno sotto `$ROOT`, che è il contratto
di QUESTO worktree, e atterrano sul branch su cui la sessione è davvero avvenuta. Solo `$CURRENT`
— il cockpit, gitignored — resta a casa unica nel worktree principale, perché una copia per
worktree è una copia che nessun merge riporta indietro. La provenienza sta nell'header del blocco
(`wt:`/`branch:`).

```bash
eval "$("${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/resume_paths.sh")"
```

One resolver, shared with `/start`: `MAIN_WT`, `ROOT` (this worktree), `LOGIN`, `CURRENT` (the main worktree's cockpit) and `RADAR`. It exits
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
   # classificazione prima dell'handoff
   LP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/lane_phase.sh"
   [ -f "$LP" ] || LP="$HOME/.agents/skills/end/scripts/lane_phase.sh"
   bash "$LP" "$PWD"
   ```

   `KEEP` means the worktree stays in the handoff. `READY_FINALIZE` means it may close only after
   the handoff commit. Unknown or unverifiable PR state is never cleanup permission. The script
   holds the two guards this question needs: a repo with **no remote** was never pushed, so it says
   so and stops (asking anyway answered «push presente ma nessuna PR verificabile», a refusal that
   reads like a broken branch), and a machine without `git-power` degrades in one line.
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

### I sei campi sono i cinque elementi del confine — nessuno è opzionale

Le sei righe non sono un formato gradito: sono i **cinque elementi** che rendono la sessione
ripartibile, e la sessione dopo apre da qui. Un campo senza contenuto si scrive `none`, esplicito;
un campo **assente** è il confine rotto, e `/end` non chiude.

| elemento | campo |
|---|---|
| scope e decisioni | `Key context` |
| stato dei task e prossimo task | `In progress` + `Next session` |
| file cambiati e stato del working tree | `Files` |
| comandi di verifica lanciati ed esito | `Done` |
| domande, rischi e approvazioni aperte | `Blocker` |

**Fail-closed su una decisione presa e non scritta.** Una clausola di `Key context` taggata
`#decisione` o `#superata` deve **nominare la casa che la porta**, in una di queste tre forme:

- l'id del record — `DEC-…` o `ADR-…` — e il record deve esistere sotto `decisions/`;
- il titolo della voce di `decisions.md` (Step 3), che la clausola ripete per esteso;
- l'issue nella forma **qualificata**: `issue:<repo>#<numero>`, per esempio `issue:acme-api#407`.
  Il numero nudo (`#407`, «vedi PR #424») **non** conta: è la cosa più comune che finisca in una
  riga `Key context`, e prenderlo per una casa assolveva ogni decisione non scritta.

Una ritrattazione è una decisione come le altre — un numero ritirato si scrive **accanto al
numero**, non solo qui. Se la clausola non nomina nulla, si scrive prima (Step 3) e solo dopo si
chiude: una decisione che vive solo in questo log è la decisione che la sessione dopo prende di
nuovo, o rovescia senza sapere che esisteva.

Dove il repo porta il gate del backbone, la stessa cosa è una verifica eseguibile e non un
promemoria — altrimenti le sei righe sopra restano la checklist:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" close \
  --root "$ROOT" --handoff "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" || exit 1
```

Chiude **la sessione che `/start` ha aperto in questo checkout**: il sid non si passa e non si
inventa — è checkout + giorno + login, ricalcolato qui (polaris-os#155). Il motore è quello del
repo, se lo porta, altrimenti quello del vault dichiarato (`git config polaris.vault`), la stessa
ricerca che fa il pack del brief.

Chiude **la sessione aperta**, non il sid di oggi: a mezzanotte la derivazione cambia mentre la
sessione è ancora aperta, e un pannello può non aver mai fatto `/start`. `SESSION: none open —
nothing to close` esce 0 e `/end` prosegue: la cosa durevole è il commit dell'handoff, e una
ricevuta già scritta non viene mai riscritta.

**Il `|| exit 1` vale solo per i rifiuti.** Prima questo blocco era un `if [ -f "$GATE" ]` su un
path solo-host, e con una catena `&&` … `||` OGNI rifiuto — anche `ID_COLLISION` — cadeva nel ramo
`||` stampando «nessun gate» con `$?` a `0`: la skill proseguiva al commit dello Step 5 proprio nei
casi che il gate esiste per fermare. Ora l'assenza del motore esce 0 stampando la nota, e il
`|| exit 1` intercetta soltanto i rifiuti veri.

Sette rifiuti, tutti prima della ricevuta — ma solo **con una sessione aperta**: senza, il motore
non gira e restano i due che il log si guadagna da solo, che la porta controlla per prima
(`HANDOFF_MISSING`, `HANDOFF_UNREADABLE`, exit 1). Gli altri cinque — decisione non scritta, id già
speso, albero altrui — non hanno una sessione contro cui girare: valgono comunque come regola, e
quello che scoprono va in una issue, non in un rifiuto che non esiste.
I sette: `HANDOFF_MISSING` se non gli si passa il log e
`HANDOFF_UNREADABLE` se il path non è leggibile (i cinque elementi si leggono, non si inventano),
`HANDOFF_INCOMPLETE` nomina l'elemento mancante, `DECISION_UNWRITTEN` la clausola che non nomina la
sua casa, `ID_COLLISION` un id di Decision già speso altrove, `TREE_NOT_OURS` un path sporco che
nessuna riga `Files` dichiara e `TREE_UNREADABLE` un albero che `git` non riesce a leggere (un
committer per tree), `SESSION_UNKNOWN` un sid che non ha una `start.json`.
Le lezioni escono come righe `LESSON_PROPOSAL` su stderr: sono **proposte**, e
lo Step 3 decide quali qualificano e le scrive. Il gate non tocca `lessons.md` da solo.

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
section — add the heading the contract declares (`skills/start/templates/repo-contract/state/current.md`), never
let the entry land at EOF.

Additionally, if this repo DECLARES a vault and it is not the current root, put the SAME one-line
entry in the vault's own ring, so work done here is visible from there without growing a second
everything-file anywhere:

```bash
VAULT="$(python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/start/scripts/session_gate.py" \
  vault --root "$ROOT")"                                 # declared per repo, never guessed
[ -n "$VAULT" ] && [ "$VAULT" != "$ROOT" ] || VAULT=""
```

```bash
RC="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/recent_context.py"
[ -n "$VAULT" ] && python3 "$RC" "$VAULT/state/current.md" \
  --entry "### $(date +%F) — <repo>: <cosa lascia questa sessione> · branch <branch>"
```

No declaration, or a declared path that is not there → no copy, and this repo's cockpit is the only
record. A literal path used to live here, which meant every install looked for a directory that
exists on one machine and the public package carried a home directory. Set it once per repo:
`git config polaris.vault <path>`, the same mechanism `polaris.login` already uses — **one key**,
the one `/start`, `/init` and the doctor already read. `polaris.vault-root` was a second spelling
of the same fact and is still read for one cycle, with a deprecation note on stderr naming the
key that replaces it.

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
Sweep this session for qualifying decisions: each must ALREADY have its record in the house the
repository declares — the `decision:` row of the `outputs:` map in its contract (`_polaris/config.yml`,
else `./config.yml` when the repository root is itself the contract root). Without a map, look where
that repository already keeps its durable choices, and name that location in the closing summary.
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
3. The decisions.md entry gets `→ ADR: <the declared house>/<record>` appended; the record states
   decision, alternatives weighed, and consequences — content per domain-modeling.
4. Include the ADR file in the Step 5 commit pathspec.

If nothing durable happened, say so. Do not log routine progress as either.

## Step 4 — Prune the live pointer (the only step allowed to close a thread)

Path per the **One home** rule: `$CURRENT` — the handoff lands where the next
session opens. **Reconcile** it: read it first, never blind-overwrite, same rules as `/update` Step 3 (threads keyed
by branch, nothing open lost, other panels' threads and `Next` lines untouched) — with one
difference. **`/end` is the only Team OS command with closing authority**, and it spends it against
ground truth rather than impression.

La potatura è **automatica e provata**, non più a mano. Il rimotore chiede due fonti e pretende che
concordino: il **tracker** (`gh pr view N` dice `MERGED`, oppure `gh issue view N` dice `CLOSED` per
`COMPLETED`) e il **repo** (la head di quella PR, o il suo merge commit, è antenata del default
branch QUI). Prima si guarda, in sola lettura:

```bash
# read-only: nessuna riga esce da `## Open`, si guardano i verdetti
PT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/prune_threads.py"
[ -f "$PT" ] || PT="$HOME/.agents/skills/end/scripts/prune_threads.py"
python3 "$PT" "$CURRENT" --owner "$LOGIN" --now "$(date +%F)"
```

A thread closes only when **every** citation it carries is settled: a lane reading «closes #77,
then #79» with #79 still open stays. Five verdicts. `PROVEN` really landed. `DEAD` is abandoned
work — a PR closed without merge, an issue closed as not planned — and closes the lane too, logged
as `DEAD`, never as completed; a `DEAD` citation next to an `OPEN` one keeps the lane (measured
2026-09-30: 15 of 38 lanes in a product cockpit were dead and `/end` closed none). `AMBIGUOUS` is
merged where this checkout cannot see it, **or** a branch carrying commits past the merged head:
that lane is alive again. `OPEN` is a PR still open. `BLOCKED` is a tracker that does not answer
(no `gh`, an error, a rate limit, an empty answer): **one `BLOCKED` stops the whole run** and exits
`2`, because a prune that removes four lanes and silently skips one is the old silent no-op,
inverted. Then apply:

```bash
PT="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/prune_threads.py"
[ -f "$PT" ] || PT="$HOME/.agents/skills/end/scripts/prune_threads.py"
python3 "$PT" "$CURRENT" --apply --owner "$LOGIN" --now "$(date +%F)" \
  --log "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" \
  --todos "$ROOT/state/todos.md"
```

Ogni `PROVEN` esce da `## Open`, la sua riga di `state/todos.md` passa da `## Active` a `##
Completed` con la data di oggi, `Updated:` si riduce a **data e owner**, e il thread **con il suo
verdetto** viene appeso al session log: il thread non sparisce, si sposta, e il log resta
append-only. `Active` non si azzera mai e `Added:` non si ri-timbra: le altre righe tornano
byte-identiche. `state/todos.md` **non è obbligatorio** nel contratto: se non c'è, il passo funziona
lo stesso e lo dice (`"todo": "skipped"`). Chiudere significa togliere la **lane intera** — la riga e
ciò che le sta sotto, figli indentati e blocco fence compresi: una riga orfana sotto `## Open` è
lavoro che la sessione dopo deve riconciliare.

The run also prints `STALE=` for every lane that cites nothing and is older than 14 days: no
verdict can close it, so **each one is resolved in this `/end`** — open an issue for it (then it has
a citation), or close it by hand below with the reason in the session log. Reading `0 PROVEN` and
moving on is how a cockpit reached 38 lanes. The manual close takes the lane id, or `#N` for the
one lane citing #N; a missing `state/todos.md` is skipped, as the contract allows:

```bash
CL="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/state_close.py"
python3 "$CL" close "$CURRENT" --key "<branch>" --todos "$ROOT/state/todos.md" \
  --owner "$LOGIN" --now "$(date +%F)"
```

Una chiave che non nomina un thread solo esce `2` e non tocca niente — meglio un rerun che la lane
sbagliata cancellata.

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
cui verdetto non è MAIN — CLOSABLE è ciò che si può chiudere, DIRTY ciò che ha lavoro non
committato o file ignorati non vuoti. Sono le due cose che chi riprende deve sapere senza rileggere
il grafo. `/end` **non chiude nulla** — elenca, e la chiusura resta un atto esplicito.

`git-power` non viaggia in questo pacchetto, e i **tre** siti che lo chiamano lo risolvono allo
stesso modo: catena `$CLAUDE_PLUGIN_ROOT` → `$HOME/.agents`, `[ -f ]`, e una riga di degrado
dichiarata. Senza quel guard un `/end` a metà si spezzava con un errore Python grezzo su una
macchina senza `git-power`. Il fallback scatta **solo su exit 2**, che è «flag sconosciuto»: exit 1
vuol dire «c'è da agire» ed è un risultato valido, non un errore da ripetere in prosa. Una copia
più vecchia del contratto rifiuta `--tsv` e il fallback stampa la stessa
cosa in prosa italiana, un elemento per riga col verdetto fra parentesi quadre. In entrambi i casi
vale la stessa regola: **leggi i verdetti che il comando stampa**, non quelli che questa riga
ricorda. Il vocabolario è del tool, e questa prosa invecchia prima di lui.

### Le PR aperte del pannello — una riga di ragione ciascuna

Chi apre una PR la porta al merge. Una PR lasciata aperta a fine sessione non è neutra: va in
conflitto con la lane dopo, e diverse PR aperte insieme sullo stesso manifest fanno pagare il conto
tutto in una volta. Quindi `/end` le **elenca** e dice quali portano già la loro ragione nel
cockpit:

```bash
CK="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/checkpoint.sh"
[ -f "$CK" ] || CK="$HOME/.agents/skills/update/scripts/checkpoint.sh"
bash "$CK" open-prs
```

`OPEN_PR=#N <branch> — ragione: MANCA` è la riga che ti riguarda: scrivi **una riga** in `$CURRENT`
che dica perché quella PR resta aperta — un atto del founder, una credenziale che non hai, una CI
ancora da leggere — e citala col suo `#N`, che è la chiave con cui il giro dopo la ritrova.
`PRESENTE` significa che il cockpit la nomina già e non c'è niente da scrivere. `OPEN_PRS=unknown`
è `gh` che non ha risposto: elencale a mano e vai avanti lo stesso.

**Questo passo non rifiuta mai** (decisione founder, 2026-09-06): è un promemoria, non un muro. Un
gate che blocca la chiusura di sessione è un gate che si aggira, e una sessione chiusa male perde
l'handoff, non solo la lista delle PR. Il comando esce `0` in ogni ramo, PR aperte senza ragione
comprese.

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

## Step 4b — Reconcile `## Active Priorities` (the only writer of the order)

The cockpit is the one view the founder reads, and `/start` reads only it — so the order of the
work lives here and **this step is its only writer**. Every `/end`, after Step 4, rebuild the
ordered list from four inputs: `state/goals.md` (where we are going), the `## Active` rows of
`state/todos.md`, the `## Open` threads that survived Step 4, and what this session changed.
Rules: each line is `#<issue or lane> — <outcome in one line>`; the first line is the next thing
to do. An item leaves **only** when Step 4 closed it as `PROVEN` — an `OPEN` or `AMBIGUOUS` lane
stays in the order, and if Step 4 stopped on `BLOCKED`, do not rewrite the order this session.
Keep it to **7** lines by folding the tail into one last line (`… — also: #A, #B, #C`), never by
dropping a live item in silence. If the order did not change, write it anyway —
the stamp records that it was reviewed today, and `/start` names an order older than 7 days.

The heredoc is QUOTED (`<<'ORDER'`) on purpose: lane ids carry backticks, and inside double
quotes the shell would run them and write a corrupted order with exit 0.

Never edit the section by hand or by string surgery: on 2026-09-13 an unanchored `s.index` matched
a backtick mention of the heading and fused it into a sentence, and the order stayed wrong for ten
days. The script finds the real heading, writes atomically under the cockpit lock, and adds the
section before `## Open` when it is missing:

```bash
PR="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/state_priorities.py"
[ -f "$PR" ] || PR="$HOME/.agents/skills/update/scripts/state_priorities.py"
[ -f "$PR" ] || { echo "STOP: state_priorities.py not resolved — never hand-edit the order"; exit 1; }
python3 "$PR" set "$CURRENT" <<'ORDER'
#N — first
#M — second
ORDER
```

## Step 5 — Land the handoff in git (same guard as `/update`, in code)

Land what you wrote through **the same script `/update` uses** — pathspec-only, never `git add -A`,
and never a push. Il log di sessione si committa sul branch corrente, sempre; due eccezioni
dichiarate (HEAD staccato, policy `no-direct-default` sul default branch). Un repo senza alcun
commit non è un'eccezione: il primo handoff atterra come tutti gli altri.

Un `/end` che rinvia invece di committare è un `/end` che non ha lavorato (decisione founder,
2026-09-04). Terzo esito dichiarato, sempre exit 2: un path che git rifiuta (ignorato, o dentro un
repo annidato) viene nominato con la sua ragione e gli altri path atterrano comunque — un handoff
non muore perché il journal sta in una directory ignorata.
Nelle eccezioni lo script esce 2 con una riga che dice quale: i file restano dove
li hai scritti, non vengono copiati altrove, e tu lo dici in chiaro invece di riportare successo.
The Step 1 `polmem remember` line lands in `.wiki/journal/`: it is committed shared history, so it
belongs here or it never reaches the team.

```bash
cd "$(git rev-parse --show-toplevel)"   # the panel's own worktree, never another one
SC="${CLAUDE_PLUGIN_ROOT:-}/skills/update/scripts/session_commit.sh"          # plugin install
[ -x "$SC" ] || SC="$HOME/.agents/skills/update/scripts/session_commit.sh"    # skills-CLI install (npx)
"$SC" --end "$ROOT/team/$LOGIN/sessions/$(date +%F)-@$LOGIN.md" \
            "$ROOT/team/$LOGIN/handoff/$(date +%F).md" \
            "$ROOT/team/$LOGIN/weeks/$(date +%G-W%V).md" \
            "$ROOT/decisions.md" "$ROOT/lessons.md"   # add the journal file if Step 1 wrote one
```

`--end` is the mode that may commit `decisions.md` / `lessons.md` (they are this command's vetted
promotion); it still refuses `state/current.md` and `.env*`, and never pushes. On one of the three
declared exceptions (exit 2) say plainly which one it was and that the handoff is still in the
working tree, uncommitted — never report a clean close. **Both resolver candidates missing**
(say which you tried): `git add --` those exact paths and
`git commit -m "chore(polaris): session handoff $(date +%F) @$LOGIN"` — never `git add -A`.

I path si nominano tutti: quelli che non esistono vengono **scartati prima** dell'`add`, perché
`git add -- esistente assente` non stage NIENTE ed esce 128 — un piano settimanale mai aperto
faceva atterrare l'intero handoff da nessuna parte. E se un hook rifiuta il commit lo script esce 1,
riporta la riga dell'hook e ripulisce l'indice dei soli path Polaris: lasciarli staged significa che
il commit dopo, senza pathspec, si porta via l'handoff. Mai `--no-verify`.

Then read the ground truth back, because a skill that reports success on a dirty tree is the failure
this step exists to close:

```bash
git status --short   # 0 righe sui path Polaris, o dì esattamente quale è rimasta e perché
```

Never commit or push without an explicit request. After committing, if the branch is ahead of its
remote, remind the contributor there is unpushed work:

```bash
git status -sb | head -1   # e.g. "## main...origin/main [ahead 1]"
```

## Finish

After the handoff commit, close only the current lane when it is already remote-merged:

```bash
LP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/end/scripts/lane_phase.sh"
[ -f "$LP" ] || LP="$HOME/.agents/skills/end/scripts/lane_phase.sh"
bash "$LP" "$PWD"
# only after READY_FINALIZE — and only where the lane phase could actually be read:
GP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] || GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] && python3 "$GP" phase finalize --repo "$PWD" --confirm "$PWD"
```

`finalize` preserves dirty/divergent main and removes only the current clean merged feature
worktree plus its exact branch ref.

Summarize the handoff in three bullets (shipped, open, next). This command never writes outside the
current repository and never mutates the tracker.
