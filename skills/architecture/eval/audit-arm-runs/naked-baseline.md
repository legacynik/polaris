## Verdetto

L'architettura è **meno rotta di quanto la dimensione suggerisca**. 39.4k LOC in `app/`, ma solo 5 cicli di import (tutti da 2 nodi, locali), un solo path di generazione vivo in prod, e una config pulita. I problemi veri sono tre, e solo uno merita un progetto.

Metodo: census AST dell'intero grafo di import di `app/` (301 file), verifica dei sopravvissuti con grep repo-wide su `app/ eval/ scripts/ tests/`. Non ho eseguito test né misurato coverage — dove parlo di test parlo di conteggi, non di verde.

---

## Cosa è messo bene (per non rifattorizzarlo)

- **Cicli**: 5 SCC, tutti da 2 nodi e intra-modulo (`listino_service↔price_lookup`, `pipeline_v4↔runner`, `web_market_triage↔_llm`, `watchdog.checks↔cli`, `computo_reader↔xpwe`). Per un backend di questa taglia è poco.
- **Un solo path di generazione in prod**. REST → `background_runner` → `generate_quote`; chat agent → `generate_quote`; computi → `computo_entry` → `finalize_pricing` (ingresso allo Step-6, deliberato e documentato). Il path divergente `mode="quote"` è 410 Gone (#554/#529). Quel lavoro ha retto.
- **Config**: 192 LOC, 44 campi, **zero flag dark default-`False`**. La disciplina flag di CLAUDE.md ha funzionato davvero.
- **Test**: 539 file, 3971 `def test_`. Non è un backend senza rete.

---

## I problemi, in ordine di rapporto danno/costo

### 1. `app/services/` non è un layer, è un namespace — 125 file, 18.7k LOC, 7 contesti

| Contesto | file | LOC |
|---|---|---|
| generation/pricing | 21 | 4000 |
| **GTM/CRM** (odoo, outbox, lifecycle, enrichment) | **13** | **3045** |
| learning/feedback | 18 | 3023 |
| ingest/parse | 21 | 2243 |
| platform/obs | 16 | 2470 |
| LLM infra | 7 | 1604 |
| retrieval/search | 14 | 1434 |

141 edge interni a `services/`, nessuna barriera fra i gruppi. Il caso più netto: **3045 LOC di CRM Odoo condividono processo, DB, release cycle e blast radius con la pipeline che genera le offerte**. Un deploy del CRM può far cadere la generazione, e viceversa.

### 2. `generator.py` — il god-module

1263 LOC. `generate_quote()` = **389 righe, 14 parametri** (gate: 20 righe / 3 param). Fa quattro lavori scollegati: orchestrazione, motore di pricing Step-6 (`_adopt_step6_lookup`, `_merge_lookup_into_items`, materiality gate, overlay, price index), export tracing Langfuse (`_trace_quote_to_langfuse`, 208 righe), vista a-corpo.

**20 import funzione-locali** su 220 in tutto `app/` — è la firma della circolarità evitata a mano, non di lazy-loading. Include `from app.pipeline.steps.pricing_v4 import _price_journey`: un simbolo privato di un altro modulo.

### 3. Tre astrazioni ferme a metà migrazione — costano più di quanto rendano

**a) `PipelineConfig`: 17 campi, 12 morti.** Verificato leggendo la catena:

```
generate_quote → run_pipeline_with_config(17) → run_pipeline(17, ne ignora 12) → run_pipeline_v4(5)
```

Il docstring di `run_pipeline` lo dice esplicito: i kwargs legacy «are accepted … but ignored». Tre livelli di adattatore per una chiamata a 5 parametri, e la migrazione citata nel docstring (`2026-05-07-pipeline-config-migration-plan.md`) è ferma da 3 mesi e mezzo. **Non è estetica**: un caller che setta `skip_audit`, `fetch_prezzario`, `use_reranker` o `item_cap` crede di configurare la pipeline e non configura niente. Gli unici caller dei kwargs legacy sono 2 script dev (`gepa_reprice.py`, `_sandbox_wiring.py`).

**b) Repository layer adottato a metà.** 6 repository esistono, ma **41 moduli importano `app.db` direttamente** e 51 file fanno query raw fuori da `repositories/`+`prezzario_db`. Il layer API è spaccato in due: 16 edge verso `repositories`, 18 verso `db`. Costo concreto: il cutover Supabase staging/prod e ogni cambio di schema toccano 41 posti invece di 6.

**c) `PIPELINE_VERSION`**: `run_pipeline` accetta ancora il parametro e solleva `RuntimeError` se ≠ v4. Un branch morto che sopravvive per messaggio d'errore.

### 4. Router core caricati come "optional", con except-and-warn — fix da 5 minuti

`app/main.py:250` — `app.api.quotes`, `chat`, `computi`, `quote_stream` sono in `_optional_routers`:

```python
except Exception as e:
    logger.warning("Skipping %s: %s", module_path, e)
```

Un ImportError in `app.api.quotes` produce: **boot verde, `/health` verde, POST /api/quotes → 404**. È esattamente la classe di silent failure che E33 vieta, piazzata alla radice dell'app. `crm_manual_actions` sta invece fra i `_required_routers` — il CRM è protetto, la generazione no.

(Nota a margine, stesso file: `@app.on_event` è deprecato da FastAPI in favore di `lifespan`.)

### 5. Inversioni di dipendenza — poche, ma tutte sintomatiche

- `services/chat_runner.py:27,40` → `app.api.chat`, `app.api.stream_protocol` (service che dipende dall'HTTP layer)
- `models/schemas.py:3` → `app.services.acorpo.models`
- `repositories/quote_repo.py:4` → `app.services.error_logger`
- `infra/tracing.py:46,120` → `_ambient_trace_meta`, privato di `litellm_client`
- **31 import di simboli privati cross-modulo** in totale

### 6. Dead code — verificato, non stimato

- `services/listino_storage.py` e `services/prezzario_pricer.py`: **zero riferimenti in tutto il repo** (`prezzario_pricer` contiene una funzione da 118 righe)
- `app/autoresearch_v3/` e `app/autoresearch_v4/`: directory vuote
- 5 cartelle `_archive/` = 5347 LOC (`app/`, `app/pipeline/`, `tests/`, `scripts/`, `eval/`)
- `scripts/run_langfuse_experiment.py`: importa `app.autoresearch_v4.*` che non esiste più — rotto e **non** archiviato

### 7. Un secondo path nell'eval

`eval/v4/runner.py` e `eval/runner.py` passano correttamente da `generate_quote`. **`eval/matrix_query.py:105` chiama `run_pipeline_with_config` diretto** → salta `finalize_pricing`, materiality gate, overlay e vista a-corpo. È il pattern E40 (eval≠prod = false gate), sopravvissuto in un modulo laterale. `eval/` ha ~70 moduli top-level e 5 runner diversi: la sprawl è lì, non in `app/`.

---

## Cosa farei, e in che ordine

**Prima di qualsiasi refactor** (< 1 giorno, rischio quasi nullo, riduzione di rischio reale):
1. `app.api.quotes`/`chat`/`computi`/`quote_stream` → `_required_routers`. Il boot deve fallire rumorosamente.
2. Cancella `listino_storage.py`, `prezzario_pricer.py`, le due dir vuote, `run_langfuse_experiment.py`.
3. Chiudi `PipelineConfig`: 17 campi → 5. I 2 script dev si adeguano. Elimina `run_pipeline` e `run_pipeline_with_config`, lascia `run_pipeline_v4`.
4. `eval/matrix_query.py` → `generate_quote`, o dichiaralo esplicitamente non-gate.

**Il progetto vero, se lo vuoi fare**: estrarre il pricing Step-6 da `generator.py` in un modulo suo. Non perché il file è lungo, ma perché è **l'unica cosa in `generator.py` che l'eval deve poter chiamare isolata** — e già oggi `computo_entry` ci entra dalla porta di servizio. Il tracing Langfuse (208 righe) esce nello stesso taglio. Restano ~400 righe di orchestrazione onesta.

**Cosa NON farei ora**: separare GTM/CRM in un servizio proprio. È l'anomalia architetturale più grossa, ma è isolata (13 file, dipendenze in uscita chiare) e non ti sta facendo male oggi. Costa settimane, rende quando avrai un secondo deploy target.

---

## L'obiezione

Hai chiesto un audit architetturale e questo è quello che ho trovato. Ma il numero che governa il prodotto in questo momento è **Step 2 al 26% di precisione**, con recall pool al 67%. Nessuno dei problemi qui sopra ne è la causa, e nessun refactor lo sposta di un punto — anzi, i punti 4 e 5 dell'audit riguardano codice che il replay non attraversa nemmeno.

I quattro interventi rapidi valgono comunque: costano un pomeriggio e uno di essi (i router optional) è una bomba a orologeria. Lo split di `generator.py` invece è la cosa da mettere in coda dietro la precisione, non davanti — a meno che tu non lo faccia proprio *per* poter misurare lo Step 2 isolato, che è l'unica motivazione che lo renderebbe urgente.
