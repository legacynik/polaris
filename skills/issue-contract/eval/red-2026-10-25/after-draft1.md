# Run transcript — issue-contract 2.6.0 first draft, 2026-10-25 (failed c6 on timing)

Agent: fresh context, a fast model, dry run (no gh, bd or python). Same brief as `baseline.md`,
skill at the first 2.6.0 draft, whose SKILL.md line said only "or a timing". Reply verbatim below.

---

**Titolo**

Deploy: aggiungere `--dry-run` e un timeout, oggi il deploy si pianta e non scade mai

**Corpo**

```markdown
Oggi non si può provare un deploy senza toccare niente: ogni lancio di `deploy.sh` modifica davvero lo stato. In più il deploy a volte si pianta e non scade mai, quindi resta appeso senza che nessuno se ne accorga. Serve poter girare il deploy "in prova" e avere un tempo massimo oltre il quale il deploy fallisce invece di restare bloccato.

Lavoro per un agente.

## DoD
- `deploy.sh --dry-run` esegue il percorso del deploy mostrando cosa farebbe, senza modificare nulla (nessuna scrittura, nessun riavvio, nessun cambio di stato).
- Senza `--dry-run` il deploy si comporta come prima.
- Il limite di tempo del deploy è configurabile in `config.yml` come `DEPLOY_TIMEOUT`, con valore 300 secondi.
- Un deploy che si pianta termina con un errore esplicito e un codice di uscita diverso da zero, invece di restare bloccato.

## Come si prova
- Lanciare `deploy.sh --dry-run` su un ambiente di prova: vede l'elenco di ciò che verrebbe fatto, e dopo l'esecuzione lo stato dell'ambiente (file, servizi, versione in esecuzione) è identico a prima.
- Lanciare `deploy.sh` senza flag: il deploy avviene come prima, nessuna regressione.
- Simulare un passo del deploy che non termina mai: il deploy si interrompe da solo con un messaggio che indica il timeout e un codice di uscita diverso da zero, senza restare appeso.
- Caso limite: `--dry-run` combinato con un passo che si pianta non deve lasciare nulla di modificato.
```

**Etichette**

`agent-ready`
