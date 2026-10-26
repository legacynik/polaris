# Decisione architetturale — generazione offerte: percorso sincrono con heartbeat vs pipeline asincrona

**Titolo (ADR):** Generazione offerte grandi: sostituire il percorso edge sincrono con una pipeline asincrona (job queue + polling/SSE)
**Trigger arm:** architectural decision → `ford-richards-hard-parts` §J: `least-worst-not-best` (86) · `three-step-tradeoff-process` (87) · `mece-the-comparison-set` (90) · `qualitative-not-quantitative` (89) · `model-the-hard-scenario` (92) · `bottom-line-not-evidence` (93) · `adr-with-alternatives-and-consequences` (98)
**Qualifica per ADR** (regola globale: supera una decisione corrente — esecuzione sincrona — e fissa direzione architetturale con impatto 30gg–anni su `chat_runner` e l'interfaccia dell'estimator) → `adr/2026-08-18-adr-quote-generation-async-pipeline.md`

---

**reversibilità**: `OWNED`. Tutte e tre le condizioni tengono: (a) caller set chiuso — tutti i chiamanti vivono in questo repo, nessun consumer esterno nominabile; (b) ogni caller sta in un repo pushabile da noi; (c) nessuna approvazione/finestra di rilascio di terze parti richiesta ("deployed by us"). Nota: (a) è presa per dato dichiarato dal fixture — nessuno script di census né lookup sul grafo è stato eseguito su codice reale in questo run (vedi `ASSUMED`).

**opzioni** (MECE — rule 90):
- **A — sync edge + heartbeat**: stesso modello di esecuzione (blocca la request fino al risultato), workaround che mantiene viva la connessione durante la generazione lunga.
- **B — pipeline async (job queue + polling/SSE)**: `chat_runner` sottomette un job, l'estimator lo esegue fuori dal ciclo request/response, il risultato arriva per poll o subscribe.

Nessuna terza opzione viva: alzare il ceiling non è nelle mani del team (vincolo di piattaforma), e uno streaming di risultati parziali dentro la stessa invocazione sincrona è una variante di A, non un'alternativa distinta.

**costo per opzione** (mai il beneficio — rule 86/89):
- **A**: non rimuove il vincolo strutturale — se il "ceiling" è un hard cap sul tempo di invocazione (non un idle-timeout), l'heartbeat non lo tocca e l'opzione può restare inefficace esattamente sulle offerte grandi che oggi lo triggerano; anche se efficace, richiede ri-tuning ricorrente man mano che le offerte crescono, senza margine strutturale; `chat_runner` resta bloccato sull'intera durata della generazione (rischio timeout lato client indipendente dal ceiling edge); nessuna resumability — un fallimento a metà perde tutto il lavoro fatto.
- **B**: `chat_runner` e l'interfaccia dell'estimator cambiano contratto (da return-in-place a submit+poll/subscribe) — ogni call site nel repo va migrato nella stessa finestra; nuovo componente infrastrutturale (coda + worker + store stato job) da costruire, operare, monitorare; nuove classi di failure da progettare esplicitamente (job orfano, poll che scade, doppia esecuzione/idempotenza, worker crashato a metà) — più superficie di concorrenza da presidiare.

**scelta**: **B — pipeline async**. Applicando `model-the-hard-scenario` (92): lo scenario duro non va modellato, è già lo scenario di oggi — le offerte grandi rompono il ceiling adesso. Sotto questo scenario A rischia di non risolvere affatto il problema (dipende dal tipo di ceiling, non verificato — vedi ASSUMED), mentre B lo rimuove strutturalmente una volta per tutte. In linguaggio di business (`bottom-line-not-evidence`, 93): la domanda non è "heartbeat o coda", è "vogliamo che generare un preventivo abbia per sempre un tetto di dimensione/complessità, o investiamo una volta per toglierlo definitivamente" — la seconda vince come meno peggio, non come design migliore: si paga in superficie di migrazione e nuova infrastruttura, si compra l'assenza di un vincolo che oggi sta già fallendo in produzione.

**enforcement**: check meccanico (grep/graph sul repo) che segnala — commento rosso, mai blocco CI, fuori dai gate CI propri e dalla pipeline AFK — ogni nuova call-site che invoca l'estimator in modalità return-diretto anziché tramite submit al job queue, per impedire che un nuovo caller reintroduca silenziosamente il percorso sincrono dopo la migrazione.

**verifica di chiusura**: dichiarata prima del lavoro, eseguita da un job CI (non dal founder): (1) query sul grafo simboli — zero caller residui della vecchia firma sincrona dell'estimator; (2) load-test che genera il preventivo più grande noto oggi attraverso il percorso async e completa senza toccare alcun ceiling di piattaforma. La decisione non è chiusa finché entrambe non tornano verdi.

**ASSUMED**:
1. **Tipo di ceiling** (hard wall-clock cap vs idle-timeout resettabile da heartbeat) — non specificato nell'input, assunto hard cap dal termine "ceiling". Se fosse idle-timeout, il costo di A cambia sostanzialmente e la scelta va riaperta. Nessuna piattaforma è nominata nell'input per verificarlo.
2. **Chiusura del caller set** (condizione a della reversibilità) — presa dal fixture ("all callers live in this one repo"), non riverificata con census script + graph su codice reale: nessuno script di census esiste in questa cartella (`skills-suite/architettura/scripts/` vuota) e nessun repo bersaglio concreto era in scope per questo run.
3. **Margine di headroom offerto da un heartbeat**, se applicabile — dipende da limiti specifici del vendor/piattaforma non nominato nell'input.