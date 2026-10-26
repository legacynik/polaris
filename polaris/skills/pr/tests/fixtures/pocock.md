## Summary

Il PDF ora stampa sotto SPETT.LE il blocco completo del committente, fotografato quando lo scegli. Prima stampava solo il nome.

```diff
 SPETT.LE

 BK1719 Condominio Ciliegi
+c.a. Amministratore Studio BK1719 Verd
+Via dei Ciliegi 3
+31100 Treviso (TV)
+C.F. 02345678904
```

Se manca un dato fiscale, nell'app compare una riga «Dati da completare: … · Completa». Non blocca mai il PDF.

Dentro lo stesso giro (tornata di feedback) entrano anche:

```text
committenti
├── Enter con due nomi uguali      # non sceglie nessuno dei due
├── «Annulla»                      # un solo clic anche con la lista aperta
├── «Completo»                     # compare subito dopo il salvataggio
└── stesso committente riscelto    # riscatta la foto (serve all'amministratore del condominio)
download PDF/XLSX/CSV fallito      # una frase italiana, l'eccezione va in error_log (#1207)
segnalazioni errori dal frontend   # l'endpoint le accetta, prima 422 sempre (#792)
release                            # v6.4.0 registrata (#1878 #1892 #1728, già in prod)
```

## Evidence

- **Before:** PDF con solo il nome sotto SPETT.LE. «Annulla» richiedeva due clic con la lista aperta (il pulsante si spostava di 162 px). «Completo» appariva 5 s dopo il salvataggio. Un download fallito mostrava testo inglese dell'eccezione. Le segnalazioni errori del frontend ricevevano 422.
  **After:** blocco completo nel PDF per azienda, privato e condominio. «Annulla» a un clic, anche nella finestra del PDF. «Completo» 74 ms dopo la risposta di salvataggio. Una frase italiana al posto dell'eccezione. Segnalazioni errori: 422 diventa 204.

Test visti rossi prima della correzione, poi verdi:

```text
Enter con due nomi identici sceglie nessuno ......... FAIL -> PASS
«Annulla» un clic con lista aperta ................. FAIL -> PASS
«Completo» senza ricaricare, letture in attesa ..... FAIL -> PASS
export 500 (pdf, xlsx, csv): una frase + log ....... FAIL -> PASS
client-error con il corpo vero del frontend ........ 422 -> 204
```

Screenshot sul commit servito su staging:

- «Completo» subito dopo aver creato un'azienda: ![](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/04-theta-dopo-crea.jpg?raw=true)
- Lista aperta, prima del clic su «Annulla»: ![](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/05-cambia-lista-aperta.jpg?raw=true)
- Dopo un solo clic, editor chiuso: ![](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/06-dopo-un-click-annulla.jpg?raw=true)
- Due nomi uguali + Enter, non sceglie niente: ![](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/27-omonimi-enter.jpg?raw=true)
- Finestra PDF con lista aperta: ![](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/32-dialog-pdf-lista-aperta.jpg?raw=true)
- Finestra PDF chiusa con un clic: ![](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/33-dialog-pdf-dopo-un-click-annulla.jpg?raw=true)

Prova su staging: due breaker a contesto fresco, account `qa@example.com`, nulla validato. Il commit servito è `ad76031ae`. Il commit `e45cbbe09` aggiunge solo file di prove. Verdetto della ricevuta: **MERGEABLE-CON-GAP**. CI verde (backend 4 shard, frontend 4 shard, lint, tsc). `supabase-migrations-check` è rosso anche prima di questa PR, perché staging ha 4 migrazioni di altre lane che non sono su main.

**Cosa NON è stato fatto**

- Nessun confronto affiancato con 4 computi veri dell'impresa pilota (criterio della issue #1719, non soddisfatto).
- Ditta individuale non provata su staging (provati privato, azienda, condominio).
- Il link a `/impostazioni` accanto al messaggio «manca la P.IVA» (#1207) non è stato controllato.
- La riga di promemoria dice «Dati da completare: … · Completa», non «Manca la P.IVA · Aggiungi» come scritto nella issue.

**Gap aperto:** su staging, durante risposte 502 e da 6-10 s, il primo PDF subito dopo aver riscelto lo stesso committente ha stampato una volta la vecchia foto (1 caso su 2; il secondo era giusto). Sul backend del branch il meccanismo è deterministico: 5 cicli su 5 «modifica scheda, stessa scelta, lettura immediata» restituiscono l'intestazione nuova, e il PDF legge proprio quel campo. I rami di errore sono coperti solo da test unitari.

## Merge Danger

**Door:** two-way per il codice, ma con un ordine obbligato.

La migrazione `20261018100000` aggiunge una colonna facoltativa (`quotes.committente_intestazione`). È già applicata su staging, **non ancora su prod**. Se questo main va in prod senza la colonna, ogni scelta del committente si rompe, perché il salvataggio scrive in quella colonna. Prima la migrazione su prod (workflow), poi il deploy.

**Blast Radius:** Committenti

Tocca la scelta del committente nel preventivo, il PDF, i messaggi di errore di download e le segnalazioni errori. Prod oggi serve `4dd343db9`. Dopo, su main sono entrati #1934, #1930, #1937, #1938, #1941: il deploy porta anche quelli. Il diff mostra circa 3.300 righe di documenti `prezzario-multiregione` cancellate (HOT, ROADMAP, manifest Puglia e Toscana, due validazioni). Non fanno parte di questo lavoro: probabilmente il branch è indietro rispetto a main. Va verificato che sia aggiornato prima del merge, così non si cancella lavoro altrui.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_018Mn6wYKp5aaZQt3TNdEdRj
