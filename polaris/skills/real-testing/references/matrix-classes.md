---
title: real-test — le 10 classi della matrice per-hunk
description: Dettaglio per classe — cosa cercare, prova minima, e se e' "a prova live obbligatoria" (LIVE_REQUIRED in verdict.py).
status: active
---

# Le 10 classi

Ogni file/hunk del diff appartiene a una di queste classi (`verdict.py new` la indovina
dall'estensione/percorso, correggila a mano se sbaglia — e' un aiuto, non oracolo).

Le classi in **grassetto** sono `LIVE_REQUIRED`: `verdict.py` rifiuta `evidence: not-applicable`
su di loro (devono essere `live` con artefatto, o `assumed` con `exception_ticket` — mai silenzio).
Nascono da G2.1 (34 osservazioni: "il test verde certifica il mock, non il comportamento reale") —
sono esattamente le classi dove le fonti misurano il pattern: DB mockato, LLM mockato, endpoint
sbagliato, dipendenza mai installata pulita, browser mai aperto davvero.

| Classe | Cosa cercare | Prova minima | Live-required |
|---|---|---|---|
| `symbol` | chiamanti, fallback, tipi, errori | percorso reale di ogni chiamante | no |
| **`api-cli`** | contratto pubblico e consumatori | invocazione reale + forma output + errore | **si'** |
| `config-ci` | parsing, precedenza, deny/allow | carica config + caso positivo e negativo | no |
| **`dependency`** | fresh install, import, packaging | ambiente pulito + build/import | **si'** |
| **`db-migration`** | fresh install, upgrade, vincoli, dati | DB reale + schema/dati prima/dopo | **si'** |
| **`frontend`** | build, routing, rete, console, stati UI | browser vero + network + console | **si'** |
| **`llm-agent`** | provider, tool call, output, fallback | chiamata provider-backed + trace | **si'** |
| `deletion` | riferimenti attivi, config, sostituto | vecchio percorso assente + sostituto funzionante | no |
| `docs` | link, comandi copiabili, residui | link/checker mirato; niente stack se non rilevante | no |
| `test-only` | il test fallisce davvero sul difetto | prova negativa o mutation mirata | no |

## Asse degli attacchi (`verdict_attack.py`)

La classe dice **dove** atterra la modifica; l'attacco dice **come** è stata colpita. Ogni riga ha una
lista `attack`: ogni voce nomina una classe, e o è `run` con `probe` e `result`, o è `n/a` con `reason`.
Una riga `live` di classe `api-cli`, `llm-agent` o `frontend` senza almeno un attacco `run` è rifiutata.

| Attacco | Cosa prova |
|---|---|
| `malformed-input` | JSON rotto, campi mancanti, stringhe enormi, Unicode strano, path tipo traversal |
| `interruption` | continue/stop ripetuti, output tagliato a metà, retry dopo progresso parziale |
| `prompt-injection` | testo che prova a scavalcare le regole, saltare la verifica, dichiarare successo |
| `cancel-resume` | annullo a metà, poi ripresa o ripartenza da stato in corso rimasto |
| `stale-state` | file di stato vecchi, sessioni che non combaciano, metadati di fase contraddittori |
| `dirty-worktree` | modifiche e file non tracciati preesistenti restano intatti |
| `hung-command` | un comando che non torna: timeout limitato, figlio ucciso, ripresa |
| `flaky` | politica di rerun: un passaggio fortunato non è verde |
| `misleading-success` | parole di successo con exit diverso da 0, test saltati, log parziali |

Un harness costruito male (import sbagliato, interpolazione di shell, ambiente che trapela) non è un
difetto del prodotto: si classifica come detrito, si ripara e si ripete la prova.

## Regole di evidenza (`verdict.py validate_evidence`)

- `evidence: live` → richiede `evidence_artifact` che esista, non sia vuoto, e sia **piu' recente**
  del file sorgente sul disco (altrimenti e' G2.6: prova raccolta prima dell'ultima modifica, come
  nel caso reale del newline-collapse validato sulla funzione vecchia).
- `evidence: assumed` → richiede `exception_ticket` non vuoto. E' l'unica via legittima per una
  classe LIVE_REQUIRED senza prova live (es. niente credenziali provider disponibili in questa
  sessione) — un rischio **scritto e tracciato**, non taciuto.
- `evidence: not-applicable` → vietato su LIVE_REQUIRED. Consentito solo su classi che non lo sono
  (es. un file `docs` che non tocca boot/build/runtime).

## Scala del "livello piu' reale pertinente"

Dal piu' economico, fermati quando il contratto e' provato — non oltre:

1. test mirati
2. CLI/modulo reale — se il repo dichiara i comandi dei suoi flussi (un manifest o uno script
   documentato), usa quelli invece di improvvisare l'invocazione
3. stack locale reale con DB/queue/storage
4. browser locale reale
5. provider sandbox/staging
6. staging deployato con browser, DB e trace

Frontend: browser obbligatorio se cambiano UI/build/routing/wiring. DB: DB reale obbligatorio se
cambiano query/schema/migrazioni/transazioni. LLM: chiamata provider-backed obbligatoria se cambia
modello/prompt/toolset/routing — se mancano credenziali il verdetto e' `NOT-MERGEABLE` salvo che il
repo dichiari esplicitamente quel controllo come gate post-merge (allora e' `MERGEABLE-CON-GAP`).
