---
title: bypass-test — issue-contract
description: I test che DEVONO fallire (exit != 0) se qualcuno aggira il gate di build_issue.py.
status: active
---

# Bypass-test

Il gate è `scripts/build_issue.py`. Vale blindato solo se **non esiste un modo di ottenere un
comando `gh issue create` (o un brief locale) senza aver soddisfatto DoD misurabile + campi
richiesti dal template reale**. I test sotto coprono i modi misurati in cui le 4 repo del
founder bypassano oggi un template che pure esiste (acme-api 91,8% freeform, acme-web 0/708 con label
di default).

## Test 1 — acceptance criteria non misurabile deve bloccare

```bash
cd issue-contract
D=$(mktemp -d) && mkdir -p "$D/.github/ISSUE_TEMPLATE"
cat > "$D/.github/ISSUE_TEMPLATE/config.yml" <<'EOF'
blank_issues_enabled: false
EOF
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "va bene, ci penso"
echo "exit=$?"   # DEVE essere 2, non 0
```

**Cosa proverebbe un bypass**: se questo esce `0`, il gate accetta un criterio non verificabile
("va bene" — la classe di fallimento che il PRD nomina esplicitamente, "piani/issue senza spina
dorsale") e il gate è decorativo.

## Test 2 — campo `required: true` del template reale non compilato deve bloccare

Stesso `$D` di sopra:

```bash
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "\`GET /x\` returns 200"
echo "exit=$?"   # DEVE essere 2 — manca il campo acceptance-criteria compilato via --field
```

`build_issue.py` mappa `--ac` sull'alias `acceptance`/`criteria` (vedi `FIELD_ALIASES`), quindi
questo test in realtà PASSA (`--ac` riempie da solo il campo). Per forzare davvero il buco, usa un
template con un campo che NON ha alias noto (es. `id: security-gate-triage`, misurato reale su
acme-web `feat-medium.yml`):

```bash
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
  - type: textarea
    id: security-gate-triage
    attributes: {label: Security-gate triage}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "\`GET /x\` returns 200"
echo "exit=$?"   # DEVE essere 2 — security-gate-triage non ha alias e non è stato passato
```

**Cosa proverebbe un bypass**: se questo esce `0`, il gate genera un'issue che manca un campo che
il template della repo dichiara obbligatorio — la stessa forma di G2 (gate `required` ma
strutturale) che il registro misura sulle 4 repo, riprodotta qui.

## Test 3 — tipo senza match + `blank_issues_enabled: false` non deve cadere sul freeform

```bash
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type nonexistent-type --title "x" --ac "\`GET /x\` returns 200"
echo "exit=$?"   # DEVE essere 2, mai 0 con un gh-command silenzioso senza template
```

**Cosa proverebbe un bypass**: se questo esce `0` e produce comunque un comando `gh issue
create`, lo script ha ignorato la dichiarazione esplicita della repo ("niente issue vuote") — è
esattamente il fatto misurato che GitHub stesso applica quel flag SOLO alla UI web, mai a `gh`/API:
se noi non lo applichiamo qui, nessuno lo applica mai.

## Test 4 — `--field` vuoto/solo-spazi su un campo required non deve passare

Il Test 2 copre solo "campo non passato". Trovato reale in EVAL-issue-contract-copertura.md §3.2
(Bypass B): un `--field id=` presente ma vuoto veniva accettato come "compilato" perché il
controllo era "la chiave c'è nel dict", non "il valore ha contenuto".

```bash
cd issue-contract
D=$(mktemp -d) && mkdir -p "$D/.github/ISSUE_TEMPLATE"
cat > "$D/.github/ISSUE_TEMPLATE/config.yml" <<'EOF'
blank_issues_enabled: false
EOF
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
  - type: textarea
    id: repro
    attributes: {label: Repro steps}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" --ac "\`GET /x\` returns 200" --field "repro="
echo "exit=$?"   # DEVE essere 2, non 0
```

**Cosa proverebbe un bypass**: se questo esce `0`, l'issue nasce con una sezione "Repro steps"
vuota che il template dichiara obbligatoria — esattamente ciò che Test 2 dovrebbe già impedire,
solo con un input leggermente diverso (vuoto invece di assente).

## Test 5 — un singolo segnale cosmetico nell'AC non deve bastare

Trovato reale in EVAL-issue-contract-copertura.md §3.2 (Bypass A): il regex originale accettava
qualunque cifra/backtick/keyword isolata, anche dentro prosa vaga identica a "va bene, ci penso"
(Test 1, che blocca).

```bash
for ac in "lo sistemiamo entro il 2026, ci penso io" \
          "faccio un test e vedo come va" \
          'sistemare `quella cosa` prima possibile'; do
  python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
    --type bug --title "Fix it" --ac "$ac" --refresh
  echo "exit=$?"   # DEVE essere 2 per tutte e tre — 0 segnali di sostanza, solo cosmesi
done
```

**Cosa proverebbe un bypass**: se una qualunque delle tre esce `0`, il gate misurabilità distingue
"contiene una cifra/parola a caso" da "contiene un criterio verificabile" solo sulla carta.

## Test 6 — `--field` non deve poter sovrascrivere il campo Acceptance Criteria già validato

Trovato reale in EVAL-issue-contract-bypass.md Laterale A (gravità alta): se l'id del campo AC
del template combacia anche con un `--field`, il valore scritto nell'issue era quello di
`--field`, mai passato da `validate_acs()` — un `--ac` misurabile passava il gate, ma il corpo
finale conteneva un altro testo, mai validato.

```bash
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api \
  --type bug --title "Fix it" \
  --ac "\`GET /x\` returns 200" \
  --field acceptance-criteria="va bene, ci penso, chissene" --refresh
echo "exit=$?"   # DEVE essere 2 — non deve MAI scrivere "va bene, ci penso" nel corpo
```

**Cosa proverebbe un bypass**: se questo esce `0`, il corpo dell'issue contiene testualmente una
stringa non misurabile mentre `validate_acs()` ha approvato tutt'altro — il valore validato e il
valore spedito sono due cose diverse, il gate protegge un dato che non è quello che esce.

## Test 7 — la chiamata diretta alla funzione deve essere gated quanto la CLI

Trovato nel corpus (buco generale, EVAL-issue-contract-bypass.md Laterale C): uno script con
`main()`/`build()` gated ma funzioni di modulo pubbliche senza guardia lascia un import diretto
libero di produrre lo stesso output vietato, senza mai passare da `validate_acs()`.

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import build_issue as bi
template = {'file':'bug.yml','fields':[{'id':'acceptance-criteria','label':'Acceptance criteria','required':True}],'labels':['bug']}
body, missing = bi.compile_form(template, {'acs': ['va bene, ci penso'], 'scope_out':'', 'summary':''}, {})
assert body is None and missing, 'BYPASS: import diretto ha prodotto un body senza passare dal gate'
print('PASS: compile_form() rifiuta esattamente come la CLI')
"
```

**Cosa proverebbe un bypass**: se `body` non è `None`, esiste un modo di ottenere il corpo
dell'issue senza mai validare l'AC — la CLI diventa un pass-through opzionale, non l'unico modo.

## Test 8 — Epic con titolo duplicato deve bloccare senza `--ack-existing`

F10/G7#6: un Epic la cui DoD/titolo ricalca uno già aperto deve essere rifiutato finché non lo
si conferma esplicitamente. Verificato a livello di `apply_gate()` (unit, non attraverso
`--apply` reale — nessuna rete in questo test):

```bash
python3 -c "
import sys, json; sys.path.insert(0, 'scripts')
import build_issue as bi
from argparse import Namespace
def dup(_a): return json.dumps([{'number': 5, 'title': 'Epic dup', 'state': 'OPEN', 'url': 'https://x/5'}])
ns = Namespace(type='epic', slug='acme/api', title='Dup epic', ack_existing=False)
msg = bi.apply_gate(ns, dup)
assert msg is not None, 'BYPASS: Epic duplicato creato senza --ack-existing'
print('PASS:', msg.splitlines()[0])
"
```

**Cosa proverebbe un bypass**: se `apply_gate` ritorna `None` con un duplicato trovato, l'Epic
si crea comunque — esattamente il buco G7#6 nomina ("DoD che si sovrappone a capacità già
esistenti").

## B9 — issue senza elenco di test adversarial deve bloccare

fails_before: issue-contract v1.0.0 (contratto founder 2026-08-16: la lista di verifiche
adversarial si scrive PRIMA dell'implementazione, si esegue prima di merge/deploy)

```bash
cd issue-contract
D=$(mktemp -d) && mkdir -p "$D/.github/ISSUE_TEMPLATE"
cat > "$D/.github/ISSUE_TEMPLATE/bug.yml" <<'EOF'
name: Bug report
labels: ["bug"]
body:
  - type: textarea
    id: acceptance-criteria
    attributes: {label: Acceptance criteria}
    validations: {required: true}
EOF
python3 scripts/build_issue.py --repo-path "$D" --repo-slug acme/api --type bug \
  --title "Login 500s on empty password" \
  --ac '`POST /login` with empty password returns 400, not 500' --refresh
echo "exit=$?"
```

**Atteso PRIMA (v1.0.0)**: exit `0` — il bypass RIESCE. Output osservato 2026-08-16:
`DRY-RUN ... template: bug.yml ... exit=0`.
**Atteso DOPO**: exit `2` con messaggio che nomina gli adversarial tests mancanti
(`--adv-test`, almeno 2, ciascuno misurabile).
**Osservato DOPO (v1.1.0, 2026-08-16)**: exit `2` — `BLOCKED — issue contract / template fields: adversarial tests (B9): >=2 required, written BEFORE the work starts (--adv-test ...)`.

## B10 — issue senza executive summary (italiano semplice) deve bloccare

fails_before: issue-contract v1.0.0. Stesso comando di B9.

**Atteso PRIMA (v1.0.0)**: exit `0` — osservato 2026-08-16 (stesso run di B9).
**Atteso DOPO**: exit `2` con messaggio che chiede `--exec` (spiegazione semplice per il
founder, senza gergo tecnico).
**Osservato DOPO (v1.1.0, 2026-08-16)**: exit `2` — `executive summary (B10): --exec with a plain-language explanation (italiano semplice, >=20 chars)`.

## B11 — duplicato NON-epic deve bloccare a --apply senza --ack-existing

fails_before: issue-contract v1.0.0 (apply_gate era scoped ai soli epic).

```bash
python3 -c "
import sys, json; sys.path.insert(0, 'scripts')
import build_issue as bi
from argparse import Namespace
def dup(_a): return json.dumps([{'number': 7, 'title': 'Login 500s on empty password', 'state': 'OPEN', 'url': 'https://x/7'}])
ns = Namespace(type='bug', slug='acme/api', title='Login 500s on empty password', ack_existing=False)
print('apply_gate =', bi.apply_gate(ns, dup))
"
```

**Atteso PRIMA (v1.0.0)**: `apply_gate = None` — il duplicato bug passa. Osservato 2026-08-16.
**Atteso DOPO**: `apply_gate` ritorna il messaggio BLOCCATO con la lista dei candidati, per
OGNI tipo, non solo epic.
**Osservato DOPO (v1.1.0, 2026-08-16)**: `apply_gate = BLOCKED — F10/G7#6/B11: possible duplicate issue(s): #7 ...` su type=bug.

## B12 — issue senza label di dominio architetturale deve bloccare

fails_before: issue-contract v1.0.0. Stesso comando di B9.

**Atteso PRIMA (v1.0.0)**: exit `0` — osservato 2026-08-16 (stesso run di B9); il comando
`gh` prodotto porta solo `--label bug`, nessun `domain:*`.
**Atteso DOPO**: exit `2` senza `--domain`; con `--domain` il comando `gh` porta
`domain:<valore>`; se la repo ha un glossario (`.github/DOMAINS.yml` o `CONTEXT.md`, il
contratto della porta `domain`), un dominio fuori glossario blocca con la lista dei validi.
**Osservato DOPO (v1.1.0, 2026-08-16)**: exit `2` senza `--domain`; col contratto pieno il comando gh porta `--label bug,domain:auth,p1`.

## B13 — issue senza priorità deve bloccare

fails_before: issue-contract v1.0.0. Stesso comando di B9.

**Atteso PRIMA (v1.0.0)**: exit `0` — osservato 2026-08-16 (stesso run di B9).
**Atteso DOPO**: exit `2` senza `--priority`; accettato solo `p0|p1|p2|p3`, reso come label.
**Osservato DOPO (v1.1.0, 2026-08-16)**: exit `2` — `priority (B13): --priority p0|p1|p2|p3`.

## B14 — il dedup deve essere VISIBILE nella issue, non solo eseguito

fails_before: issue-contract v1.1.0 (blind judge 2026-08-16: R4 dedup 0/6 — anche i run CON la
skill facevano la ricerca ma la issue non ne portava traccia).

Comando: lo stesso di B9 con il contratto pieno (adv-test, exec, domain, priority) ma senza
`--dedup`.

**Atteso PRIMA (v1.1.0)**: exit `0` — osservato 2026-08-16.
**Osservato DOPO (v1.2.0, 2026-08-16)**: exit `2` — `dedup evidence (B14): --dedup "Searched:
<where/query>. Found: <none|#N>"`. Anche la forma senza Searched/Found ("ho controllato,
fidati") blocca. Limite onesto ereditato da triage/check_redundancy: prova la FORMA della
ricerca e la rende visibile, mai la sua verità.

## B15 — un riferimento inventato deve bloccare (anti-fabbricazione)

fails_before: issue-contract v1.2.0 (blind judge 2026-08-16: epic con numeri e path mai
verificati sul codice, «un template compilato con numeri finti è peggio di un documento
disordinato che dice la verità»).

Comando: contratto pieno con `--ac '\`compute_margin()\` in src/billing/margin_engine.py
returns 48.00, not 42.00'` su un repo dove quel file NON esiste.

**Atteso PRIMA (v1.2.0)**: exit `0` — osservato 2026-08-16.
**Osservato DOPO (v2.0.0)**: exit `2` — `unverified reference (B15): 'src/billing/margin_engine.py'
not found in the repo — verify it against the code (Serena) or mark the item '(new)'`.
Il marker `(new)` nell'item dichiara un file che nascerà (TDD: il test è rosso-prima) e passa.
Senza repo_root (import diretto) il check è fail-closed, non saltato.

## B16 — l'idoneità AFK va dichiarata alla nascita, sempre

fails_before: issue-contract v1.2.0 (founder 2026-08-16: «mi genero 200 issue, il 60% sono
AFK ma nessuno si ricorda di metterlo perché c'è un'altra skill a parte, dimenticata»).

Comando: contratto pieno senza `--afk`.

**Atteso PRIMA (v1.2.0)**: exit `0` — osservato 2026-08-16.
**Osservato DOPO (v2.0.0)**: exit `2` — `AFK eligibility (B16): --afk yes|no`. Con `--afk yes`
il comando gh porta la label `afk:eligible` (ciò che il poller autonomo pesca); con `--afk no`
porta `afk:human`. Fuori vocabolario (`--afk boh`) blocca.

## Caso B1 del piano (DoD narrativa) — difetto INESISTENTE, riportato

Il piano 2026-08-16-skill-issue-unica prevedeva B1 «DoD narrativa oggi passa». Falso già in
v1.0.0: Test 1 + Test 5 sopra la bloccano (`validate_acs`, ≥2 segnali indipendenti). Per la
regola GATE 2 della SPEC-MADRE il caso non si «cura»: è già coperto, lo si dichiara.

## Esecuzione automatica

I rami sopra (Tests 1-8 + B9-B16) sono anche dentro `scripts/build_issue.py --selfcheck` (fixture in-memory,
zero rete, zero mutazione reale, redundancy-gate testato via `apply_gate()` diretto — mai
attraverso `--apply` reale) — gira in <1s, nessun `gh` invocato:

```bash
python3 scripts/build_issue.py --selfcheck
python3 scripts/parse_template.py --selfcheck
```

Se uno dei due esce diverso da 0, il gate stesso è rotto — non solo aggirabile.

## Limite noto, non chiudibile da questo script

Nessuno dei test sopra copre — perché non può — un `gh issue create` freeform, una chiamata API
diretta o la UI web di GitHub: bypassano interamente questo script, senza toccarlo. Vedi
"Cosa questo gate NON può impedire" in `SKILL.md`. Non è un bypass di QUESTO gate (non passa
da qui), è il limite strutturale di ogni gate che vive in uno script invece che in un hook —
dichiarato qui perché un bypass-test che tacesse su questo lascerebbe intendere una copertura
più ampia di quella reale.
