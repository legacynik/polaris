# polaris-status — iteration 1 (state health gate)

Baseline = versione pre-modifica (git HEAD, 197 righe, nessuno step di salute).
Nuova    = con Step 5b.0 (243 righe).

## Risultati

| caso | asserzione | nuova | baseline | discrimina? |
|---|---|---|---|---|
| quiet (5 thread, 3 blocchi)  | DID_INVESTIGATE = no    | ✓ no  | ✗ **sì**  | **SÌ** |
| quiet                        | dichiara "healthy"      | ✓ sì  | ✗ no      | **SÌ** |
| quiet                        | thread invariati (5)    | ✓     | ✓         | no — guardia |
| quiet                        | blocchi invariati (3)   | ✓     | ✓         | no — guardia |
| alarm (14 thread, 25 blocchi)| ASKED_USER = sì         | ✓ sì  | ✗ **no**  | **SÌ** |
| alarm                        | riporta 14 e 25         | ✓     | ✗ solo 14 | **SÌ** |
| alarm                        | thread invariati (14)   | ✓     | ✓         | no — guardia |
| alarm                        | blocchi invariati (25)  | ✓     | ✓         | no — guardia |

pass_rate nuova: 8/8 · baseline: 4/8 (tutte e 4 guardie di sicurezza)

## Costo

| run | token | durata | tool |
|---|---:|---:|---:|
| quiet nuova    | 68.134 | 73s  | 10 |
| quiet baseline | 73.424 | 113s | 10 |
| alarm nuova    | 72.536 | 89s  | 8  |
| alarm baseline | 78.578 | 165s | 10 |

Delta: -5.3k token / -40s (quiet) · -6.0k token / -76s (alarm).

## Osservazioni dell'analista

1. **4 asserzioni su 8 non discriminano** ("non tocca", "non ruota"): passano su entrambe le
   versioni. Restano utili come guardie di regressione ma NON provano il cambiamento. Le 4 che
   discriminano sono DID_INVESTIGATE, "healthy", ASKED_USER, e il report di entrambi i conteggi.
2. **Il fixture sottostima il risparmio.** Nessun remote, nessuna issue, nessun repo prodotto: il
   baseline ha "indagato" quasi a vuoto. Sul vault reale (11 thread con riferimenti #N da risolvere
   via gh, più i subagent per repo) il divario atteso è di un altro ordine. Il numero è reale ma non
   è il numero che conta.
3. **Il baseline non ha disobbedito**: senza gate di salute, indagare ERA il comportamento prescritto.
   Il delta misura una modifica di contratto, non un errore del modello.
4. **Il raggruppamento per repo regge**: nel caso alarm la nuova ha dichiarato 1 subagent per 14
   thread (tutti su `acme`), non 14. Era il rischio dichiarato quando l'istruzione è stata scritta.
5. **Gap del fixture da chiudere nella iterazione 2**: thread su repo DIVERSI (per provare il
   raggruppamento con N>1), e riferimenti #N reali (per provare la risoluzione via gh).
