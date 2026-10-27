---
id: 2026-08-02-skill-versioning-e-gate-di-promozione
title: Ogni skill porta la propria versione, e nessuna modifica si promuove senza eval
status: accepted
scope: polaris-skills
decider: Niccolò Franzin
date: 2026-08-02
supersedes: —
governed:
  - skills/*/SKILL.md
  - evals/run_behavior.py
  - evals/cases.json
component: polaris-skills
decides: change-promotion
value: per-skill-semver-gated-by-eval
---

# Ogni skill porta la propria versione, e nessuna modifica si promuove senza eval

## 1. Contesto (misurato, non opinione)

Fino a oggi le nove skill Polaris non avevano versione propria: l'unica esisteva in
`plugin.json`. Due conseguenze misurate:

- **Il numero non discrimina.** Rilasciando 0.16.0 avanzano tutte e nove, anche `/report` che non è
  stato toccato. Chi legge un numero non sa cosa è cambiato in cosa.
- **La versione non viaggia con la skill.** Il 2026-07-30 la stessa skill esisteva in tre stati
  diversi sulla stessa macchina — `~/.agents/skills` copiata a mano, cache plugin a 0.14.0, dev clone
  a 0.15.0 con modifiche non committate. Nessun modo di sapere quale girava se non diffando i file.
  Su 337 skill installate, 68 hanno un `version:`; le nostre nove: zero.

E fino al 2026-08-02 nessuna modifica a una skill è mai stata misurata prima di essere promossa. Il
costo si è visto: `/end` committava in prosa su qualunque branch (handoff strandati su rami mai
mergiati), `/update` prescriveva uno script irraggiungibile sulle macchine skills-CLI, la stessa
skill si contraddiceva su Codex in due righe diverse. Tutti difetti che un caso rosso avrebbe
intercettato in un minuto, e che invece sono stati trovati settimane dopo, dal vivo.

Dal 2026-08-02 esiste `evals/`: fixture in stato dichiarato, asserzioni su filesystem e git,
`--selfcheck` senza modello nel giro. Il primo bench ha dato 8/8 contro 4/8 sul baseline. Lo
strumento c'è; questa decisione lo rende la condizione per promuovere.

## 2. Decisione

1. **Ogni `SKILL.md` porta `version:` nel frontmatter**, indipendente dal pacchetto e da ogni altra
   skill. Tutte partono da **`v1.0.0` oggi**: la storia precedente non è ricostruibile per-skill e
   fingere di numerarla a ritroso sarebbe inventare.
2. **Scala fissa**, tarata su cosa una modifica può rompere per chi la usa:
   - **MAJOR** — una regola cambia verso, un default si inverte, uno step obbligatorio sparisce, o
     cambia il contratto verso l'esterno (path scritti, argomenti di uno script). Chi si affidava al
     comportamento precedente deve saperlo.
   - **MINOR** — nuovo step, nuova capacità, nuovo guardrail. Aggiunge senza ribaltare.
   - **PATCH** — riformulazione che non può cambiare comportamento: refusi, esempi, formattazione.
3. **`version:` è l'etichetta leggibile, `computedHash` in `skills-lock.json` è la verità.** Un numero
   scritto a mano diverge come ogni altra cosa scritta a mano; l'hash dice se questa copia è quella
   pinnata. Dove i due si contraddicono, vince l'hash e la divergenza va segnalata.
4. **Gate di promozione — nessuna modifica si rilascia senza il suo caso rosso.** L'eval richiesto
   dipende da cosa hai toccato, perché in una skill la prosa È il codice:
   - hai toccato la **`description:`** → eval di trigger (`skill-creator/scripts/run_eval.py`): la
     skill parte dove deve e non parte dove non deve.
   - hai toccato il **corpo** → eval comportamentale (`evals/run_behavior.py`): fixture in
     stato dichiarato, asserzioni su filesystem e git.
   - hai toccato **entrambi** → entrambi.
   - **PATCH** dichiarato tale: il selfcheck dell'harness basta, ma se un caso esistente diventa rosso
     non era un PATCH — e la classificazione era sbagliata, non il test.
5. **Il caso deve essere rosso PRIMA.** Ogni caso dichiara `fails_before`: la versione su cui deve
   fallire. Un caso verde prima e dopo non misura la modifica, misura sé stesso. Girare nuova e
   baseline **sullo stesso fixture** è ciò che rende il risultato un confronto invece di
   un'affermazione.
6. **Le asserzioni che non discriminano si dichiarano tali.** Nel primo bench 4 su 8 passavano su
   entrambe le versioni: restano utili come guardie di regressione, ma contarle come prova del
   cambiamento gonfia il risultato. Il benchmark le etichetta.

## 3. Alternative valutate

- **Versione unica di pacchetto (lo stato precedente).** Semplice, un numero solo. Scartata: non
  discrimina quale skill è cambiata, ed è il difetto che ha reso invisibile la divergenza a tre vie.
- **Solo hash, niente `version:`.** Rigoroso — l'hash è già la verità. Scartata: un hash non è
  leggibile in un log di eval né in una segnalazione di bug, e la domanda "che versione stai usando"
  resta senza risposta pronunciabile.
- **Data invece di semver** (`2026-08-02`). Coerente con la convenzione ADR. Scartata qui: la data
  dice *quando*, non *quanto rompe* — e per chi consuma una skill la seconda informazione è quella
  che serve.
- **Eval obbligatorio su ogni modifica, PATCH incluso.** Più rigido. Scartata: un refuso che paga un
  run completo è la frizione che fa smettere di usare il metodo — lo stesso motivo per cui l'ADR non
  è obbligatorio su ogni scelta. La classificazione PATCH è però falsificabile (punto 4).

## 4. Cosa NON decide

- Non decide **dove vivono** le skill (globale contro per-repo): decisione aperta, altro ADR.
- Non decide la **distribuzione** (`npx skills` primario, plugin come comodità Claude Code): già
  deciso il 2026-07-19, questa vi si appoggia.
- Non copre le skill **fuori** da questo pacchetto: le 337 installate hanno provenienze diverse e non
  sono nostre da versionare.
- Non impone un eval alle skill di sola conoscenza (nessun effetto su disco): lì il trigger è
  l'unica cosa misurabile, e il punto 4 lo dice già.

## 5. Conseguenze

**Accettiamo** che modificare una skill costi un giro di eval (~70k token per caso, misurato) e che
serva una fixture per ogni comportamento nuovo. **Otteniamo** che una modifica sia dimostrata invece
che affermata, che il numero dica cosa è cambiato in cosa, e che una regressione fallisca un caso
nominato invece di emergere dal vivo settimane dopo.

Il costo cade dove serve: sulle modifiche che cambiano comportamento, non sui refusi.

## 6. Come si falsifica

- Se fra un mese ci sono skill modificate **senza** bump di versione, il campo non è manutenibile a
  mano e va derivato (dall'hash, o da un hook) invece che scritto.
- Se i casi passano sempre al primo colpo, sono scritti **dopo** la modifica per confermarla: il
  `fails_before` va verificato eseguendolo davvero sul baseline, non dichiarato.
- Se il gate viene aggirato con "è solo un PATCH" su modifiche che cambiano comportamento, la scala
  non regge e serve un criterio meno interpretabile.
- Se il costo dell'eval blocca modifiche utili, la soglia è troppo alta: si riduce il numero di casi
  per giro, non il principio.
