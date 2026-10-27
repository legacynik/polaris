# Run transcript — issue-contract 2.5.0 (baseline), 2026-10-25

Agent: fresh context, a fast model, dry run (no gh, bd or python). Given the skill at 2.5.0 and
`request.md`. Reply verbatim below.

---

**Title**

Deploy: aggiungere `--dry-run` a deploy.sh e un timeout di 300 secondi

**Labels**

`agent-ready`, `deploy` (la seconda solo se esiste già tra le label del repository; altrimenti solo `agent-ready`)

**Body**

```markdown
Oggi il deploy non si può provare senza toccare nulla, e quando si pianta non scade mai. Servono due cose: una modalità di prova (`--dry-run`) per `deploy.sh` e un timeout esplicito in `config.yml`.

## DoD
- `deploy.sh` accetta il flag `--dry-run`. In quella modalità il deploy gira in prova e non modifica nulla.
- La logica della modalità di prova sta in una funzione chiamata `run_dry`.
- `config.yml` contiene `DEPLOY_TIMEOUT: 300` (secondi), così un deploy che si pianta scade dopo 300 secondi invece di restare appeso.
- Senza `--dry-run` il deploy si comporta come prima.

## Come si prova
- `deploy.sh` contiene `--dry-run`.
- In `deploy.sh` esiste la funzione `run_dry`.
- `config.yml` contiene `DEPLOY_TIMEOUT: 300`.
- Da preservare: l'esecuzione di `deploy.sh` senza flag resta invariata.
```
