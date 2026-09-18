---
title: bugfix — i bypass-test del gate per-tappa
description: Un caso per gate. Ognuno dichiara fails_before e riporta l'output del PRIMA (il bypass riesce) e del DOPO (il bypass fallisce). Un gate senza il suo bypass rosso è una dichiarazione, non un gate.
status: active
---

# Bypass-test di `bugfix` (gate per-tappa, ex `fix-gate`)

B1–B4 sono nati sotto `fix-gate` v0.1.0, assorbita in `bugfix` il 2026-08-17 (ADR porta-unica:
il gate del workflow vive NEL workflow). I comandi valgono invariati con
`bugfix/scripts/fix_gate.py`.

Regola: il caso si scrive **prima** del codice, e deve **riuscire**. Se non riesce, il difetto che
stavi per curare non esiste — ci si ferma (SPEC-MADRE, Fase 2).

---

## B1 — record senza dominio né classe

`fails_before:` `fix-gate v0` (nessuno script esisteva)

```bash
printf -- '---\nid: t\nrepo: r\nstato: aperto\n---\n' > /tmp/b1.md
python3 scripts/fix_gate.py check --stage ingresso --record /tmp/b1.md --repo . ; echo "exit=$?"
```

**PRIMA** — nessun gate esiste, quindi non c'è niente che fermi un record incompleto:

```
zsh: command not found: fix_gate.py     → exit=127, il record passa
```

**DOPO** — eseguito 2026-08-11 su `fix-gate v0.1.0`:

```
FAIL: campi mancanti o vuoti nel record: dominio, classe, cecita, sorgente
exit=1
```

---

## B2 — valore-placeholder che soddisfa il controllo di presenza

`fails_before:` `fix-gate v0.1.0-pre` (prima variante, controllava solo che la chiave ci fosse)

È il bypass che ha già colpito questa suite: `piano-spec` accettava `deadline: .` e `serves: .`
senza nemmeno stampare un warning.

```bash
printf -- '---\nid: t\nrepo: r\ndominio: .\nclasse: logica\ncecita: bassa\nsorgente: log\nstato: aperto\n---\n' > /tmp/b2.md
python3 scripts/fix_gate.py check --stage ingresso --record /tmp/b2.md --repo <repo-con-contratto> ; echo "exit=$?"
```

**PRIMA** — `dominio` c'è, quindi il controllo di presenza passa: `exit=0`.

**DOPO** — coperto dal selfcheck (riga «valore-placeholder '.' -> FAIL»), verificato 2026-08-11:

```
FAIL: campi mancanti o vuoti nel record: dominio
exit=1
```

I valori trattati come assenti: `` (vuoto) · `.` · `-` · `--` · `?` · `tbd` · `todo` · `n/a` ·
`na` · `none` · `null` · `<>`.

---

## B3 — contratto assente, controllo disattivato in silenzio

`fails_before:` `fix-gate v0.1.0-pre`

Il caso peggiore, e il più facile da scrivere per sbaglio: se il contratto manca, `dominii` è
`None`, e un controllo scritto come «se c'è la lista, verifica» **salta senza dire niente** — il
record passa. È la forma canonica di G2: il gate approva quando non sa decidere.

```bash
mkdir -p /tmp/repo-senza-contratto
python3 scripts/fix_gate.py check --stage ingresso --record <record-valido> --repo /tmp/repo-senza-contratto ; echo "exit=$?"
```

**PRIMA** — `exit=0`: nessun vocabolario, nessun controllo, nessun messaggio.

**DOPO** — coperto dal selfcheck (riga «contratto assente -> FAIL, mai PASS silenzioso»),
verificato 2026-08-11:

```
FAIL: contratto senza 'dominii': il vocabolario di dominio non si improvvisa
      (atteso in <repo>/.fix/contract.yml)
exit=1
```

---

## B4 — stage non implementato che passa

`fails_before:` `fix-gate v0.1.0-pre`

Chiedere una tappa che non esiste ancora non deve produrre un PASS: sarebbe un modo di saltare
l'intero workflow scrivendo un nome sbagliato.

```bash
python3 scripts/fix_gate.py check --stage riproduzione --record <record-valido> --repo <repo> ; echo "exit=$?"
```

**DOPO** — verificato 2026-08-11:

```
stage sconosciuto: riproduzione (noti: ingresso)
exit=2
```

`2` è errore d'uso e **blocca**, come `1`. Le tappe successive arrivano con le slice T2..T8: finché
non esistono, non si passa da lì per sbaglio.

---

## B5 — test orfano: committato ma mai raccolto dalla CI

`fails_before:` `bugfix v0.1.0` (nessuna tappa controllava il raccolto)

È R5 dell'eval sul campo (`docs/skill-refactor/2026-08-16-bugfix-eval/VERDICT.md`): il braccio
suite su Acme-quotes #876 ha committato un test nuovo che **nessun workflow CI referenzia** — la fase ④
si è chiusa su un test che protegge solo chi lo lancia a mano. Il legacy aveva il raccolto già nel
subset di `ci.yml`.

Setup:

```bash
cd "$(mktemp -d)" && mkdir -p .fix tests
printf 'def test_orfano():\n    assert True\n' > tests/test_orfano.py
printf 'def test_altro():\n    assert True\n'  > tests/test_altro.py
printf -- '---\nid: t1\nrepo: r\ndominio: auth\nclasse: logica\ncecita: bassa\nsorgente: issue\nstato: fixato\ntest: tests/test_orfano.py::test_orfano\n---\n' > rec.md
printf 'dominii: [auth]\nci.collect: python3 -m pytest --collect-only -q tests/test_altro.py\n' > .fix/contract.yml
```

Comando:

```bash
python3 <bugfix>/scripts/fix_gate.py check --stage raccolto --record rec.md --repo . ; echo "exit=$?"
```

**PRIMA** — eseguito 2026-08-17 su v0.1.0: la tappa non esiste, il test orfano attraversa l'intero
workflow senza che niente lo fermi:

```
stage sconosciuto: raccolto (noti: causa, deposito, firma, ingresso, mutazione, prod, raggio, realtest, riproduzione, rosso, verde)
exit=2
```

(`2` blocca la chiamata esplicita, ma il difetto è l'assenza: nessuna delle 11 tappe controllava il
raccolto, e sul campo il record è passato — R5.)

**DOPO** — eseguito 2026-08-17 su v1.0.0. Il subset della CI raccoglie ma non contiene il test:

```
FAIL: test ORFANO: tests/test_orfano.py::test_orfano non e' raccolto da 'ci.collect' — committato, ma la CI non lo eseguira' mai
exit=1
```

Con `ci.collect` puntato al subset che lo contiene: `exit=0`. Raccolta che fallisce (path
inesistente, pytest exit 4): `FAIL: la raccolta CI fallisce (exit 4)` — mai PASS silenzioso.

---

## B6 — thrashing: il quarto tentativo di fix invece di questionare l'architettura

`fails_before:` `bugfix v1.0.0` — donatrice: superpowers `systematic-debugging` («3+ failed
fixes → STOP, question the architecture»), censimento donatori 2026-08-17.

Setup: `rosso_log` con **4 run rossi** dello stesso test e poi un verde; contratto con
`test.suite: /usr/bin/true`.
Comando: `fix_gate.py check --stage verde --record rec.md --repo .`

**PRIMA** (v1.0.0, eseguito 2026-08-17): `exit=0` — la suite passa e nessuno conta i tentativi:
il fix n.4 procede identico al n.1.

**DOPO** (v1.1.0, stesso comando):
```
FAIL: CIRCUIT BREAKER: >=4 run rossi dello stesso test — 3+ fix falliti non chiedono il fix n.4,
chiedono di questionare l'architettura. Dichiara 'architettura_riesaminata: <cosa hai concluso>' per procedere
exit=1
```
Con `architettura_riesaminata:` dichiarato → PASS (escape esplicito, mai silenzioso).
2 run (1 rosso + 1 verde) → nessun breaker.

## B7 — chiamanti elencati a memoria, mai prodotti da un comando

`fails_before:` `bugfix v1.0.0` — donatrice: `bug-protocol` (incidente #107: fix al sito
primario coi chiamanti mai guardati = fix muto, spedito silenzioso).

Comando: `check --stage raggio` su record con `chiamanti: [f_a, f_b]` + assi issue dichiarati,
**senza** `chiamanti_cmd`.

**PRIMA** (v1.0.0): `exit=0` — bastava che la lista esistesse.
**DOPO** (v1.1.0): `FAIL: 'chiamanti_cmd' assente: i chiamanti si PROVANO col comando che li ha
prodotti` · `exit=1`. `chiamanti: [nessuno]` resta PASS senza comando (lo zero si dichiara).

## B8 — indagine partita senza consultare l'archivio bug

`fails_before:` `bugfix v1.0.0` — donatrice: acme-web `backend-debug` (ricerca attiva di recidiva
per modulo+eccezione: «may be a RECURRING bug — check if the previous fix regressed»).

Comando: `check --stage causa` su record con `causa_in: path:riga` valido, **senza** campo
`ricorrenza`.

**PRIMA** (v1.0.0): `exit=0` — la triade pattern/prevention/detection era storage passivo.
**DOPO** (v1.1.0): `FAIL: 'ricorrenza' assente: l'archivio bug si interroga PRIMA di indagare` ·
`exit=1`. Placeholder `.` → FAIL; `ricorrenza: 0 match in archivio` → il controllo passa.

---

## B9 — grep spacciato per prova del raggio

`fails_before:` `bugfix v1.1.0` — trovato dal founder a caldo («il raggio si vede con Serena
graph, sempre»): B7 pretendeva UN comando, ma `chiamanti_cmd: grep -rn compute_price backend/`
passava — e grep trova testo, non riferimenti.

**PRIMA** (v1.1.0, eseguito 2026-08-17): `exit=0`.
**DOPO** (v1.1.1, stesso comando): `FAIL: 'chiamanti_cmd' non e' un verbo del code-graph … il
raggio si vede col graph (Serena), MAI a grep` · `exit=1`. Con
`chiamanti_cmd: find_referencing_symbols compute_price` → `exit=0`. Verbi accettati:
find_referencing_symbols/find_symbol/find_implementations/find_declaration/trace_path/
references/call_hierarchy.

---

## B10 — fail-open del `verde`: `cd x && suite` eseguiva `/usr/bin/cd`, exit 0, zero test

`fails_before:` `bugfix v1.1.1` — trovato dal **validatore sul campo** (eval Acme-quotes #771,
2026-08-17): il contratto reale diceva `cd backend && PYTHONPATH=... pytest`; `shlex.split`
senza shell lo trasformava in argv `["cd","backend","&&",...]` → su macOS `/usr/bin/cd` esiste,
ignora gli argomenti ed **esce 0**: la suite non girava MAI e `verde` passava. Il peggior
fallimento possibile per un gate che si dichiara fail-closed.

Setup: contratto con `test.suite: cd <dir> && /usr/bin/false` (comando che DEVE fallire).
Comando: `fix_gate.py check --stage verde --record rec.md --repo .`

**PRIMA** (v1.1.1, eseguito 2026-08-17): `exit=0` — fail-open.
**DOPO** (v1.1.2, stesso comando): `FAIL: la suite non passa (exit 1)` · `exit=1`.

Fix: i comandi del CONTRATTO girano con la shell (`_sh`, fiducia = Makefile del repo) su tutte
le tappe che eseguono (`riproduzione`, `verde`, `raccolto`, `prod`) + guardia sul **127**: un
comando non trovato non è mai né un rosso né una riproduzione — è errore, detto forte. Stesso
fix in `red_check.py` di tdd-red (che registrava VERDE farlocco sullo stesso pattern), più il
difetto C: `record` su file di test irrisolvibile ora è errore d'uso SUBITO, non un
`file_sha: assente` silenzioso che affiora solo al verify.

---

## Selfcheck — la prova che i rami dell'ignoranza sono coperti

```bash
python3 scripts/fix_gate.py --selfcheck ; echo "exit=$?"
```

**76 controlli**, tutti `ok`, `exit=0` — rieseguito 2026-08-17 dopo B6-B8 (11 rami nuovi:
breaker/thrashing, chiamanti provati, ricorrenza). I rami dell'ignoranza — record assente, record
vuoto, contratto assente, comando di raccolta inesistente, placeholder — non escono mai 0. Un
selfcheck che prova solo il caso felice è una promessa, non una prova.
