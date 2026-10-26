## In una riga

Il preventivo in PDF ora si apre con l'intestazione completa del committente (nome, indirizzo, codice fiscale o P.IVA), fotografata nel momento in cui lo si sceglie. Verdetto del real-test: **mergeabile con un gap**, e con **una migrazione da applicare in produzione prima del deploy**.

Chiude #1719, #1207, #792.

## Cosa cambia per l'Impresa

**1. L'intestazione sul PDF (#1719).** Prima, sotto «SPETT.LE» c'era solo il nome. Ora:

```
SPETT.LE

BK1719 Zeta Edile Srl
Via Roma 9
36100 Vicenza (VI)
P.IVA 01234567897
```

Per un condominio con amministratore:

```
SPETT.LE

BK1719 Condominio Ciliegi
c.a. Amministratore Studio BK1719 Verd
Via dei Ciliegi 3
31100 Treviso (TV)
C.F. 02345678904
```

- I dati sono una **fotografia presa quando si sceglie il committente**. Se poi si modifica la scheda del committente, il PDF già emesso non cambia; si riaggiorna scegliendo di nuovo lo stesso committente o con «Completa».
- Se manca un dato fiscale compare un promemoria nell'app («Dati da completare: … · Completa») che **non blocca mai** il PDF.
- Il titolo del preventivo usa il giorno in italiano.
- Sul PDF non c'è nulla di tecnico né il disclaimer AI.

**2. Errore di download (#1207).** Se la generazione del PDF, dell'XLSX o del CSV fallisce, l'Impresa vede **una frase in italiano** e non più il testo inglese dell'eccezione. L'eccezione va nel registro errori.

**3. Segnalazioni di errore dal frontend (#792).** Il frontend mandava un corpo che il server rifiutava con 422: nessuna segnalazione è mai arrivata. Ora il server risponde 204.

**4. Piccoli ritocchi.** Messaggio del controllo P.IVA riscritto in modo più chiaro; scegliere con Invio un nome che esiste due volte non sceglie più nessuno dei due.

## Cosa ha trovato il test reale, e cosa è stato corretto

Due revisori indipendenti (contesto pulito) hanno provato la versione su staging con un account di prova, senza validare nulla.

Difetti del primo giro, tutti corretti e riprovati dal secondo revisore:
- «Completo» compariva con 5 secondi di ritardo dopo il salvataggio; ora 74 ms.
- «Annulla» richiedeva due clic quando la lista dei suggerimenti era aperta (nell'editor e nella finestra PDF); ora ne basta uno.
- Un amministratore aggiunto alla scheda del condominio dopo il collegamento non arrivava al PDF; ora scegliere di nuovo lo stesso committente rifotografa i dati.
- Errore di download in inglese e segnalazioni 422: vedi sopra.

Verificato su staging: intestazione per azienda, privato e condominio; passando da committente A a B non escono mai i dati di A; omonimi; telefono 390×844 senza scorrimento orizzontale.

Schermate (a fine sezione i file completi stanno in `.real-test/evidence/1942-ad76031ae/`):
- [«Completo» subito dopo la creazione](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/04-theta-dopo-crea.jpg?raw=true)
- [Cambia con lista aperta](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/05-cambia-lista-aperta.jpg?raw=true) e [dopo un clic su Annulla](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/06-dopo-un-click-annulla.jpg?raw=true)
- [Due nomi uguali + Invio: nessuno scelto](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/27-omonimi-enter.jpg?raw=true)
- [Finestra PDF con lista aperta](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/32-dialog-pdf-lista-aperta.jpg?raw=true) e [chiusa con un clic](https://github.com/acme/acme-api/blob/e45cbbe099fb5a28845c6067fd0e9a29d6d5cdc5/.real-test/evidence/1942-ad76031ae/33-dialog-pdf-dopo-un-click-annulla.jpg?raw=true)

## Il gap noto

Su staging, durante 502 e risposte da 6-10 secondi, **una volta su due** il primo PDF scaricato subito dopo aver scelto di nuovo lo stesso committente ha stampato la vecchia fotografia (la seconda prova è passata). Sul backend del branch, in locale, 5 cicli su 5 danno l'intestazione nuova, e il PDF legge proprio quel campo: l'ipotesi è che sia l'instabilità di staging, ma non è dimostrato. Effetto pratico: in rari casi si può dover riscaricare il PDF. I rami d'errore di `ritorno.ts` e `quote_committente.py:126` sono coperti solo da test unitari, non provati dal vivo.

## Cosa NON è stato fatto

- Nessun confronto affiancato con 4 computi reali dell'Impresa pilota (richiesto dall'issue #1719 come verifica avversariale).
- La ditta individuale non è stata percorsa su staging (privato, azienda, condominio sì).
- Non è stato verificato il collegamento a /impostazioni accanto al messaggio «manca la P.IVA» (richiesto da #1207).
- Il testo del promemoria è «Dati da completare: … · Completa», non «Manca la P.IVA · Aggiungi» come scritto nell'issue.

## Prima di mergiare e deployare

1. **Migrazione `20261018100000`**: aggiunge una colonna (`quotes.committente_intestazione`, nullable) ed è applicata su staging, **non ancora in produzione**. Un main deployato in produzione senza la colonna **rompe ogni scelta del committente** (la scrittura usa la colonna). Va applicata in produzione prima del deploy.
2. Il controllo `supabase-migrations-check` è rosso, ma lo era già prima di questa PR: staging ha 4 migrazioni di altre lane che non sono su main.
3. **Da controllare, non spiegato qui:** il confronto con main mostra anche circa 4.400 righe di documentazione cancellate nell'area prezzario multiregione (ADR del database multiregione, manifest Puglia/Toscana, validazioni Lombardia/Piemonte) e modifiche a HOT/README/ROADMAP. Non c'entrano con il committente. Se non sono volute, il branch va riallineato a main prima del merge.
4. Contiene anche la release v6.4.0 (registro versioni e nota): registra #1878, #1892, #1728, già in produzione. Prod serve oggi `4dd343db9`; dopo ci sono su main altri cambi (#1934, #1930, #1937, #1938, #1941): elencarli prima di promuovere.

## Prove

- CI verde: backend (4 shard), frontend (4 shard), lint, tsc.
- Test visti rossi prima della correzione: export in errore con frase italiana e log (PDF, XLSX, CSV); segnalazione errori 422→204; Invio con due nomi uguali; «Annulla» a un clic; «Completo» senza ricaricare. Per #1719 i test di intestazione, migrazione e giorno del titolo (backend 333, frontend 2240) sono verdi.
- Real-test: `/health` e marcatore dell'anteprima su `ad76031ae`; l'ultimo commit (`e45cbbe09`) aggiunge solo file di prova. Ricevuta nel commento della PR, verdetto MERGEABLE-CON-GAP.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_018Mn6wYKp5aaZQt3TNdEdRj
