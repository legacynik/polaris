# bypass-test — critic

Ogni caso è riproducibile con un comando. Il criterio è uno: **prima della porta passava, adesso
deve fallire.** I casi 1-3 sono i tre fallimenti misurati sul campo, non ipotesi.

```bash
mkdir -p /tmp/critic-artifact
printf 'actual artifact line\n' > /tmp/critic-artifact/a.md
```

## Il baseline che questi casi riproducono

Tre run identiche di Opus nudo sullo stesso artefatto (una riga di censimento skill), 2026-08-21,
prompt identico e nessun suggerimento di formato. Tutte e tre hanno trovato i difetti reali. Nessuna
ha superato i casi qui sotto.

## Caso 1 — commento senza rendiconto (0/3 lo superavano)

Un report con finding veri e nessun `ledger`: il critico non dice cosa ha aperto né cosa ha
accettato sulla fiducia.

```bash
cat > /tmp/bypass-1.json <<'JSON'
{"artifact":"census-row","contract":"row must match the file it measures",
 "findings":[{"claim":"the row describes a file it does not measure","severity":"important",
 "evidence":{"path":"plan-eng-review/SKILL.md","line":1015,"quote":"Read sections/review-sections.md"}}]}
JSON
python3 scripts/critic_gate.py --validate /tmp/bypass-1.json   # atteso: exit 1, "ledger: missing"
```

## Caso 2 — finding plausibile mai falsificato (3/3 lo producevano)

Ledger completo, citazione presente, ma nessun contro-argomento tentato. È la forma esatta delle tre
run nude.

```bash
python3 - <<'PY' > /tmp/bypass-2.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"minor","contract_quote":"c","evidence":{"path":"a.md","line":1,"quote":"actual artifact line"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-2.json   # atteso: exit 1, "falsification: missing"
```

## Caso 3 — finding non citato, declassato invece che scartato

È il difetto **verificato nel donatore**: la skill donatrice forza un finding non citato a confidenza `4-5`
dichiarandolo soppresso, ma la sua tabella mostra `5-6` «con caveat», quindi un finding a 5 arriva
comunque all'utente. Qui non esiste banda.

```bash
python3 - <<'PY' > /tmp/bypass-3.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"critical","contract_quote":"c","evidence":{"path":"a.md","line":1,"quote":"  "},
   "falsification":{"counter":"maybe fine","survived":True,"why":"checked"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-3.json   # atteso: exit 1, "unquoted is not a finding"
```

## Caso 4 — zero finding taciuti

«Sembra a posto» senza dirlo. È la scappatoia che la skill donatrice lascia aperta: tutti gli specialist possono
tornare `NO FINDINGS` e il run prosegue a `clean` senza che nessuno lo dichiari.

```bash
python3 - <<'PY' > /tmp/bypass-4.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-4.json   # atteso: exit 1, "zero findings must be declared"
```

Zero finding **dichiarati** invece passano, ed è voluto: `halt.reason` non vuoto → exit 0.

## Caso 5 — finding che non è sopravvissuto al proprio contro-argomento

Il critico tenta la falsificazione, il contro-argomento tiene, e riporta il finding lo stesso.

```bash
python3 - <<'PY' > /tmp/bypass-5.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"c","ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"minor","contract_quote":"c","evidence":{"path":"a.md","line":1,"quote":"actual artifact line"},
   "falsification":{"counter":"the section is inlined elsewhere","survived":False,"why":"and it is"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-5.json   # atteso: exit 1, "did not survive"
```

## Caso 6 — input illeggibile che non deve passare per verde

File assente, vuoto, o JSON rotto: **exit 2**, mai exit 0. Un gate che non sa leggere non approva.

```bash
python3 scripts/critic_gate.py --validate /tmp/does-not-exist.json   # atteso: exit 2, "UNUSABLE"
printf '   ' > /tmp/bypass-6.json && python3 scripts/critic_gate.py --validate /tmp/bypass-6.json
printf '{nope'  > /tmp/bypass-6.json && python3 scripts/critic_gate.py --validate /tmp/bypass-6.json
```

## Caso 7 — citazione o clausola contrattuale inventata

Il gate rilegge sia `evidence.path:line` sia `contract_quote`. Una frase plausibile ma assente
dall'artefatto o dal contratto deve fallire.

```bash
python3 - <<'PY' > /tmp/bypass-7.json
import json
r={"artifact":"/tmp/critic-artifact","contract":"must preserve the exact line",
   "ledger":{"opened":["a.md"],"not_opened":[],"accepted_unverified":[]},
   "findings":[{"claim":"x","severity":"important","contract_quote":"invented requirement",
   "evidence":{"path":"a.md","line":1,"quote":"invented artifact line"},
   "falsification":{"counter":"maybe present","survived":True,"why":"claimed"}}],"halt":None}
print(json.dumps(r))
PY
python3 scripts/critic_gate.py --validate /tmp/bypass-7.json   # exit 1, both quotes rejected
```

## B8 — artifact relativo risolto dalla cwd del chiamante

Il selfcheck scrive report e artifact insieme, poi invoca il gate da una cwd sorella vuota. La
versione precedente cerca `artifact/` nella cwd e fallisce; il gate corrente lo risolve dal report.

## Quello che questa porta NON blocca — dichiarato

- **Un ledger mentito.** `opened` può elencare un file che il critico non ha davvero letto: lo
  script verifica la presenza del campo, non la lettura. Chiudere questa metà richiede la
  strumentazione delle tool call, fuori dallo scope di un gate che decide in millisecondi.
- **Una falsificazione di facciata.** `counter` non vuoto e `survived: true` si scrivono anche
  senza aver pensato. Il gate impone che il passo esista e sia visibile a chi legge, non che sia
  stato fatto bene — quello lo giudica il T3, non uno script.
- **Provenienza runtime mentita.** Il gate verifica file e righe, non può provare che il modello
  abbia davvero eseguito le tool call dichiarate; il T3 fresco resta l'autorità su quel passaggio.

```bash
python3 scripts/critic_gate.py --selfcheck   # 24 rami, inclusi ignoranza e rilocazione
```
