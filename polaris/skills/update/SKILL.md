---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Trigger after meaningful progress, a blocker, a context switch, or on "checkpoint / save progress / /update".
user-invocable: true
model: sonnet
version: 2.6.0
invokes: [git-power]
---

# /update — leave the work legible

```bash
"${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/checkpoint.sh" prepare
```

Root, login, branch, worktree, session-log path, **`CURRENT` (the cockpit)**, harvest offset and the
hygiene sweep all come from that command. If it fails, read its message and stop — never guess a
path. `prepare` resolves `CURRENT` through `$ROOT/scripts/state_home.py path` when the repo carries
it and applies the identical rule inline when it does not; either way it is the MAIN worktree's
cockpit, never this panel's. Use `$CURRENT` verbatim — a cwd-relative `state/current.md` written
from a worktree is gitignored there and never comes back.

## The entry

```md
## HH:MM — <titolo: cosa è successo> · wt: <worktree> · branch: <branch>
- Done: <verificato, con la prova>
- In progress: <cosa è a metà, così chi riprende sa dove sta>
- Next: <un passo concreto>
- Blocker: <esatto, oppure none>
- Key context: <la decisione presa e perché · la scelta architetturale · la scoperta che ribalta
  una conclusione · l'errore e la regola che ne segue · la decisione superata e cosa la supera>
  — tag: #decisione #architettura #scoperta #errore #superata #incidente
- Files: <path · simbolo toccato (funzione/classe) · perché>
```

**Il titolo porta la entry.** "checkpoint" non dice nulla; `#1010 chiuso end-to-end: prod deployato`
dice tutto prima ancora dei bullet.

**`In progress` non è riempitivo**: lavoro al 50% senza una riga è lavoro che riparte da zero.

**`Key context` è il campo che conta** — è l'unico posto dove finisce ciò che non è avanzamento:
perché è stata presa una decisione, cosa si è scoperto che ribalta una conclusione precedente,
**quale errore hai fatto e che regola ne discende**. I tag lo rendono contabile su mesi di log: i
pattern si trovano contando, e si conta solo ciò che ha una forma.

Quando il founder ti corregge, quella correzione è la riga più preziosa della sessione e **tu sei
il suo unico testimone** — lo scratchpad conserva le tue risposte finite, non le strade sbagliate.
Scrivila prima che sparisca, con: cosa credevi, cosa era vero, cosa lo prova, la regola che resta.

**`Files` è un indice inverso sul codice, non un elenco.** Il campo esisteva nel design originale e
si è perso nella prosa. Scritto come `path · simbolo · perché` diventa la cosa più utile del log:
da un file si risale alla sessione, alla decisione e al motivo. Il **simbolo** (funzione, classe,
metodo) lo dai perché Serena naviga per simbolo, non per riga — così mesi dopo un
`find_referencing_symbols` e questo log si incontrano sullo stesso nome, e sai *quando* e *perché*
quel simbolo è cambiato. Un path nudo obbliga a rileggere il diff; `path · simbolo · perché` no.

Una scelta architetturale che qualifica (supera una decisione precedente o fissa una direzione con
impatto 30gg+) non si esaurisce qui: `Key context` la registra e la propone come **ADR**, che è
l'unico posto dove vive legata al codice.

Tre righe vuote sono legittime (`Blocker: none`, `Key context:` assente su una sessione tranquilla).
Un `Key context` inventato per sembrare produttivi è peggio di nessun `Key context`.

**Gli SHA, i conteggi e i numeri si VERIFICANO, non si ricordano.** `git log`, non memoria: in un test
A/B su una sessione reale entrambe le versioni hanno scritto lo stesso SHA sbagliato, ricordandolo
invece di leggerlo. Un numero errato in un log è peggio di un numero assente — verrà creduto.

**Un numero da solo non è informazione: dagli il suo confronto e il suo "quindi".** "79 cloni" non
dice nulla; "79 cloni ma solo 4 view → traffico quasi certamente automatico, non persone" è una
conclusione su cui si decide. Stessa regola per i limiti: se una cosa non è reversibile, o un dato
non è verificabile, scrivilo — è la parte che tra tre settimane evita di ri-derivare tutto.

## Harvest del delta

`prepare` ha stampato `HARVEST_FROM`. Leggi lo scratch **solo da quell'offset** — mai tutto il file.
Ciò che trovi diventa `Key context`. Poi `"$CHECKPOINT" harvest-done` sposta il watermark: si sposta
comunque, harvestato o no, altrimenti ogni run successivo ripropone gli stessi byte.

## Lessons e decisioni: scrivi nell'archivio, proponi per l'apex

Due superfici, due regole opposte — e la distinzione è la ragione per cui il sistema regge:

- **Archivio** (`lessons.md`, `decisions.md`): **scrivi sempre**, append-only, newest on top. È
  storico, non viene mai caricato in contesto: il rumore lì costa nulla, una lezione persa costa
  tanto. Una lezione che aspetta un'approvazione è una lezione che muore col contesto.
- **Apex** (`CLAUDE.md`, `rules/*.md`): **mai** da qui. Ogni riga dell'apex si paga in ogni
  sessione di ogni repo — ci arriva solo via `pol-apex-curate`, che propone e lascia scrivere
  all'umano. Se una lezione merita l'apex, dillo in una riga di chiusura; non promuoverla tu.
- **ADR**: una scelta architetturale che qualifica va proposta come ADR, non sepolta in
  `decisions.md` — è l'unico posto dove vive legata al codice e viene segnalata quando il codice
  cambia sotto di lei.

`/end` applica le stesse tre regole e usa lo stesso formato di entry: un log con due grammatiche si
legge due volte e non si conta.

## Plan tick — owed only when the weekly plan exists

If `prepare` resolved a `team/<login>/weeks/<current-week>.md`, record the checkpoint's progress
on it: one line under the outcome it advanced (or its blocker), dated. Then pass it as the second
argument to `commit` so plan and log land together. No weekly file = no step, no noise. `verify`
fails when the file exists but predates today's session log. Plans are the roadmap (founder,
polaris-os#85): a plan nobody ticks is a wish, not a plan.

## `$CURRENT` — la riga di stato si sovrascrive, i thread si aggiungono

**Se nulla di materiale è cambiato, non scrivere affatto.** Materiale = un thread aperto, un item
completato, una priorità cambiata, un blocker nuovo. Un checkpoint che riscrive lo stato senza
motivo è rumore. Il donor upstream (marvin `update.md`, step 4) è più preciso e vale come regola:
*«Only update what's relevant to the current work. Don't rewrite the whole file.»* — un checkpoint
tocca la riga del lavoro che ha in mano, non riscrive il file intero.

Se è cambiato: `$CURRENT` (nel MAIN worktree, regola One home) ha **due metà con regole opposte**,
e confonderle è il difetto. La riga `Updated:` è **stato**: una sola, sovrascritta con data e titolo
del checkpoint — mai una seconda. Gli `## Open` sono un **ledger**: aggiungi o barra **con data e
prova**, mai chiudere o riscrivere la riga di un altro owner — si flagga. `/end` è l'unico che chiude.

Il vecchio titolo di questa sezione diceva «add and flag» sopra *tutto* il file, e la prosa sotto
diceva «sovrascrivi» solo sulla riga di stato: il testo si contraddiceva. Misurato il 2026-08-31,
con la regola già scritta qui: **13 righe `Updated:` impilate in un repo, 5 in un altro**, 1 sola
dove un umano aveva potato a mano. Perciò `verify` ora gatea il **conteggio**, non solo l'mtime —
una regola senza cancello è un desiderio.

## Landing

Prima del checkpoint, chiudi il lavoro della lane: assegna ogni path dirty a un owner; per i path
propri usa staging esatto, `git-power commit-check` e un Lore commit. Un path foreign o unknown
blocca `/update`; non fare `git add -A`, stash o commit per conto di un altro panel.

```bash
GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
git add -- <exact-owned-paths>
python3 "$GP" commit-check --repo "$PWD"
# split/receipt on exit 3, then Lore commit; finally require:
python3 "$GP" phase checkpoint --repo "$PWD"

"$CHECKPOINT" commit    # pathspec-only, mai -A, mai .env*, mai state/current.md
"$CHECKPOINT" verify    # fallisce rumorosamente se un passo è stato saltato
```

`verify` esiste perché un passo che vive solo nella prosa prima o poi viene saltato — anche da chi
l'ha scritto. Se `commit` rinvia, `/update` è fallito e non emette la riga di completamento: la entry è su disco, non in git.
Una entry che non raggiunge un ref è una entry che non esiste (misurato: 46% delle entry recenti di
un repo, e 74 file di journal non committati sulle 4 repo al 2026-08-08).

Su repo con `main` protetto da status check, il commit di journal **non passa dal branch di lavoro**:
scrive nel worktree agganciato a main che `prepare` risolve. Il diario non deve superare i cancelli
del codice.

Dopo il landing, prova che anche il worktree principale è clean. `/update` non censisce e non
rimuove worktree, ma non può terminare dirty:

```bash
GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
MAIN_WT="$(git worktree list --porcelain | sed -n '1s/^worktree //p')"
python3 "$GP" phase checkpoint --repo "$MAIN_WT"
```

`BLOCKED_DIRTY` è un fallimento, mai un warning. `/update` è completo solo quando entrambi i
checkpoint riportano `CLEAN` e `git status --short` è vuoto.

## Output

Una riga: `Checkpointed: <cosa>`. Niente riassunto, niente elenco di next action — sono già nella
entry (donor marvin `update.md`: *«No summary. No next actions list. Just confirm the save»*). Il
checkpoint costa quanto lo stato che rilegge: tenuto `current.md` sotto i 2.000 token, resta sotto
il migliaio end-to-end.

## Mai

Creare issue, branch, PR o deployment · dichiarare completo senza prova linkata · toccare
il `$CURRENT` di un altro panel · scrivere un `state/current.md` dentro un worktree · `git add -A`.
