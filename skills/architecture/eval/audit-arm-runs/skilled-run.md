Report emesso. Nessun file toccato nel repo target (gli script del censimento stanno in `/tmp/arch-audit/`).

---

# Audit arm — `the product repo` / `backend/app/services/`

## Step 0 — reversibilità (prima di ogni consiglio)

**`OWNED`** — passano tutte e tre.

| | Verifica | Esito |
|---|---|---|
| (a) insieme dei chiamanti chiuso | grep su tutto il vault per `app.services`: l'unica altra directory che importa è `prev_wt_oracle`, che `git worktree list` conferma essere un **worktree dello stesso repo**, non un secondo consumatore | ✅ chiuso |
| (b) tutti i chiamanti in un repo che puoi pushare | uno solo: `acme/acme-api` | ✅ |
| (c) atterrano insieme senza terze parti | solo founder; i consumatori HTTP (frontend Vercel, expo mobile) stanno dietro `app/api`, non sulla superficie Python — **nessun reperto qui sotto tocca una firma di rotta** | ✅ |

Conseguenza (tabella `SKILL.md`): si ottimizza per **profondità**, superficie più piccola vince, un seam si costruisce solo a **due** adattatori.

**Costo che non cambia il verdetto ma pesa sul rimedio:** 32 worktree/branch vivi. Una cancellazione di 465 righe nel file più caldo del backend confligge con ogni branch che tocca `generator.py`. Va fatta per prima, o subito dopo la merge dell'onda corrente.

## `perimetro`

`backend/app/**` @ `4f2eb5b1` (branch `main`) — 301 moduli Python, 18.070 statement. Di cui `backend/app/services/` = **125 moduli, 8.396 statement (46% del backend)**.

**Non esaminati** (non "a posto" — non guardati): `frontend/`, `frontend-old/`, `supabase/`, `odoo/`, `infra/`, `docker/`, `backend/migrations/`. `backend/scripts|tests|eval|cli` letti **solo** come superficie di riferimento per il censimento degli orfani, mai valutati. Gli altri 32 worktree non sono stati letti: il verdetto vale su `main`.

## `strumentazione`

Cosa si è potuto misurare qui, prima di qualunque reperto — così sai cosa copre il silenzio.

**Misurato (con leg di verifica chiusa):**

| Segnale | Metodo | Leg di chiusura |
|---|---|---|
| direzione degli import / accesso ai layer | passata AST su 301 moduli → 706 archi | Serena + lettura sorgente sui 4 sopravvissuti |
| cicli tra componenti | Tarjan SCC sullo stesso grafo | ispezione diretta delle 5 coppie |
| complessità ciclomatica | contatore AST proprio (`radon` non installato) — metodo: `1 + if/for/while/except/with/assert/IfExp/Match + operandi BoolOp + generatori di comprehension` | nessuna, è deterministico sul sorgente |
| dimensione per statement, aggregata **per modulo** (non per file) | AST — precondizione della regola 19 soddisfatta | — |
| moduli morti | censimento `Ca==0` + sweep testuale su tutto `backend/` | `find_referencing_symbols` su ognuno dei 3 sopravvissuti → `{}` |
| frequenza di modifica per modulo (volatilità) | `git log --since=180d --name-only` | — |
| leftover-naming-test | qualitativo, nomi scritti | — |

**Non misurabile qui → `ASSUMED`, con lo strumento che lo chiuderebbe:**

- **Abstractness `A` e quindi `D = |A+I−1|`.** Ho calcolato `A` dalle basi `ABC`/`Protocol`: viene ≈0 ovunque, perché Python è duck-typed. `D` risulterebbe dominato da `I` e **il numero sarebbe finto**. Non lo pubblico. Strumento: nessun equivalente JDepend/NDepend per Python — servirebbe prima una convenzione (interfacce `Protocol` dichiarate) perché la metrica significhi qualcosa. `distance-from-main-sequence` **non è stata applicata**.
- **LCOM** (per `lcom-before-splitting-a-shared-class`). Non calcolato. Strumento: matrice campo/metodo per classe, ~40 righe di AST. Nessun reperto qui sotto dipende da questo.
- **Chattiness runtime tra unità** (khononov 17). Non osservabile staticamente; è l'unica regola del set con dipendenza da strumentazione. Strumento: **Langfuse è già cablato** (`app/infra/tracing.py`) — un'aggregazione span-per-preventivo la chiuderebbe. È lo strumento più economico da aggiungere qui.
- **Static quantum diagram** (topologia operativa reale: code, cron, unità di deploy). Ho letto solo l'albero sorgente. Strumento: inventario `docker/` + workflow di deploy.
- **Copertura test.** CI non ha gate di coverage (`addopts = "-m 'not integration'"`, nessun `--cov`). Il numero non esiste.

**Stop condition di `where-to-start` — verificata prima di tutto:** il deploy **non** è intrattabile (workflow `deploy-backend-staging/prod`, `post-deploy-smoke`, `auto-revert` presenti). Quindi i reperti strutturali non sono accademici. `ASSUMED`: non ho eseguito `gh` per verificarne il verde.

**`four-reasons-not-to-build` — uscita valutata e non presa:** non è un big ball of mud (4 violazioni di layer su 706 archi, 5 cicli tutti di dimensione 2, media 60 statement/modulo), non è sacrificale, il business non chiude, nessuna caratteristica dominante in conflitto. **L'intervento è finanziabile.**

---

## Reperti — ordinati per raggio d'esplosione (decrescente)

> Nota sull'ordine: `gravità` = raggio, quindi questa classifica dice **quanto costa muoverlo**. L'ordine di escalation (`manutenzione > sviluppo > deploy > esercizio`) dice invece cosa prendere per primo col budget, ed è **R3**, che qui ha il raggio più piccolo.

---

### R1 — Nessuna regola architetturale eseguibile: 4 violazioni di layer e 5 cicli esistono e niente se ne accorge

- **`reperto`** — CI esegue `ruff` (nessun `select` in `pyproject.toml` → solo le regole di default `E4/E7/E9/F`) e un sottoinsieme di `pytest`. Nessun `import-linter`, nessun contratto di layer, nessun gate di coverage. Sotto quel silenzio: `app.services.chat_runner` importa **10 funzioni private** (prefisso `_`) da `app.api.chat` più 6 da `app.api.stream_protocol`, mentre `app.api.chat_stream` importa `chat_runner` — ciclo a 3 moduli attraverso il confine di layer. Più: `app.models.schemas → app.services.acorpo.models`, `app.repositories.quote_repo → app.services.error_logger`, e 5 cicli mutui (`listino_service ↔ price_lookup`, `pipeline_v4 ↔ runner`, `watchdog.checks ↔ cli`, `computo_reader ↔ .xpwe`, `web_market_triage ↔ _llm`).
- **`evidenza`** — censimento AST: 301 moduli, 706 archi, 4 violazioni, 5 SCC di dimensione 2. Leg di chiusura: lettura diretta delle righe di import in `chat_runner.py:27-47`, `schemas.py:3`, `quote_repo.py:4` — tutte confermate. Import dinamici confinati a `main.py` (registrazione router) e `api/health.py`: **la scansione statica è completa per gli archi app→app**, quindi il conteggio non è sottostimato.
- **`costo`** — `manutenzione/rischio` (un ciclo di N è una unità deployabile di N, qualunque cosa dica l'albero delle directory) + `sviluppo`.
- **`gravità`** — 17 moduli coinvolti. Il peggiore singolo: 3 (`api.chat_stream` → `services.chat_runner` → `api.chat`).
- **`semplificazione`** — **CANCELLARE** i due blocchi `from app.api...` in `chat_runner.py`: sono 16 simboli, 10 dei quali privati dell'API. Spostandoli sotto (a `app/services/` o `app/models/`) il ciclo sparisce senza aggiungere nulla — il file *è già* il posto dove vivono, ci sono finiti al contrario. Stesso trattamento per gli altri 4 archi.
- **`decisione`** — braccio **decisione architetturale** per la collocazione dei 16 simboli spostati (è la sola scelta con più letture); i restanti 4 archi sono meccanici.
- **`ASSUMED`** — **il check mancante è, secondo `directionality-of-imports`, il reperto vero**, non le violazioni. Ma installare `import-linter` è un'**ADDIZIONE**, e §5 clausola 2 chiede il costo rimosso e il costo aggiunto *come due numeri*: non li ho. Quindi, per `102 hypothesis-based-analysis`: **è un'ipotesi, non una raccomandazione.** L'evidenza che la deciderebbe: contare quante delle 4 violazioni sono state introdotte negli ultimi 180 giorni contro quante sono preesistenti. Se il tasso è ~0, il check costa più di quanto rende e non va installato.

---

### R2 — `services/` è un nome di layer che contiene almeno 9 domini; il più grande è un sottosistema batch che non appartiene al percorso di richiesta

- **`reperto`** — Il cluster GTM/CRM/Odoo è **13 moduli, 1.539 statement (18% di `services/`)** e ha **zero importatori dentro `app/`**: `gtm_outbox_worker`, `gtm_enrichment_ingest`, `gtm_phase0`, `gtm_phase1_drill`, `odoo_preflight`, `enrichment` sono guidati solo da `scripts/` e `tests/`; `odoo_crm_adapter` e `odoo_transport` sono importati solo da dentro il cluster stesso. È un sottosistema offline che vive nel package del percorso di richiesta.
- **`evidenza`** — `Ca==0` dal grafo per tutti i moduli `gtm_*`; sweep testuale su `backend/` che trova i riferimenti solo in `scripts/` e `tests/`; raggruppamento per statement misurato (GTM 1.539 / gepa-learning 847 / pricing 770 / quote-gen 743 / retrieval 592 / onboarding 580 / computo 559 / lifecycle 473 / acorpo 156 / **non raggruppabili 2.137 su 34 moduli**).
- **`costo`** — `manutenzione/spelunking` (il costo dominante: dove va una modifica al CRM? in `services/`, insieme alla generazione offerte) + `sviluppo`.
- **`gravità`** — 13 moduli spostati, **0 archi di import dentro `app/` da riscrivere** (verificato: `Ca==0`), ~2 entry point in `scripts/` e ~8 file di test da ri-puntare. 0 unità di deploy: stesso artefatto.
- **`semplificazione`** — **SPLIT**, e passa il `leftover-naming-test` in entrambe le direzioni: la parte estratta si chiama `gtm/`, il resto si chiama ancora "servizi di generazione offerte". Nessun nome inventato per il residuo, che è il criterio della regola 20.
- **`decisione`** — nessuna. È uno spostamento di directory, non un'estrazione di servizio: `5 build-services-from-components` non si applica perché non stiamo creando un deployable.
- **`ASSUMED`** — nessuno.

**E la parte che NON va toccata:** i 34 moduli "non raggruppabili" (2.137 statement) sono un outlier grande **senza sotto-domini chiari**. La regola 19 ha uno stop esplicito qui: *"if a component is a large outlier but contains no clear sub-domains, leave it as is. Splitting on size alone is not licensed."* Se un piano di refactor propone di spezzarli, quel pezzo di piano è sbagliato.

---

### R3 — `generator.py`: il 37% del file è morto dietro un toggle permanente, ed è il file più caldo del backend

**Il primo da prendere.** Raggio minimo, colonna di costo massima.

- **`reperto`** — `generate_quote` ritorna alla riga 1043 sul suo ramo di default. Le righe **1044–1263 (220 righe, 96 statement)** sono raggiungibili solo con `use_pipeline_v2=False`. **Nessun chiamante lo passa** — né in `app/`, né in `scripts/`, né in `cli/`, né in `eval/`. Con esse muoiono 3 helper usati solo lì: `_legacy_price_item` (26 righe), `_search_rag` (10), e `_trace_quote_to_langfuse` (**209 righe**).
- **`evidenza`** — tre leg indipendenti, tutte chiuse:
  1. AST: `return` alla riga 1043 dentro `if use_pipeline_v2:` (897–1043), che non ha `else`;
  2. grep di tutti i call site di `use_pipeline_v2` su `app|tests|scripts|cli|eval` → solo test, tutti passano `True`;
  3. **il repo lo sa già**: `tests/test_step6_admit_gate.py:144` dice testualmente *"the legacy (use_pipeline_v2=False) Step-6 loop has no live caller in this codebase"*.
  
  E il pezzo grosso è confermato superato, non perso: `_trace_quote_to_langfuse` è chiamato solo alla riga 1210 (dentro la regione morta), mentre il percorso vivo traccia via `app/infra/tracing.py` — il cui docstring recita *"replaces 40+ copy-pasted try/except blocks"*. **Non è un buco di osservabilità, è il duplicato che quel modulo doveva sostituire.** Quindi il reperto è strutturale, non comportamentale: nessuna lane `bugfix` da aprire.
- **`costo`** — `manutenzione/spelunking` come colonna dominante, e la misura di volatilità lo prova: **`generator.py` = 63 commit in 180 giorni, il file più modificato dell'intero backend**. Ogni singola di quelle 63 volte qualcuno ha dovuto capire quale metà del file fosse viva. Secondariamente `manutenzione/rischio`: 14 parametri sulla firma pubblica, di cui uno è il toggle morto.
- **`gravità`** — **3 file**: `generator.py` + `tests/test_step6_admit_gate.py` (13 test) + `tests/test_langfuse_trace_parent.py` (6 test). 0 unità di deploy.
- **`semplificazione`** — **CANCELLARE ~465 righe su 1263 (37% del file)**, un parametro su 14 dalla firma pubblica, e la complessità ciclomatica di `generate_quote` scende **da 65 a 25 (−62%)** — misurato, non stimato: il ramo morto vale 41 dei 65 punti. È l'unica funzione di `services/` sopra CC 50, la soglia oltre la quale `cc-threshold` dice che nessuna copertura la salva.
- **`decisione`** — nessuna. Cancellazione pura.
- **`ASSUMED`** — i 19 test nei due file toccati vanno riscritti, non solo cancellati: alcuni verificano l'admit-gate che esiste **anche** sul percorso vivo. La precondizione di `coarse-functional-tests-before-restructuring` è **soddisfatta** qui (32 file di test importano `generator`, `tests/test_pipeline/test_integration.py` copre il percorso vivo end-to-end), quindi non serve un giro di test prima — ma quale dei 19 sia genuinamente legacy-only non l'ho verificato test per test.

---

### R4 — Tre moduli di `services/` con zero riferimenti, confermati dal grafo

- **`reperto`** — `prezzario_pricer.py` (47 statement, `price_items_from_prezzario`), `onboarding/orchestrator.py` (37, `run_onboarding`), `listino_storage.py` (16, `store_listino_upload` + `safe_name`). 100 statement totali.
- **`evidenza`** — censimento: `Ca==0` e **zero riferimenti testuali** in tutto `backend/` (`scripts`, `tests`, `eval`, `cli`, `config`, `migrations`, `deploy`, inclusi `.yaml/.json/.toml`). Leg di chiusura: `find_referencing_symbols` su ognuno dei tre simboli pubblici → `{}` per tutti e tre. Su 30 moduli `services/` con zero importatori in-app, questi sono i **soli 3** senza alcun riferimento altrove: gli altri 27 sono job batch guidati da `scripts/`, e **non** sono morti.
- **`costo`** — `manutenzione/spelunking`. `prezzario_pricer` è il caso peggiore: il suo docstring promette *"replace LLM-generated prices with prezzario matches"*, che è esattamente ciò che il tier 3 di `price_lookup` fa davvero. Un lettore che cerca il pricing da prezzario trova prima il file morto.
- **`gravità`** — 3 moduli, 0 riferimenti da aggiornare.
- **`semplificazione`** — **CANCELLARE** 3 file, 100 statement.
- **`decisione`** — nessuna.
- **`ASSUMED`** — nessuno. Questa è la riga più chiusa del report.

---

### R5 — `services/pricing.py` è uno shim di passaggio dentro un cluster pricing di 11 moduli

- **`reperto`** — `pricing.py` è un solo `async def match_prices_for_items` che chiama `lookup_prices_for_items` di `price_lookup`, con un unico importatore (`capitolato_pricer`). Il cluster attorno è: `price_lookup`, `price_overlay`, `listino_service`, `computo_pricing`, `capitolato_pricer`, `prezzario_pricer` (morto, R4), `regole_prezzario`, `um_normalizer`, `pricing`. Con dentro un ciclo mutuo: `listino_service ↔ price_lookup`.
- **`evidenza`** — grafo di import + docstring letti su tutti e 9 i moduli. `pricing.py ← [capitolato_pricer]`, `price_lookup ← [agents.tools, domain_validator, generator, listino_service, pricing]`.
- **`costo`** — `manutenzione/spelunking`. `pricing_v4.py` (`app/pipeline/steps/`) è a 60 commit/180gg, secondo solo a `generator.py`: il pricing è la zona calda, ed è quella con un livello di indirezione in più.
- **`gravità`** — 2 moduli per lo shim; 2 per il ciclo.
- **`semplificazione`** — **CANCELLARE** `pricing.py` facendo importare a `capitolato_pricer` direttamente `price_lookup` (un chiamante, una riga). Il ciclo `listino_service ↔ price_lookup` va rotto separatamente ed è parte di R1.
- **`decisione`** — nessuna per lo shim.
- **`ASSUMED`** — **non ho valutato se il cluster pricing a 11 moduli sia il confine giusto.** Servirebbe LCOM (non disponibile, vedi `strumentazione`) e la chattiness runtime via Langfuse. Finché non esistono, "spezzare o fondere il pricing" è una domanda aperta, non un reperto — e ci sono 770 statement in ballo, quindi non va deciso a occhio.

---

## §5 — Test dell'addizione

Applicato a ogni raccomandazione. **R3, R4, R5 e la metà eseguibile di R1 sono cancellazioni. R2 è uno split il cui residuo ha un nome proprio.** Nessuna raccomandazione fa crescere il sistema.

L'unica addizione che si è affacciata — `import-linter` in R1 — **fallisce la clausola 2** (nessun before/after numerico) ed è marcata come ipotesi, con l'evidenza che la deciderebbe. Non è nel piano.

Totale cancellabile con verifica chiusa: **~570 righe** (465 in `generator.py` + 100 statement in 3 moduli morti + lo shim), più 13 moduli spostati senza riscrivere un solo import interno ad `app/`.

## Noted, not actionable

- `app/autoresearch_v3/` e `app/autoresearch_v4/` contengono **zero file `.py`** — solo `__pycache__` residuo. Cancellabili, raggio 0.
- `app/_archive/` — 2 moduli, 163 statement, già dichiarati archivio.
- 66 funzioni in `services/` sopra CC 10 su 757 (8,7%) e 175 sopra le 20 righe. **Non è un reperto**: `cc-threshold` fallisce ovunque solo se il codebase intero sfonda la soglia, e qui non lo fa — 8,7% significa che un gate a 10 sarebbe installabile. Ma installarlo è un'addizione e vale la stessa obiezione §5 di R1.
- `app/pipeline` (3.807 statement) e `app/services` (8.396) si sovrappongono concettualmente sulla generazione offerte. **Non l'ho valutato**: il perimetro chiesto era `services/`, e giudicare quel confine richiede il quantum diagram operativo che non ho.
