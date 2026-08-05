---
name: real-testing
description: "Gate adversariale pre-merge e post-deploy. Deriva il perimetro dal diff reale con Serena, classifica ogni cambiamento incluse config/CI/docs/migrazioni/dipendenze/delezioni, collega ogni conseguenza a una prova osservabile, verifica happy path, failure path e bordi sul livello piu reale disponibile, e chiude lasciando in CI il test che protegge cio che hai trovato. Usala prima di ogni merge o deploy, dopo una fix o un refactor, e quando ti chiedono se una PR e davvero testata o mergiabile."
user-invocable: true
model: sonnet
version: 1.1.0
---

# Real Testing

## Regola

**Test verdi non provano che il cambiamento funzioni. Ogni hunk deve avere una conseguenza dichiarata e ogni conseguenza una prova osservabile.**

Non eseguire rituali estranei al diff. Browser, DB, provider e trace sono obbligatori solo quando il percorso cambiato li attraversa o il playbook del repo li richiede.

## 0. Fissa branch, base e delta

Prima di testare:

1. Verifica branch e worktree secondo le regole del repo.
2. Determina la base reale della PR; preferisci la base dichiarata dalla PR, poi l'upstream configurato. Non assumere `main`.
3. Aggiorna la base se è sicuro e consentito. Se non puoi, registra commit e freschezza della base come gap.
4. Raccogli almeno:
   - `git diff --name-status <base>..HEAD`
   - `git diff --stat <base>..HEAD`
   - `git diff --check <base>..HEAD`
   - commit inclusi e stato sporco del worktree
5. Simula l'integrazione senza modificare il worktree, per esempio con `git merge-tree --write-tree <base> HEAD`. Un conflitto rende la PR non mergiabile.

Non testare file staged isolati se il verdetto richiesto riguarda una PR: testa esattamente il delta `<base>..HEAD`.

## 1. Carica il playbook verticale

Cerca prima `_project_specs/testing-protocol/INDEX.md` o l'equivalente indicato dalle istruzioni del repo. È la fonte primaria per tenant, fixture, credenziali, comandi e soglie reali.

Prima di eseguirlo, verifica con Serena che file, simboli e call-chain nominati esistano ancora. Se divergono, marca il playbook come stale e testa il codice attuale; non eseguire comandi obsoleti alla cieca.

Il playbook e il perimetro derivato dal diff si sommano: il playbook conosce l'ambiente, Serena conosce il blast radius.

## 2. Classifica OGNI cambiamento

Costruisci una matrice. Ogni file/hunk deve comparire, individualmente o in un gruppo semanticamente equivalente:

| Classe | Conseguenze da cercare | Prova minima reale |
|---|---|---|
| Simbolo applicativo | chiamanti, fallback, tipi, errori | Serena + percorso reale di ogni chiamante |
| API/CLI/tool/event/schema | contratto pubblico e consumatori | invocazione reale + forma output + errore |
| Config/permission/hook/CI | parsing, precedenza, deny/allow, comando avviato | carica config + caso positivo e negativo |
| Dipendenza/lock/build | fresh install, import, packaging, vulnerabilità | ambiente pulito + build/import/audit |
| DB/migrazione/storage | fresh install, upgrade, vincoli, dati, recovery | DB reale + schema/dati prima/dopo |
| Frontend | build, routing, rete, console, stati UI | browser vero + network + console |
| LLM/agent/prompt/toolset | provider, tool call, output, fallback, usage, trace | chiamata provider-backed + trace, se toccato |
| Delezione/rename | riferimenti attivi, config, processo, binario, sostituto | vecchio percorso assente + sostituto funzionante |
| Docs/guidance/history | link, comandi copiabili, residui, gate contenuto | link/checker/search mirata; niente stack se non rilevante |
| Test-only | test che fallisce davvero sul difetto e copre il contratto | prova negativa o mutation mirata |

Puoi raggruppare decine di file documentali modificati dalla stessa sostituzione solo se una ricerca repo-wide e il content gate provano l'intero gruppo. Non usare il raggruppamento per nascondere eccezioni.

Per ogni riga registra:

```text
file/hunk -> contratto o comportamento -> consumatori -> failure mode -> prova -> PASS/FAIL/GAP
```

Un file non classificato rende il gate incompleto.

## 3. Deriva il blast radius con Serena

Attiva Serena sul worktree esatto della PR, poi per ogni simbolo modificato:

1. `find_symbol`: firma, tipi e corpo attuale.
2. `find_referencing_symbols`: chiamanti diretti.
3. Ripeti sui chiamanti quando attraversano un boundary pubblico o un adapter.
4. Identifica endpoint, CLI, schema, evento, migrazione, tool agente o file configurazione che espongono il cambiamento.

Zero riferimenti non significa automaticamente codice morto: controlla entrypoint, registrazione dinamica, framework routing, reflection, string lookup e file non analizzabili. Se il simbolo dovrebbe avere chiamanti e Serena restituisce zero, correggi progetto/path/query prima di proseguire.

Dichiara il perimetro prima delle prove:

```text
Perimetro derivato:
  delta: <base>..<head>, N file
  simboli: ...
  chiamanti: ...
  cambiamenti non simbolici: ...
  contratti al bordo: ...
  prove richieste: ...
  superfici escluse perché non attraversate: ...
```

Una superficie estranea al diff è **fuori perimetro**, non un gap. Esempio: nessun cambiamento al runtime Pydantic/LLM significa che l'assenza di credenziali provider non blocca quella PR.

## 4. Progetta prove avversariali

Per ogni ramo nuovo o modificato esegui almeno:

- happy path realistico;
- failure path atteso;
- bordo rilevante: vuoto, malformed, limite, duplicato, timeout, stato assente o config stale;
- fallback/degraded path, se esiste;
- persistenza e side effect, se esistono;
- log senza errori/warning inattesi nella finestra della prova.

Verifica il contratto, non solo l'exit code: status, payload, record DB, file generato, evento, tool call, UI, trace o processo devono avere la forma attesa.

Quando possibile, dimostra che la prova è sensibile al difetto: fixture negativa, assertion sul ramo rotto o confronto controllato. Un comando che passerebbe anche senza il cambiamento non è evidenza sufficiente.

Completezza obbligatoria: se playbook o matrice elencano N prove, riporta N risultati. N-1 non è verde.

## 5. Usa il livello più reale pertinente

Procedi dal più economico al più reale e fermati quando il contratto è provato:

1. test mirati;
2. CLI/modulo reale;
3. stack locale reale con DB/queue/storage;
4. browser locale reale;
5. provider sandbox/staging;
6. staging deployato con browser, DB e trace.

Regole di rilevanza:

- **Frontend:** browser obbligatorio se cambiano UI, build, routing, API base o wiring frontend/backend.
- **DB:** DB reale obbligatorio se cambiano query, schema, migrazioni, transazioni o mapping persistiti.
- **LLM/provider:** chiamata provider-backed obbligatoria se cambiano modello, prompt, toolset, output validator, routing o fallback. Se mancano credenziali, il gate è `NOT MERGEABLE` salvo che il repo definisca esplicitamente quel controllo come gate post-merge.
- **Langfuse/trace:** obbligatorio quando il percorso testato invoca un LLM o cambia observability. Verifica parent/children, zero orfani, errori, versione/tag e usage.
- **API:** chiamata HTTP reale obbligatoria se cambia route, middleware, auth, serialization o wiring runtime.
- **Docs/config-only:** non avviare l'intero prodotto salvo che il file controlli realmente boot/build/runtime.

Non stampare segreti. Per provider a pagamento dichiara numero massimo di chiamate e usa la fixture minima che prova il contratto.

## 6. Gate di merge locale

Esegui, quando applicabili al delta:

- test mirati dei comportamenti toccati;
- suite/lint/typecheck/build richiesti dal repo;
- install/build puliti quando cambiano dipendenze o packaging;
- smoke reale sulle superfici individuate;
- `git diff --check`;
- simulazione merge contro la base;
- verifica worktree finale e artefatti non intenzionali;
- verifica che ogni nuovo test sia incluso nel runner CI corretto.

CI verde remoto e peer review restano requisiti separati se il repo li impone. Il gate locale non deve fingere di averli eseguiti.

## 7. Verdetto obbligatorio

Concludi con uno solo di questi:

- **MERGEABLE**: tutte le prove richieste dal delta e dal playbook pre-merge passano; integrazione pulita; nessun gap rilevante.
- **MERGEABLE CON GAP**: il delta è provato e integra pulito, ma resta un controllo esterno/non bloccante esplicitamente post-merge o post-deploy. Indica proprietario e momento del gate.
- **NOT MERGEABLE**: conflitto, prova fallita, file non classificato o prova rilevante mancante.

Formato:

```text
VERDETTO: MERGEABLE | MERGEABLE CON GAP | NOT MERGEABLE
Base/HEAD: <sha> / <sha>
Perimetro: N file, N simboli, N contratti, N prove
PASS: <una riga per prova>
FAIL: <una riga per prova>
GAP: <solo evidenza pertinente non eseguibile>
FUORI PERIMETRO: <superfici considerate ma non attraversate>
Artefatti: <log, screenshot, trace, query, output>
```

Non usare “sembra”, “dovrebbe” o un solo verdetto aggregato senza evidenze.

## 8. Dopo un deploy

Il deploy aggiunge un gate di promozione, non riscrive retroattivamente il gate locale:

1. migration/schema reali se applicabili;
2. smoke API end-to-end;
3. browser vero, network same-origin e console;
4. DB/queue/storage per i side effect;
5. trace provider-backed per flussi LLM;
6. log e metriche nella finestra della prova.

Se uno fallisce, la release non è promuovibile anche se la PR era mergiabile.


## 9. Raccolto — il real-test NON è finito finché non ha lasciato un test in CI


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
