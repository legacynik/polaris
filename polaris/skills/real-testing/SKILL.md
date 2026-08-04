---
name: real-testing
description: Il gate adversariale prima di dire "fatto" — unit test verdi non sono la prova che una cosa funziona. Deriva il perimetro da testare dal codice realmente toccato con serena-code-graph (simboli cambiati, chi li chiama, contratti al bordo), poi esegue le prove su staging/reale — API, browser, DB, trace — coprendo OGNI ramo nuovo, non il primo che passa. Usala prima di ogni merge/deploy, dopo una fix, quando un playbook di test del repo va verificato contro il codice attuale, o quando ti chiedono "è testato davvero / real test / verifica che funzioni". Vale per ogni repo: il metodo è uno, la specificità la deriva il grafo.
user-invocable: true
model: sonnet
version: 1.0.0
---

# Real Testing Skill

## Regola

**Unit test VERDI ≠ Funziona. VERIFICA SEMPRE manualmente.**

---

## 0. Playbook verticali del repo — controlla PRIMA di usare il checklist generico

Prima di improvvisare, cerca `_project_specs/testing-protocol/INDEX.md` (o convenzione equivalente) nella root del repo corrente. Se esiste: **è la fonte primaria**, non uno dei tanti — descrive i moduli verticali reali del prodotto (generazione/onboarding/edit/ecc.), con tenant/fixture/comandi esatti e i gate specifici di quel modulo. Il checklist generico sotto resta il fallback per repo senza un protocollo scritto, o per coprire quello che il protocollo verticale non menziona esplicitamente.

**Prima di seguire QUALSIASI playbook (generico o verticale), verifica col code-graph che descriva ancora la realtà**: `find_symbol` sui file/funzioni che il playbook nomina (**serena-code-graph**, LSP-live: risponde sul codice di adesso, non su un indice ricostruito ieri). Un doc scritto un mese fa può descrivere un call-chain che nel frattempo è cambiato. Usa il doc come mappa, verifica i nomi contro il grafo prima di eseguire i comandi. Se il grafo diverge dal doc, il doc è stale — segnalalo invece di eseguire un playbook che punta a codice che non esiste più.

## 0b. Il perimetro da testare si DERIVA dal codice toccato, non si indovina

Questa skill è una sola per tutti i repo, e resta tale: ciò che cambia da repo a repo non è il metodo ma **quali contratti tocchi**, e quello lo dice il grafo — per-cambiamento, non per-repo. Un playbook verticale scritto a mano invecchia; il grafo no.

### Primo: stabilisci COSA stai testando e portalo su disco

Serena risponde **su ciò che è sul disco in questo momento**. Se il codice sotto test non è in checkout, ogni risposta riguarda un altro codice — e non te lo dice: ottieni un perimetro plausibile, completo, e della cosa sbagliata. È il modo più facile di dichiarare un real-test verde su qualcosa che non hai testato.

Quindi prima di tutto, dichiara la **base** e la **testa**, e verifica di averle:

| stai testando | base..testa | come lo metti su disco |
|---|---|---|
| il tuo lavoro locale | `origin/main..HEAD` | ci sei già |
| **la PR di qualcun altro** | `origin/main...pr/<n>` | `gh pr checkout <n>` — **in un worktree separato**, mai nel tuo albero |
| cosa gira su staging | `<sha deployato>..origin/main` | leggi lo SHA dal deploy, non dalla memoria |
| una release / un batch | `<tag precedente>..<tag>` | checkout del tag |
| un hotfix su prod | `<sha prod>..<branch fix>` | worktree dal fix |

Per una PR altrui, tre cose che non sono opzionali:

```bash
gh pr view <n> --json headRefName,headRepositoryOwner,mergeable,files
git worktree add ../.rt-pr<n> && cd ../.rt-pr<n> && gh pr checkout <n>   # isolato: non tocchi il tuo lavoro
```

1. **In un worktree separato.** Testare la PR di un altro nel tuo albero ti fa perdere il lavoro in corso e mescola i due cambiamenti nel diff — cioè nel perimetro.
2. **Poi `activate_project` su QUELLA directory**, o Serena continua a risolvere sul tuo albero. Se salti questo passo, tutto il resto è sbagliato in silenzio.
3. **La base è il merge-base, non `main` di oggi**: `git merge-base origin/main HEAD`. Con `..` semplice ti prendi anche i commit di main che la PR non ha, e ti inventi un perimetro che non è suo.

Casi che vanno detti invece di aggirati: una PR **da un fork** può non essere risolvibile localmente senza fetch del remoto — dichiaralo, non testare a metà. Una PR **con conflitti** (`mergeable: CONFLICTING`) non è testabile come sarà dopo il merge: il real-test vale per lo stato attuale, e va scritto così.

E se stai testando il lavoro di qualcun altro, ricorda cosa **non** puoi derivare dal grafo: perché l'ha fatto e cosa considerava fatto. Quello sta nella issue e nella descrizione della PR — leggile, perché i criteri di accettazione sono suoi, non tuoi.

### Poi: deriva il perimetro

Da `git diff --name-only <base>...<testa>` ricava i **simboli** cambiati, poi con serena-code-graph:

1. **`find_symbol`** su ogni simbolo toccato → firma attuale, tipi, file reale. È anche il controllo che stai testando la cosa giusta.
2. **`find_referencing_symbols`** su ognuno → **chi lo chiama**. Ogni chiamante è un percorso che il tuo cambiamento può rompere anche se il suo file non compare nel diff: sono i test che nessuno pensa a fare, e il posto da cui esce la maggior parte delle regressioni.
3. **I contratti sul bordo** — endpoint/route, schema o modello di risposta, migrazione DB, evento emesso, tool o funzione esposta a un agente, firma pubblica di un modulo. Quando il diff tocca uno di questi, **il contratto è la cosa da testare**, non l'implementazione interna: chi lo consuma non vede il tuo refactor, vede la forma che gli arriva.
4. **Dichiara il perimetro PRIMA di testare**, in questa forma — così è verificabile invece che affermato:

```
Perimetro derivato (serena):
  simboli toccati:  pricing_v4.py::_resolve_tier1, schemas.py::QuoteOut
  chiamanti:        3 (generate.py::run, api/quote.py::post_quote, tasks/batch.py::replay)
  contratti al bordo: POST /v1/quote (response QuoteOut), migrazione 041
  → prove necessarie: <una riga per contratto e per chiamante>
```

**Due segnali che il grafo sta rispondendo sul codice sbagliato** — entrambi vogliono dire "fermati", non "prosegui con quello che ho":

- `find_symbol` **non trova un simbolo che il diff dice aggiunto** → non sei sul codice sotto test (checkout mancante, o `activate_project` puntato altrove).
- `find_referencing_symbols` restituisce **zero chiamanti per un simbolo non nuovo** → quasi sempre un errore di risoluzione, non un fatto.

Entrambi producono un perimetro vuoto o parziale, e un gate verde a vuoto. Verifica prima su quale directory Serena è attiva.

Il perimetro derivato **si somma** al playbook verticale del repo, non lo sostituisce: il playbook sa cose che il grafo non può sapere (quale tenant usare, quale fixture è realistica, quale latenza è accettabile). Il grafo sa cosa hai rotto. Servono entrambi.

**Completezza, non happy-path**: un loop/agente autonomo che esegue questo skill non è "finito" solo perché un comando ha girato senza errori — deve coprire esplicitamente ogni ramo/edge-case che il modulo/playbook elenca (non solo il primo che passa), e riportare per ognuno pass/fail, non un verdetto aggregato tipo "sembra ok". Se un playbook verticale elenca N verifiche, un real-test che ne copre N-1 e dichiara successo è un gate INCOMPLETO — vale la stessa regola "real-test = adversariale, mai happy-path" a prescindere dal repo.

**Langfuse (se il progetto ne usa uno)**: se il repo ha una configurazione Langfuse (variabili `LANGFUSE_*`, un client SDK importato, o una skill `langfuse` locale), il real-test include SEMPRE una verifica trace — non solo curl/browser/DB. Trace atomica (parent + figli, zero orfani), nessun errore/warning nella finestra della chiamata testata, tag/versione coerenti col deploy testato. Non limitarti a quello: è UNA delle superfici da controllare (insieme a API/browser/DB/log), non un sostituto delle altre.

---

## Dopo ogni feature

### Backend/API
```bash
# 1. Avvia l'app
# 2. Chiama l'endpoint realmente
curl -X POST http://localhost:3000/api/users -d '{"email":"test@test.com"}'

# 3. Verifica DB
psql -c "SELECT * FROM users WHERE email='test@test.com'"

# 4. Controlla i log
tail -f logs/app.log
```

### Frontend/UI
```
# 1. Apri il browser
# 2. Naviga alla feature
# 3. Screenshot o Playwright MCP per verificare
# 4. Testa edge cases (form vuoto, errori, loading)
```

### DB Migration
```bash
# 1. Applica migration
# 2. Verifica schema
\d table_name

# 3. Testa rollback
```

---

## Checklist Pre-Merge

- [ ] App avviata e testata manualmente
- [ ] Endpoint chiamati con curl/Postman
- [ ] Dati verificati in DB
- [ ] UI verificata visivamente (screenshot se possibile)
- [ ] Edge cases testati (errori, vuoti, limiti)
- [ ] Log controllati per errori/warning

---

## Real-testing su STAGING dopo OGNI deploy (obbligatorio)

**curl NON basta. Apri il BROWSER vero (Playwright).** curl colpisce il backend
giusto, ma il frontend deployato puo' essere buildato/wirato male: un solo errore
di build e l'utente vede "Failed to fetch" mentre curl dice 200. Solo una sessione
browser reale becca i bug di frontend/build/wiring.

### 1. Smoke API end-to-end (prima di dire "fatto")
```bash
SMOKE_EMAIL=... SMOKE_PASSWORD=... scripts/smoke-staging.sh
# login -> onboard create+fetch -> dossier PDF -> screening, contro staging live
```

### 2. Browser reale (Playwright MCP) - il passo che mancava sempre
```
mcp__plugin_playwright_playwright__browser_navigate  -> dashboard
browser_fill_form + browser_click                    -> login + submit feature
browser_network_requests                             -> le chiamate vanno a /api (200)?
browser_console_messages (level=error)               -> errori?
```
Verifica che le chiamate vadano a **same-origin /api**, NON a `localhost:8001`.

### 3. I 3 gotcha di deploy che nascondono i bug (incidente 2026-06-17)
- **Migration NON auto-applicate ad Aurora** (solo nova-db locale al primo boot).
  Dopo deploy: applica le migration pending + verifica che le colonne esistano,
  altrimenti 500 (`column ... does not exist`).
- **Frontend buildato con `.env.local`** (`VITE_API_URL=http://localhost:8001/api`):
  Vite lo prioritizza su `.env`. Builda con **`VITE_API_URL=/api`** (sposta via
  `.env.local`), poi deploy in `/var/www/dashboard-staging`. Caddy proxa `/api/*`
  same-origin.
- **Verifica nel browser** che login + la feature funzionino davvero, non solo l'API.

Sequenza corretta deploy: **migrate Aurora -> deploy(app) -> build+deploy frontend(/api) -> smoke API -> smoke BROWSER.**

---

## Raccolto — il real-test NON è finito finché non ha lasciato un test in CI

Uno sweep manuale è conoscenza che evapora: la prossima persona (o il prossimo te
fra tre giorni) ripete lo stesso lavoro, o non lo ripete e la regressione passa.
**L'artefatto del real-test non è il verdetto, è il test che resta.**

Il perimetro derivato al punto 0b serve due volte: la prima dice cosa provare a
mano, la seconda dice **cosa CI non sta proteggendo**. Chiudendo, classifica ogni
cosa emersa e agisci di conseguenza:

| Cosa hai trovato | Cosa lasci in CI |
|---|---|
| **Difetto reale** | Test che lo **riproduce**, scritto PRIMA del fix e visto fallire. Senza il rosso non sai se testa il difetto o l'implementazione. |
| **Combinazione non testata** (due cambi corretti separatamente, mai insieme) | Test della combinazione. È il buco più frequente quando due PR toccano lo stesso file: ogni lato ha i suoi test verdi. |
| **Invariante verificato a mano che nessun unit test può cogliere** (una sola fonte per un concetto, nessuna scorciatoia che bypassa il resolver, nessun URL hardcoded) | **Test strutturale**: scandisci i sorgenti e asserisci la proprietà. Un unit test non lo becca perché ogni copia duplicata passa i propri test. |
| **Falso allarme** | Nessun test — ma scrivi perché sembrava un difetto, o lo riscopri identico fra un mese. |
| **Tetto non correggibile** (serve una credenziale, dipende dalle intenzioni di chi builda) | Nessun test: va in un ADR come rischio residuo accettato. Un rischio scritto è governato, uno taciuto no. |

**Chi dice quali chiamanti coprire**: `find_referencing_symbols` sui simboli
toccati. I chiamanti che il diff non nomina sono esattamente quelli che nessuno
pensa a testare — ed è da lì che escono le regressioni. Se il grafo non risolve
il linguaggio del cambiamento (capita: un progetto rilevato mono-linguaggio,
un path ignorato), **dillo e usa un sostituto enumerabile** — in TS/JS gli import
sono espliciti, quindi i call-site si contano con certezza — ma dichiara la
sostituzione invece di spacciarla per grafo.

**Ogni test scritto così va visto FALLIRE su una violazione fabbricata apposta**,
non solo passare. Un enforcer che non hai mai visto rosso non sai se funziona.
E attento al falso positivo speculare: un test strutturale che matcha **testo**
scatta anche sui commenti, e un guard che si accende sulla prosa insegna alla
gente a ignorarlo. Se scandisci i sorgenti, spoglia i commenti e asserisci
sull'uso reale. Aggiungi sempre un'asserzione che la scansione **ha trovato
qualcosa**, o il giorno che si rompe la camminata sull'albero il test diventa
verde a vuoto.

## Perché

L'AI scrive test che confermano cosa il codice FA, non cosa DOVREBBE fare.
Test verdi + feature rotta = succede spesso. E curl-verde + dashboard-rotta pure
(incidente onboarding 2026-06-17: backend 202, browser "Failed to fetch").

**Trova i bug tu col browser, non l'utente.**
