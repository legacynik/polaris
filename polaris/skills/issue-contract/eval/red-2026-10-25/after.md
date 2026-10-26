# Run transcript — issue-contract 2.6.0 (this change), 2026-10-25

Agent: fresh context, a fast model, dry run (no gh, bd or python). Same brief as `baseline.md`,
skill at 2.6.0 as merged. Reply verbatim below.

---

**Titolo**

Deploy: modalità `--dry-run` e timeout di 300 secondi

**Body**

```markdown
Oggi `deploy.sh` non ha modo di essere provato senza toccare nulla, e quando il deploy si pianta non scade mai: resta appeso senza fallire. Servono due cose: un flag `--dry-run` in `deploy.sh` e `DEPLOY_TIMEOUT` a 300 secondi in `config.yml`.

## DoD
- `deploy.sh --dry-run` mostra cosa farebbe il deploy e non modifica nulla (nessun servizio toccato, nessuno stato cambiato), poi termina con successo.
- Un deploy che non finisce entro `DEPLOY_TIMEOUT` (300 secondi, definito in `config.yml`) viene interrotto e termina con errore, invece di restare appeso.
- Il deploy normale, senza flag, si comporta come prima.

## Come si prova
- Lancia `deploy.sh --dry-run`: l'output elenca i passi che eseguirebbe, il sistema resta identico a prima (nessuna modifica osservabile) e l'exit code è 0.
- Lancia `deploy.sh` senza flag su un caso che va a buon fine: si comporta come prima e non scatta alcun timeout.
- Simula un deploy che non termina abbassando temporaneamente `DEPLOY_TIMEOUT` a pochi secondi, senza aspettare i 300 reali: il deploy viene interrotto allo scadere e termina con exit code diverso da 0 e un messaggio di timeout.
- Un valore di timeout assente o non valido non deve lasciare il deploy senza limite in silenzio.
```

**Labels**

`agent-ready`
