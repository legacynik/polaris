---
title: polaris-sweep — i bypass-test
description: Un caso per difetto, con fails_before e output del PRIMA (il bypass riesce) e del DOPO (il bypass fallisce). Il revisore su cui poggia l'auto-merge non può essere l'unico pezzo del loop senza casi rossi.
status: active
---

# Bypass-test di `polaris-sweep`

Regola: il caso si scrive **prima** del codice, e deve **riuscire** (SPEC-MADRE, Fase 2).

Il PRIMA dei tre casi è lo stesso ed è stato eseguito il 2026-08-17 su polaris-sweep
senza versione (407r di prosa):

```bash
python3 polaris-sweep/scripts/sweep_gate.py automerge ... 
# can't open file '.../scripts/sweep_gate.py': [Errno 2] No such file or directory → exit 2
```

**Nessuno script esisteva**: Phase 4.5 era prosa, quindi qualunque verdetto scritto bene
autorizzava l'auto-merge. L'evidenza sul campo è il run-state REALE
`_polaris/sweep/runs/acme-app/pr-59.md` (2026-05-01): dichiara `auto_mergeable: true`
**senza** `head_sha`, senza `attestazione`, senza `risk` nel frontmatter.

---

## B1 — verdetto approve su codice mai eseguito (test che non provano nulla)

`fails_before:` `polaris-sweep` senza versione (pre-1.0.0)

Una review statica eccellente su una PR mai fatta girare da nessuna parte: le tre lenti leggono,
nessuna esegue. PRIMA: il blocco Auto-mergeable dipendeva solo dalla prosa della Phase 4.5.

**DOPO** — eseguito 2026-08-17 su v1.0.0 (dal selfcheck, ramo B1):

```
NEGATO: attestazione 'non-attestata': questo codice non e' mai stato eseguito da nessuna parte — real test prima del merge
exit=1
```

`attestazione: non-deployabile` (doc-only) resta PASS: l'attestazione non è richiesta dove non
c'è runtime da provare.

## B2 — la PR tocca la pipeline e si approva da sola

`fails_before:` `polaris-sweep` senza versione (pre-1.0.0)

Una PR che modifica `.github/workflows/`, i gate della suite o il contratto `.fix/contract.yml`
può alterare esattamente i controlli che dovrebbero fermarla. PRIMA: nessun controllo sui path.

**DOPO** — eseguito 2026-08-17 su v1.0.0 (selfcheck, ramo B2):

```
NEGATO: la PR tocca la pipeline (.github/workflows/ci.yml): il gate non approva chi modifica il gate — merge umano
exit=1
```

## B3 — verdetto emesso su una SHA diversa da HEAD

`fails_before:` `polaris-sweep` senza versione (pre-1.0.0)

La sweep approva, poi la PR riceve altri commit: il commento resta, il verdetto pure — e vale per
un codice che non esiste più. PRIMA: il run-state non registrava nemmeno la SHA (vedi `pr-59.md`).

**DOPO** — eseguito 2026-08-17 su v1.0.0, contro il run-state reale pre-v1:

```bash
python3 scripts/sweep_gate.py automerge --run _polaris/sweep/runs/acme-app/pr-59.md \
  --pr-head deadbeef123 --files files-59.txt
NEGATO: campo 'head_sha' assente o vuoto nel run-state: senza, il verdetto non e' legato a niente
NEGATO: campo 'attestazione' assente o vuoto nel run-state: senza, il verdetto non e' legato a niente
NEGATO: campo 'risk' assente o vuoto nel run-state: senza, il verdetto non e' legato a niente
exit=1
```

E col campo presente ma stale (selfcheck, ramo B3):

```
NEGATO: verdetto emesso su aaa111 ma la PR e' a bbb222: STALE — la revisione ha letto un codice che non esiste piu'
exit=1
```

---

## B4 — PR fuori dal perimetro prod bloccata dal requisito risk:trivial

`fails_before:` `polaris-sweep v1.0.0` — difetto INVERSO ai primi tre: over-blocking.
Decisione founder 2026-08-17: *«PR che non toccano pipeline o prod vengono SEMPRE auto-mergiate»*.
La v1.0.0 chiedeva `risk:trivial` + attestazione a TUTTE le PR — anche una doc-only restava in
coda al founder, che è esattamente il collo di bottiglia che il loop esiste per togliere.

Setup: run-state `verdict: approve · head_sha: aaa111 · attestazione: non-attestata ·
risk: medium` · diff = `docs/README.md, tests/test_x.py` · contratto con
`deployabili: [src/*, app/*]`.

**PRIMA** — eseguito 2026-08-17 su v1.0.0 (script da `git show`):

```
NEGATO: risk 'medium': solo risk:trivial si fonde da solo
NEGATO: attestazione 'non-attestata': questo codice non e' mai stato eseguito da nessuna parte — real test prima del merge
exit=1
```

**DOPO** — stesso comando su v1.1.0 (con `--repo` che dichiara il perimetro): `exit=0`.

I contro-rami che restano NEGATI (selfcheck 18/18): stesso diff ma dentro `deployabili` →
via stretta · perimetro **non dichiarato** → via stretta (non si indovina cosa è prod) ·
pipeline nel diff → NEGATO sempre, il perimetro non lo salva.

---

## Selfcheck

```bash
python3 scripts/sweep_gate.py --selfcheck ; echo "exit=$?"
```

18 controlli, tutti `ok`, `exit=0` — eseguito 2026-08-17 (13 di v1.0.0 + 5 del perimetro prod).
Rami dell'ignoranza inclusi: run-state assente/vuoto → 2, file-list assente/vuota → NEGATO,
placeholder `.` → NEGATO, perimetro non dichiarato → via stretta. Mai PASS al buio.
