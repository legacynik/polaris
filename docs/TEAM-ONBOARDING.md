# Polaris Team OS — onboarding reale per un team

Questo documento serve a una persona che apre una repo prodotto per la prima volta. Se un comando
qui sotto non passa, fermati e segnala il blocco: non creare un vault personale e non improvvisare
una seconda configurazione.

## 1. Installa il plugin Polaris

`legacynik/polaris` è il marketplace pubblico del plugin. Il plugin contiene solo workflow:
non inserire qui dati di progetto, decisioni private, clienti o stato della repo operativa. Poi,
in Claude Code:

```text
/plugin marketplace add legacynik/polaris
/plugin install polaris-team-os@polaris-team-os
```

Riavvia Claude Code, poi verifica:

```bash
claude plugin list
```

Devi vedere `polaris-team-os@polaris-team-os` abilitato.

## 2. Preflight strumenti — una volta per macchina

### Superpowers

Polaris non sostituisce Superpowers: lo usa per pianificazione e delivery quando il lavoro richiede
codice. Installa/verifica il plugin ufficiale:

```text
/plugin install superpowers@claude-plugins-official
```

Poi controlla con `claude plugin list`. Se il marketplace ufficiale non è disponibile nella tua
installazione, chiedi al maintainer il comando del marketplace configurato: non indovinare un ID.

### Context7

Context7 serve per documentazione aggiornata di SDK e librerie:

```text
/plugin install context7@claude-plugins-official
```

### MCP del plugin

Polaris dichiara Sequential Thinking e Codebase Memory; Context7 arriva dal plugin ufficiale
installato sopra. Dopo il riavvio verifica lo stato reale, non solo la presenza del file:

```bash
claude mcp list
```

Devono risultare connessi o avere un motivo esplicito.

Per `codebase-memory` serve anche il binario `codebase-memory-mcp`. Se `claude mcp list` lo segnala
come mancante, installalo con il gestore Python della tua macchina (per esempio
`pipx install codebase-memory-mcp`), poi ripeti `claude mcp list`. Non salvare chiavi o credenziali
nella repo.

## 3. Rendi `polmem` disponibile nella tua shell

`polmem` è la CLI di memoria della repo: fa `recall` su ciò che la repo già sa (decisioni,
reference, architettura, journal committati in `.wiki/`). **La CLI è l'interfaccia che usi tu.**
Polaris dichiara anche un adattatore MCP, ma è opzionale: la CLI è il percorso affidabile.

Installa il launcher una volta per macchina (lo aggiunge a `~/.local/bin/polmem`, indipendente
dalla versione del plugin):

```bash
bash "$CLAUDE_PLUGIN_ROOT/polaris/scripts/install-polmem-cli.sh"
```

Se lo script segnala che `~/.local/bin` non è sul PATH, aggiungi al tuo profilo di shell:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

Poi, da dentro una repo prodotto wired a memoria, verifica:

```bash
polmem health
polmem recall "confirmation gate"
```

`recall` restituisce voci ordinate — punteggio, path sorgente, titolo, riassunto di una riga:

```text
$ polmem recall "confirmation gate" --top 3
[70] _polaris/decisions.md#2026-05-07 — Production runtime = ECS Fargate + Terraform …
[70] references/cardaq-gateway-integration — Cardaq Gateway Integration …
[70] synthesis/orbit-adversarial-gate-framework — Orbit Producer/Validator/Gate Framework …
```

I tre comandi del primo giorno: `polmem recall "<query>"`, `polmem health`,
`polmem remember "<nota breve>"`. Se `recall` dice che la repo non è wired, fai `git pull`
(il `.wiki` è committato e arriva col codice). Serve `python3`. `polmem` legge solo la repo in cui
lo esegui.

## 4. Verifica il contratto della repo

La repo possiede **una sola** root: `polaris/` oppure `_polaris/`. Deve contenere:

```text
<root>/config.yml
<root>/team/<tuo-github-login>/profile.yml
<root>/team/<tuo-github-login>/weeks/
<root>/team/<tuo-github-login>/reports/
<root>/sessions/
<root>/decisions.md
```

Se manca il profilo o la root, chiedi al repository owner. Non eseguire bootstrap e non creare una
cartella Polaris personale.

## 5. Primo giorno

1. Apri Claude Code dalla repo prodotto.
2. Esegui `/start` e leggi outcome, proof, blocker e ownership altrui.
3. Prima di proporre un branch, controlla il tuo piano e il lavoro già attivo.
4. Usa `/update` dopo un avanzamento o un blocco reale.
5. Usa `/end` quando chiudi: lascia una prossima azione concreta.

## 6. Settimana

- Il CEO o il responsabile usa `/plan-week` per una proposta basata su issue/PR reali e capacità.
- Una proposta CEO con `ceo_signature: pending` **non autorizza lavoro**.
- Dopo firma, ogni persona mantiene il proprio piano nella repo.
- A fine settimana `/report` confronta piano e realtà: consegne, prove, blocchi e prossima priorità.

### Esempio minimo

```md
# Week 2026-W29 — @niccolo

## Outcome
Rendere verificabile il confirmation gate, con prova staging.

| Issue | Stato | Prova |
|---|---|---|
| #573 | in revisione | PR + test staging |

## Non iniziare
- Nuove feature finché #573 non è verificabile.
```

Il report non conta messaggi o token: dice cosa era previsto, cosa è stato davvero consegnato e che
cosa serve per chiudere il resto.
