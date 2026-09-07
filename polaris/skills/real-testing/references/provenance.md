---
title: real-test — provenienza (ADATTA, zero verbatim)
description: Da dove viene ogni pezzo del meccanismo, e cosa e' stato corretto rispetto alla fonte. Nessun testo esterno copiato — solo meccanismi, riscritti.
status: active
---

# Provenienza

`real-test` **ADATTA** la dottrina gia' installata `real-testing` (v1.1.0, `~/.claude/skills/real-testing`
→ `~/dev/polaris-plugin/polaris/skills/real-testing/SKILL.md`, 227 righe). Quella dottrina e' gia'
piu' granulare di ogni fonte esterna minata (tassonomia a 10 classi, nessuna delle 8 fonti C-* ce
l'ha) — il gap non era dottrina, era enforcement: *"la dottrina non e' agganciata a un hook che la
rende obbligatoria"* (SUITE-disegno.md, job 8). Questo pacchetto aggiunge SOLO quell'aggancio:

| Pezzo | Preso da | Cosa e' stato corretto/aggiunto, non copiato |
|---|---|---|
| Hook `PreToolUse` keyed sul content-hash | `parallel-issue-flow/scripts/gates/preCommitGate.sh` | Il donatore estrae `tool_name`/`command` con `sed -nE 's/.../\s.../'` — `\s` e' un'estensione GNU **assente nel sed BSD di macOS**: il match fallisce sempre, `tool_name` resta vuoto, il gate e' **sempre allow** (riprodotto io stesso: `EXIT: 0` invece di `2`, stesso esito di CRITIC-1 §1 riga 12). `gate.sh` qui parsa SOLO con `python3 -c "import json"` — mai regex su JSON. |
| Ancora il perimetro a un commit reale, mai "a voce" | BMAD (`quick-dev`, `baseline_commit` catturato a inizio sessione) | Non e' prosa qui: e' l'hash-albero (`git write-tree` / `<ref>^{tree}`) scritto DENTRO il verdetto e ricalcolato ad ogni `validate` — non un numero che l'agente promette di aver notato. |
| Fixture materializzate in repo git usa-e-getta, traccia giudicata | `anthropic/agent-skills` (osmani), Tier 3 eval | Il pattern e' lo stesso principio (mai una directory finta, mai solo il diff finale) — qui si applica al `references/bypass-test.md` di QUESTA skill: 5 tentativi di aggiramento su un repo `git init` reale, ognuno con l'exit-code atteso verificato, non narrato. |
| Matrice a 10 classi | `real-testing` v1.1.0 (nostra, gia' installata) | Riportata quasi identica (e' gia' nostra, non esterna — zero vincolo anti-verbatim), ma resa STRUTTURALE: prima era una tabella da compilare a mano nella testa dell'agente, ora e' un JSON che `verdict.py` valida riga per riga. |
| Rank/soglia mai-abbassabile (ratchet) | `anthropic/agent-skills` Tier 2 (menzionato, non riusato qui) | **Non applicato**: real-test non ha un punteggio continuo da alzare, ha un verdetto a 3 stati binario per riga. Il pattern e' del job `skill-meta` (16), non di questo. Dichiarato per onestà, non per uso. |

## Confine dichiarato con `flow-cli` (job 7)

`real-test` **riceve** la CLI di `flow-cli` come substrato per il livello 2 della scala
("CLI/modulo reale" — vedi `matrix-classes.md`). `flow-cli` non e' stato costruito in questo
pacchetto (CRITIC-1 §5.3: nessun report ha mai aperto `printing-press/SKILL.md` riga per riga,
il gap resta aperto). La convenzione di manifest attesa (`.flow-cli/manifest.json`) e' una
**assunzione dichiarata**, non un contratto verificato — quando `flow-cli` esiste, verificare che
la convenzione combaci e correggere `matrix-classes.md` di conseguenza.

## Perché pesa meno della donatrice migliore

`real-testing` (donatrice) = 227 righe di SOLO `SKILL.md`, zero `scripts/`, zero `references/` —
zero meccanismo, tutta prosa. `real-test` (qui): `SKILL.md` sotto le 227 righe (vedi header del
file), e l'enforcement (perimeter.py + verdict.py + gate.sh + install-hook.sh, ~650 righe totali)
vive in `scripts/` — **fuori dal contesto per costruzione** (si eseguono, non si leggono). Il
costo di contesto reale (cio' che conta per il PRD) e' piu' basso, non piu' alto: la donatrice
faceva leggere 227 righe di prosa ad ogni invocazione senza mai verificare nulla; qui la stessa
dottrina compressa si legge, e la verifica gira fuori dal contesto.
