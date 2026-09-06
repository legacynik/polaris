---
title: tdd-dev — i bypass-test
description: Un caso per difetto. Ognuno dichiara fails_before e riporta l'output del PRIMA (il bypass riesce) e del DOPO (il bypass fallisce). Un gate senza il suo bypass rosso è una dichiarazione, non un gate.
status: active
---

# Bypass-test di `tdd-dev`

Regola: il caso si scrive **prima** del codice, e deve **riuscire**. Se non riesce, il difetto che
stavi per curare non esiste — ci si ferma (SPEC-MADRE, Fase 2).

---

## B1 — la CLI `record` è inagibile: collisione argparse su `dest="cmd"`

`fails_before:` `tdd-red v0.1.0` — bug confermato 2 volte in run indipendenti dell'eval sul campo
(`docs/skill-refactor/2026-08-16-bugfix-eval/VERDICT.md`, R6): entrambi i bracci suite l'hanno
aggirato importando il modulo, e un loop non presidiato si sarebbe fermato lì.

Il difetto: `add_subparsers(dest="cmd")` e l'opzione `--cmd` del subparser `record` scrivono sullo
**stesso** attributo `a.cmd`. Il valore di `--cmd` sovrascrive il nome del subcomando, `main()` non
riconosce più `record` e stampa l'help. Il selfcheck era verde perché chiama `cmd_record()` con un
`Namespace` costruito a mano, bypassando `main()` — il ramo malato non era mai percorso.

Setup:

```bash
cd "$(mktemp -d)" && printf 'def test_x():\n    assert False\n' > t.py
```

Comando:

```bash
python3 <suite>/tdd-dev/scripts/red_check.py record \
  --test t.py::test_x --cmd "/usr/bin/false" --out r.jsonl; echo "EXIT=$?"; ls r.jsonl
```

**Atteso PRIMA** — il bypass RIESCE: nessun run registrato, la skill è inagibile da CLI.

```
usage: red_check.py [-h] [--selfcheck] {record,verify} ...
...
EXIT=2
nessun log scritto
```

Eseguito 2026-08-17 su v0.1.0: output identico a sopra (`print_help`, `EXIT=2`, `r.jsonl` assente).

**Atteso DOPO** — lo stesso identico comando registra il run:

```
ROSSO exit=1 -> r.jsonl
EXIT=0
r.jsonl
```

**DOPO** — eseguito 2026-08-17 su v1.0.0:

```
ROSSO exit=1 -> r.jsonl
EXIT=0
r.jsonl
```

Detection permanente: il selfcheck ora esercita anche il path CLI (`main()` via subprocess), non
solo le funzioni importate — la classe di bug «selfcheck che bypassa l'entry point» non può più
nascondersi lì. Mutazione eseguita 2026-08-17: rimesso `dest="cmd"` → selfcheck esce **1** (il
ramo B1 scatta) · ripristinato il fix → esce **0**.

---

## B2 — targeted GREEN can claim handoff without durable regression evidence

`fails_before:` `tdd-dev v2.0.0` pre-merge. The blind grader found a RED/GREEN JSONL and an agent
claim that `pytest` had passed, but no durable proof connecting that suite run to the cycle. The
new core contract therefore remained unproved.

The test was added first to `red_check.py --selfcheck`:

```text
FAIL handoff senza suite registrata -> FAIL
exit=1
```

After the minimum fix, `suite` appends the authoritative command and exit code to the same JSONL;
final `verify --suite-cmd` rejects a missing, failing, mismatched, or pre-GREEN entry.

```text
ok   handoff senza suite registrata -> FAIL
ok   suite registrata ma rossa -> FAIL
ok   suite verde prima del GREEN mirato -> FAIL
ok   suite diversa da quella dichiarata -> FAIL
ok   rosso, verde e suite successiva registrati -> PASS handoff
ok   CLI 'suite' registra l'evidenza autoritativa
```

Detection permanente: `python3 scripts/red_check.py --selfcheck` exercises both CLI paths and the
complete RED→GREEN→suite receipt.
