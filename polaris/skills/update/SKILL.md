---
name: update
description: Polaris skill — record a short repository-first checkpoint during an active session. Trigger after meaningful progress, a blocker, a context switch, or on "checkpoint / save progress / /update".
user-invocable: true
model: sonnet
version: 2.15.0
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
cockpit, never this panel's. Use `$CURRENT` verbatim: **Resolve it from the MAIN worktree, always**
— a cwd-relative `state/current.md` written from a worktree is gitignored there and never comes
back. Un secondo cockpit dentro un worktree è una casa che **nobody will ever read**.

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

Non leggere lo scratch a mano: su una macchina multi-panel quel file è **condiviso**, e il primo
harvest della giornata partiva da riga 0 — 146 righe lette, quasi tutte flusso di altri pannelli
(`polaris-os#89`). Il comando taglia per te:

```bash
"$CHECKPOINT" harvest-slice "$POLARIS_SID"    # o l'id di questa sessione, se non è in ambiente
```

Emette **tutte** le righe che portano il tuo session id, ovunque stiano nel file, più la testa del
delta fino al tetto (`HARVEST_CAP`, 40 di default). Il tetto è sul prefisso altrui, mai sulla
posizione: un tetto posizionale butterebbe proprio la tua riga arrivata per ultima. Ciò che trovi
diventa `Key context`. Poi `"$CHECKPOINT" harvest-done` sposta il watermark: si sposta comunque,
harvestato o no, altrimenti ogni run successivo ripropone gli stessi byte.

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

## `$CURRENT` — lo stato si sovrascrive, thread compresi

**Se nulla di materiale è cambiato, non scrivere affatto.** Materiale = un thread aperto, un item
completato, una priorità cambiata, un blocker nuovo. Il donor upstream (marvin `update.md`, step 4)
vale come regola: *«Only update what's relevant to the current work. Don't rewrite the whole file.»*

Se è cambiato: **la riga del thread si AGGIORNA, non se ne aggiunge una seconda.** Founder,
2026-09-03: *«Non è che dentro current fa un'altra riga, ma va semplicemente ad aggiornare l'update
precedente. Invece all'interno della session mette sempre un'altra riga.»* Il session log è il
ledger e cresce; il cockpit è **stato** e si sovrascrive — anche se la riga precedente l'ha scritta
un altro pannello o un altro giorno. Il costo in token non è il cancello: dieci lane vive vanno
bene, una riga vecchia no.

**Reconcile, never blind-overwrite**: si legge il file com'è e si posa UNA riga per chiave, senza
toccare le lane degli altri pannelli. Non farlo a mano:

```bash
UP="$ROOT/scripts/state_upsert.py"
[ -f "$UP" ] || UP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/state_upsert.py"
[ -f "$UP" ] || { echo "STOP: state_upsert non risolto — non scrivere la riga a mano"; exit 1; }
printf '%s\n' "- \`<branch>\` (<repo>) — <stato in una riga> · since <YYYY-MM-DD>" \
  | python3 "$UP" thread "$CURRENT" --owner "$LOGIN" --now "$(date +%F)"
```

**Il `(<repo>)` non è decorativo**: il cockpit è cross-repo, e — dove `the branch is a thread's
identity` — l'identità completa è la coppia `(branch, repo)`. Un thread senza repo non è «mio», è **non verificabile**, e `/end` non lo chiude
mai — meglio una riga che resta di una lane viva cancellata perché un altro repo aveva un branch
con lo stesso nome.

Sostituisce la riga con la stessa chiave, altrimenti la accoda, e riscrive l'unica riga
`Updated:` con data e owner. Ogni altro byte torna identico: la lane di un altro pannello è
sua — `never overwrite it with yours`. **Nothing open is ever lost.**

**Never trim a live thread to make the file smaller.** Una riga che sembra vecchia non è
`stale?` finché non lo provi: una lane parcheggiata su un branch vivo è lavoro normale, e quella
riga `may be the only copy of a handoff` che il session log, committato su un branch non mergiato,
non consegna a nessuno. Se non è tua, `not yours to remove` — e anche se lo è, a toglierla è
`/end` contro la verità di git, non `/update` per fare spazio. Il repo ospite non ha bisogno degli script del vault: il pacchetto ne spedisce una copia. Se
nemmeno quella si risolve, **fermati e dillo** — non scrivere la riga a mano: appenderla è
esattamente il difetto che questo passo esiste per chiudere.

Le prime righe del file sono le **priorità attive** (`## Active Priorities`): l'ordine del lavoro,
non un archivio. I thread stanno sotto `## Open`, uno per riga, ed è lì che l'upsert posa la sua. La riga
`Updated:` porta **data e owner**, nient'altro: il riassunto della sessione sta in
`## Recent Context` (lo scrive `/end`) e l'handoff completo nel session log. `verify` legge il
CONTENUTO di quella riga, non la data del file: un `touch` a vuoto non è un checkpoint.

**`/update` has no closing authority**, never closes anything, and only `/end` may remove a
thread — aggiunge e segnala; `/end` resta
l'unico che chiude un thread, sposta una riga in `Completed` o scrive in `Recent Context`. Il log
della giornata sta in `team/<login>/sessions/`, e cresce sempre: quello è il ledger.

## Il todo della settimana segue il thread

Se il checkpoint fa avanzare un item che sta in `## Active` di `state/todos.md`, aggiorna **quella
riga**, non ne aggiungere una seconda:

```bash
printf '%s\n' "| #<issue> — <stato in una riga> | | <context> |" \
  | python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/update/scripts/state_upsert.py" \
      week "$ROOT/state/todos.md" --week "W$(date +%V)" --no-add
```

Il file è nella forma donor a **tabelle**, e la seconda cella è `Added`: si porta dietro quella
originale perché il timbro dice **da quante settimane** una cosa non si fa — ri-timbrarlo fa
sembrare nuovo del lavoro fermo da tre settimane. `--no-add` non è decorativo: **`/update` aggiorna
il TESTO di una riga che il thread cita e non ne crea nessuna**; `plan-week` riconcilia la sezione,
`/end` sposta in `Completed`. Chiave sconosciuta → exit 2, e non scrive. Nessun `state/todos.md`
nella repo: nessun passo, zero rumore.

## Landing

Prima del checkpoint, chiudi il lavoro della lane: assegna ogni path dirty a un owner; per i path
propri usa staging esatto, `git-power commit-check` e un Lore commit. Un path foreign o unknown
blocca `/update`; non fare `git add -A`, stash o commit per conto di un altro panel.

```bash
GP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] || GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] || { echo "NOTA: git-power non installato — landing senza commit-check, si prosegue"; GP=""; }
git add -- <exact-owned-paths>
python3 "$GP" commit-check --repo "$PWD"
# split/receipt on exit 3, then Lore commit; finally require:
python3 "$GP" phase checkpoint --repo "$PWD"

"$CHECKPOINT" commit    # pathspec-only, mai -A, mai .env*, mai state/current.md
"$CHECKPOINT" verify "<titolo della entry appena scritta>"   # lega il cockpit a QUESTA run
```

`verify` esiste perché un passo che vive solo nella prosa prima o poi viene saltato — anche da chi
l'ha scritto. **Passagli il titolo** della entry: senza, il gate sa solo che il cockpit porta oggi e
il tuo nome; con, sa che l'ultima voce del log è la tua, e un cockpit ri-datato a mano senza
checkpoint non passa. Il titolo non entra in `Updated:` — sta nel log e in `Recent Context`. Una entry che non raggiunge un
ref è una entry che non esiste (misurato: 46% delle entry recenti di un repo, e 74 file di journal
non committati sulle 4 repo al 2026-08-08).

Il log di sessione si committa sul branch corrente, sempre; due eccezioni dichiarate (HEAD
staccato, policy `no-direct-default` sul default branch). In quelle due `commit` esce 2 con una riga
che dice quale, i file restano dove li hai scritti e non vengono copiati altrove: `/update` è
fallito e non emette la riga di completamento. Terzo esito dichiarato, sempre exit 2: un path che
git rifiuta (ignorato, o dentro un repo annidato) viene nominato con la sua ragione e **gli altri
path atterrano comunque**. Un repo senza alcun commit non è un'eccezione: il primo checkpoint
atterra come tutti gli altri. Il log vive e si committa dove gira il pannello; il cockpit vive nel
worktree principale.

Dopo il landing, prova che anche il worktree principale è clean. `/update` non censisce e non
rimuove worktree, ma non può terminare dirty:

```bash
GP="${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}/skills/git-power/scripts/cantiere.py"
[ -f "$GP" ] || GP="$HOME/.agents/skills/git-power/scripts/cantiere.py"
MAIN_WT="$(git worktree list --porcelain | sed -n '1s/^worktree //p')"
[ -f "$GP" ] && python3 "$GP" phase checkpoint --repo "$MAIN_WT" \
  || echo "NOTA: git-power non installato — resta `git status --short` come prova di pulizia"
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
