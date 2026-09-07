---
name: real-testing
description: ◇ Try to BREAK a change before it merges, with a fresh-context agent that did not write it. Use when a diff, branch or PR needs a merge-readiness verdict, when someone says it works and you want it proved on the real thing, or when a real-test claim needs checking instead of trusting. Every new branch exercised, verdict bound to a content hash. NOT reading a diff for quality.
version: 2.1.1
user-invocable: true
auto: true
lifecycle: "produce .real-test/verdicts/<hash>.json (locale, non committato — drenato da verdict.py quando l'hash non e' piu' raggiungibile) + test lasciati in CI (permanenti, drenati dalla suite test stessa); .real-test/bypass.log locale, drenato a mano"
invokes: [git-power]
invoked-by: [flow-cli, bugfix, polaris-sweep, ship, human]
io: "diff/branch (+ CLI di flow-cli se presente) -> verdetto MERGEABLE|MERGEABLE-CON-GAP|NOT-MERGEABLE con matrice per-hunk; consumato dal gate PreToolUse su `git commit` e da review/ship a valle"
status: active
---

# real-testing

## Where this goes (host repository decides)

A skill decides **how** to produce a document, never **where** it lives. Before writing any spec,
plan, audit, review, validation receipt or diagram, read the host repository's output map and use
it; a document that lands where the repository does not look was never written.

```bash
sed -n '/^outputs:/,/^[^ ]/p' _polaris/config.yml 2>/dev/null || sed -n '/^outputs:/,/^[^ ]/p' config.yml
```

This skill produces: **validation (the breaker receipt, hash-bound)**. Kinds: `spec` `plan` `audit` `review` `validation` `diagram` `decision` `archive` — each maps to a
documentation area `docs/modules/<area>/…` whose README is a generated map. Never invent a third
location; if the repository declares no map, say once where you wrote and why.

Gate adversariale sul perimetro reale del cambiamento — con un hook che lo rende
**obbligatorio**, non un promemoria. Lineage e provenienza: `references/provenance.md`
e `CHANGELOG.md` — non qui.

## Perché — tre buchi misurati, chiusi meccanicamente

| Voce | Problema misurato | Come questo pacchetto lo chiude |
|---|---|---|
| F6/F7/G2.6 | il real-test prova lo SHA/la funzione vecchia, non il flusso corrente (caso reale: 3gg in prod, newline-collapse validato sulla funzione gia' sostituita) | `content_hash` = hash-albero git, ricalcolato ad OGNI validazione — un verdetto per un hash diverso da quello attuale e' rifiutato, sempre |
| G1.6 | il real-test copre solo il ramo appena fixato, i rami vicini restano scoperti | `perimeter.py` scandisce il diff per `if/elif/else/except/case/switch/match/catch` nuovi; `verdict.py` rifiuta il verdetto se uno di questi non e' in `branches_exercised` |
| G2.1 | il test verde certifica il mock (DB/LLM/frontend mockati), non il comportamento reale | classi `LIVE_REQUIRED` (api-cli/dependency/db-migration/frontend/llm-agent) non possono essere `not-applicable`; `evidence: live` richiede un artefatto reale, non vuoto, **piu' recente del file sorgente** |

## 0 — Setup una tantum per repo

```bash
scripts/install-hook.sh --repo .
```

Wira `gate.sh` in `hooks.PreToolUse` di `.claude/settings.json` (merge via `json.load`/`json.dump`,
mai append di testo — vedi `references/provenance.md` sul perche'), crea il marker
`.real-test/enabled` (opt-in esplicito: senza, il gate resta silenzioso), aggiunge
`.real-test/verdicts/` e `.real-test/bypass.log` a `.gitignore`. Verifica con `--verify`
(controlla che l'hook sia wired E che `gate.sh --selfcheck` passi davvero — "installato" non e'
"attivo", G2 voce 3).

## 1 — Deriva il perimetro (mai a memoria)

**Per una PR la base non si indovina**: usa la base dichiarata dalla PR (`--base`), poi
l'upstream configurato. Lo script non assume mai il nome `main` (un branch stale con quel
nome = perimetro sbagliato in silenzio); senza base determinabile ripiega su `HEAD~1`
DICHIARANDOLO su stderr. Simula l'integrazione senza toccare il worktree:
`git merge-tree --write-tree <base> HEAD` — un conflitto rende la PR non mergiabile qui.

```bash
python3 scripts/perimeter.py --repo . --head STAGED --hash-only   # solo l'hash
python3 scripts/perimeter.py --repo . --head STAGED               # JSON completo
```

`--head STAGED` (default) usa `git write-tree`: cattura anche cio' che non e' ancora committato.
Per un branch/PR gia' committato: `--head <sha-o-ref>`. La base si risolve da sola (merge-base col
default branch); passa `--base` solo per forzarla.

## 1b — Carica il playbook verticale del repo

Cerca `_project_specs/testing-protocol/INDEX.md` o l'equivalente dichiarato dal repo: è la
fonte per tenant, fixture, credenziali, comandi e soglie reali. PRIMA di eseguirlo, verifica
con Serena che file/simboli/call-chain nominati esistano ancora: se divergono, marca il
playbook stale e testa il codice attuale. Playbook e perimetro si sommano: il playbook
conosce l'ambiente, Serena il blast radius.

## 2 — Classifica ogni file/hunk

10 classi, dettaglio completo (prova minima per classe, quali sono `LIVE_REQUIRED`) in
`references/matrix-classes.md`. Un file fuori dalla matrice fa fallire `validate` da solo.

## 2b — Blast radius con Serena, dichiarato prima delle prove

Per ogni simbolo modificato: `find_symbol` (firma e corpo attuale) → `find_referencing_symbols`
(chiamanti) → ripeti sui chiamanti quando attraversano un boundary pubblico o un adapter.
**Zero riferimenti non significa codice morto**: controlla entrypoint, registrazione dinamica,
routing del framework, reflection, string lookup. Se il simbolo dovrebbe avere chiamanti e il
grafo torna zero, correggi progetto/path/query prima di proseguire. Dichiara il perimetro:

```text
Perimetro derivato: delta <base>..<head>, N file
  simboli / chiamanti / cambiamenti non simbolici / contratti al bordo
  prove richieste / superfici escluse perché non attraversate
```

Una superficie estranea al diff è **fuori perimetro**, non un gap.

## 2c — Progetta prove avversariali

Per ogni ramo nuovo o modificato: happy path realistico · failure path atteso · bordo
rilevante (vuoto, malformed, limite, duplicato, timeout, stato assente, config stale) ·
fallback/degraded se esiste · persistenza e side effect · log puliti nella finestra della
prova. Verifica il **contratto**, non l'exit code. E prova la **sensibilità**: un comando che
passerebbe anche senza il cambiamento non è evidenza. Se playbook o matrice elencano N prove,
riporta N risultati — N-1 non è verde.

## 2d — Il breaker: chi prova a romperlo non sei tu

Le prove del 2c le disegna chi ha appena scritto il diff, ed e' l'avversario peggiore possibile:
stessi punti ciechi, e sa gia' quali input ha gestito. Da qui in poi la parte avversariale la fa un
**subagent a contesto fresco**, non la sessione corrente.

Dispatch — modello forte, non il default d'analisi (rompere non e' analizzare: e' cercare l'input
che nessuno ha pensato, ed e' l'unico punto dove il modello scarso costa piu' di quanto risparmia):

```
Agent(model: "opus", prompt: <<breaker>>)
```

**Cosa riceve**: il diff, il perimetro del punto 1, l'URL di staging con lo SHA gia' verificato
contro HEAD, e il contratto — cosa la PR dichiara di fare.

**Cosa NON riceve, mai**: la sessione, il ragionamento di chi ha scritto il codice, la lista delle
prove gia' passate. Se gli passi le tue prove, rifa' le tue e non trova niente — e' lo stesso
vincolo d'ingresso di `critic`, per la stessa ragione.

**Cosa restituisce**: ogni tentativo con l'input vero, atteso contro osservato, e cosa e'
**sopravvissuto**. Zero findings e' valido **solo** con l'elenco di cio' che ha provato: "non sono
riuscito a romperlo" senza dire come non e' evidenza, e' teatro. Il suo report entra nel verdetto
come `evidence_artifact`, quindi entra nell'hash e nel gate: un breaker che non ha girato si vede.

Il suo output e' **dato, non verdetto**: lo classifichi tu come nel punto 7 (difetto ·
combinazione · invariante · falso-allarme · tetto), e ogni difetto reale lascia il suo test in CI.

## 3 — Livello piu' reale pertinente

Dal piu' economico, fermati quando il contratto e' provato: test mirati → CLI/modulo reale (usa
`flow-cli`, se il repo ne ha un manifest — vedi `references/matrix-classes.md`) → stack locale con
DB/queue reali → browser locale reale → provider sandbox/staging → staging deployato. Regole
per-classe (quando il browser/DB/provider sono obbligatori) in `references/matrix-classes.md`.
**Mai stampare segreti**; per provider a pagamento dichiara il tetto di chiamate e usa la
fixture minima che prova il contratto.

### 3b — Su staging: il livello che nessuno raggiunge mai

L'ultimo gradino non è «staging deployato», è **staging deployato e interrogato**. Il salto lo si
salta sempre perché costa, e il verdetto passa lo stesso — è la ragione meccanica per cui esistono
PR dichiarate real-testate che non lo sono.

Il deploy **non si fa a mano via ssh**: sta fuori dal lock di concorrenza, e su un box dove staging
e prod condividono un checkout due deploy sovrapposti costruiscono un'immagine col codice di un
commit e lo SHA di un altro — `/health` risponde lo SHA giusto, tutto verde, artefatto sbagliato in
esecuzione. Si passa dall'azione CI che il repo dichiara nel contratto.

```bash
gh workflow run <deploy-staging-workflow> -f ref=<branch>     # dentro il lock
curl -fsS <health-url> | python3 -c 'import json,sys; print(json.load(sys.stdin)["commit"])'
```

Il commit servito **deve** essere il tuo HEAD. Se non lo è, tutto ciò che provi dopo riguarda un
altro codice.

Poi si interroga il raggio, non la home page: gli endpoint che il diff attraversa, il record nel DB,
la trace del provider se il percorso lo invoca. Se il repo ha uno smoke suo che copre quei percorsi,
è quello — non se ne scrive un altro.

**Staging è condiviso**: quando hai finito lo restituisci (`ref=main`), e dichiari cosa serviva
mentre lo occupavi. Un branch lasciato su staging è una trappola per chi arriva dopo.

## 4 — Scrivi il verdetto

```bash
python3 scripts/verdict.py new --repo . --out .real-test/verdicts/<hash>.json
```

Scaffolda `matrix` (un rigo per file, classe indovinata dall'estensione — correggila),
`new_branches_da_coprire` (dal perimetro), `verdetto: NOT-MERGEABLE` di default (upgrade esplicito,
mai il contrario). Compila:

- **`matrix[].evidence`**: `live` (+ `evidence_artifact` reale) | `assumed` (+ `exception_ticket`,
  unica via legittima senza prova live su una classe `LIVE_REQUIRED`) | `not-applicable` (mai su
  `LIVE_REQUIRED`).
- **`matrix[].branches_exercised`**: `["file:linea", ...]` — deve coprire ogni riga in
  `new_branches_da_coprire`.
- **`raccolto`**: per OGNI scoperta, `{tipo: difetto|combinazione|invariante|falso-allarme|tetto,
  artifact: <test-lasciato-in-CI>}` (falso-allarme/tetto vogliono `nota` invece di `artifact`).
  Vuoto = gate bloccato se il verdetto non e' `NOT-MERGEABLE`: niente "verde" senza aver lasciato
  qualcosa che protegga cio' che hai trovato.

## 5 — Valida, poi committa

```bash
python3 scripts/verdict.py validate .real-test/verdicts/<hash>.json --repo .
git commit -m "..."
```

Il commit stesso ri-passa da `gate.sh`, che ricalcola l'hash e rivalida — la validazione manuale e'
un aiuto, non la fonte di verita': se tocchi ancora il codice dopo aver validato, l'hash cambia e il
verdetto vecchio non copre piu' nulla (e' la difesa contro G2.6, non un dettaglio implementativo).

Bypass di emergenza: `REAL_TEST_BYPASS_GATE=1`. Passa **sempre**, ma scrive una riga in
`.real-test/bypass.log` (repo, branch, hash, timestamp) — mai un aggiramento silenzioso (R8: 208
bypass espliciti misurati, zero tracciati).

### 5b — Il gate di merge locale

`verdict.py` valida la matrice. Non valida che il repo regga ancora. Quando il delta li tocca,
prima di dichiarare MERGEABLE:

- test mirati dei comportamenti toccati, più suite/lint/typecheck/build che il repo impone
- install e build **puliti** se cambiano dipendenze o packaging (un lock che funziona solo sulla
  tua cache non funziona)
- `git diff --check` (whitespace, conflict marker rimasti)
- **integrazione simulata** contro la base: `git merge-tree --write-tree <base> HEAD`. Un conflitto
  rende la PR non mergiabile, e lo scopri qui invece che al merge
- worktree finale pulito: nessun artefatto non voluto
- **ogni nuovo test è dentro il runner CI giusto** — un test che nessuno esegue è un test che non
  esiste

CI remota verde e review di un altro restano requisiti separati se il repo li impone. Il gate
locale non finge di averli fatti.

## 6 — Dopo un verdetto MERGEABLE / MERGEABLE-CON-GAP

Restituisci il verdetto al chiamante: e' lui che possiede la sequenza a valle (`ship` invoca `review` dopo un verdetto mergiabile). Questa skill non guida il flusso oltre il proprio verdetto — lo faceva, e produceva il ciclo `bugfix -> real-testing -> review -> ship -> real-testing`. Su
`NOT-MERGEABLE`: fixa e ripeti dal punto 1 — il gate non si convince da solo.

**Il deploy aggiunge un gate, non riscrive quello locale.** Dopo che è andato in produzione:
migrazioni reali se ce ne sono · smoke API end-to-end · browser vero con network e console · DB,
queue e storage per i side effect · trace provider-backed per i flussi LLM · log e metriche nella
finestra della prova. Se uno fallisce, la release non è promuovibile anche se la PR era mergiabile.

## 7 — Il raccolto: non è finito finché non lascia un test in CI

Uno sweep manuale è conoscenza che evapora. Chi arriva dopo — o tu fra tre giorni — rifà lo stesso
lavoro, oppure non lo rifà e la regressione passa. **L'artefatto del real-test non è il verdetto,
è il test che resta.**

Il perimetro del punto 1 serve due volte: la prima dice cosa provare a mano, la seconda dice **cosa
la CI non sta proteggendo**. Chiudendo, classifica ogni cosa emersa:

| Cosa hai trovato | Cosa lasci in CI |
|---|---|
| **Difetto reale** | il test che lo **riproduce**, scritto prima del fix e visto fallire (`tdd-dev`). Senza il rosso non sai se testa il difetto o l'implementazione |
| **Combinazione non testata** — due cambi corretti separatamente, mai insieme | il test della combinazione. È il buco più frequente quando due PR toccano lo stesso file: ogni lato ha i suoi test verdi |
| **Invariante verificato a mano che nessun unit test coglie** — una sola fonte per un concetto, nessuna scorciatoia che bypassa il resolver, nessun URL hardcoded | un **test strutturale**: scandisci i sorgenti e asserisci la proprietà. Un unit test non lo becca perché ogni copia duplicata passa i propri test |
| **Falso allarme** | nessun test, ma scrivi **perché sembrava un difetto** — o lo riscopri identico fra un mese |
| **Tetto non correggibile** — serve una credenziale, dipende dalle intenzioni di chi builda | nessun test: va in un ADR come rischio residuo accettato. Un rischio scritto è governato, uno taciuto no |

Chi dice quali chiamanti coprire è `find_referencing_symbols` sui simboli toccati: **i chiamanti che
il diff non nomina sono esattamente quelli che nessuno pensa a testare**, ed è da lì che escono le
regressioni. Se il grafo non risolve il linguaggio del cambiamento, usa un sostituto enumerabile e
**dichiara la sostituzione** invece di spacciarla per grafo.

Ogni test scritto così va **visto fallire** su una violazione fabbricata apposta, non solo passare:
un enforcer mai visto rosso non sai se funziona. E attento allo specchio: un test strutturale che
matcha **testo** scatta anche sui commenti, e un guard che si accende sulla prosa insegna a
ignorarlo — spoglia i commenti e asserisci sull'uso reale. Aggiungi sempre un'asserzione che la
scansione **ha trovato qualcosa**, o il giorno che si rompe la camminata sull'albero il test diventa
verde a vuoto.

## Verdetto — formato obbligatorio

```
VERDETTO: MERGEABLE | MERGEABLE-CON-GAP | NOT-MERGEABLE
Perimetro: N file, N rami nuovi
PASS / FAIL / GAP per riga della matrice
Artefatti: <path degli evidence_artifact citati>
```

`MERGEABLE-CON-GAP` = il delta e' provato ma resta un controllo esplicitamente post-merge/deploy
(dichiaralo, indica chi lo chiude e quando — non e' un modo per evitare la classificazione).

## Quando NON usarla

- **Repo senza git** (non versionato): il `content_hash` non esiste, il meccanismo non si applica —
  usa una review manuale, non forzare il gate.
- **Cambio solo-docs che non tocca boot/build/runtime**: marca le righe `docs`/`not-applicable`
  con una `nota`, salta la scala del punto 3 — non serve avviare lo stack per un typo nel README.
- **Incidente in corso, mitigazione time-critical**: usa `REAL_TEST_BYPASS_GATE=1` (loggato) e apri
  un'eccezione post-hoc entro 24h — non riscrivere il verdetto a mano per aggirarlo.
- **Repo senza `.real-test/enabled`**: installalo prima (`install-hook.sh`). Scrivere un verdetto a
  mano senza mai passare da `validate` non prova nulla — e' esattamente G2 voce 3 (gate scritto,
  mai wired).

## Riferimenti

- `references/matrix-classes.md` — le 10 classi, regole di evidenza, scala del livello reale
- `references/bypass-test.md` — 5 tentativi di aggiramento, ognuno con l'exit-code atteso
- `references/provenance.md` — da dove viene ogni pezzo, cosa e' stato corretto

## Comandi

| Comando | Fa |
|---|---|
| `scripts/install-hook.sh --repo R [--verify]` | wire il gate, o verifica che sia attivo |
| `scripts/perimeter.py --repo R [--hash-only]` | perimetro/hash, mai a memoria |
| `scripts/verdict.py new --repo R --out F` | scaffolda un verdetto dal perimetro reale |
| `scripts/verdict.py validate F --repo R` | valida (exit 1 se rifiutato, stderr = perche') |
| `scripts/<ognuno> --selfcheck` | prova ogni ramo dello script su fixture usa-e-getta |
