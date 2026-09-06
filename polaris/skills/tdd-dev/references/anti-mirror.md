---
title: Anti-mirror — perché un test verde può non provare niente
description: I quattro modi in cui un test finisce per descrivere l'implementazione invece del contratto, con l'esempio di ognuno e la forma corretta. Si carica quando il test tocca liste di parole, regex, parser, o quando stai per scrivere le fixture a mano.
status: active
---

# Anti-mirror

Un test specchio è un test che descrive **come** il codice fa una cosa invece di **cosa** deve
succedere. Passa sempre, anche quando il codice è sbagliato, perché è stato scritto guardando il
codice.

Si riconosce da un sintomo solo: **cambiando l'implementazione senza cambiare il comportamento, il
test si rompe**. Se succede, il test stava misurando l'implementazione.

---

## 1. Fallisce per la ragione sbagliata

Il test fallisce, tu sei contento, e sta fallendo per un import.

```python
# rosso, ma per il motivo sbagliato
def test_counter_incrementa():
    from app.services.usage import increment   # ImportError: il modulo si chiama usage_repo
    ...
```

Il rosso c'è ma non prova il difetto. **Leggi sempre il messaggio d'errore del run rosso** e
verifica che nomini il comportamento, non il setup. Un rosso da `ImportError`, `fixture not found`
o `ConnectionError` è un rosso da buttare.

---

## 2. Specchia i rami del codice

```python
# il codice
def classifica(testo):
    if "urgente" in testo: return "P0"
    if "importante" in testo: return "P1"
    return "P2"

# il test SPECCHIO — stessi rami, stesso ordine, stesse parole
def test_classifica():
    assert classifica("urgente") == "P0"
    assert classifica("importante") == "P1"
    assert classifica("altro") == "P2"
```

Questo test passa **per costruzione**. Se domani qualcuno aggiunge `if "critico" in testo` e sbaglia
la priorità, il test resta verde. Non sta provando la classificazione: sta rileggendo il codice ad
alta voce.

La forma corretta parte dal **contratto osservabile** — cosa deve succedere per chi usa la funzione,
inclusi i casi che il codice non nomina:

```python
def test_classifica_da_corpus_reale():
    # casi presi da record veri, non inventati guardando i rami
    assert classifica("il cliente e' fermo, urgente") == "P0"
    assert classifica("bloccante per il rilascio") == "P0"   # NON contiene "urgente"
    assert classifica("quando avete tempo") == "P2"
```

La seconda riga è quella che vale: **usa una parola che nella lista non c'è**. Se il test passa
lo stesso, la lista è incompleta e nessuno se ne accorgerà.

---

## 3. Boundary test sui miss — la regola che trova le liste incomplete

Per qualunque cosa basata su una lista di parole, una regex o un match: **il test deve contenere
casi che la lista NON copre**, e deve fallire se la copertura è insufficiente.

```python
# insufficiente: prova solo ciò che è già dentro la lista
@pytest.mark.parametrize("q", ["prezzo", "costo", "tariffa"])
def test_riconosce_intento_prezzo(q):
    assert intento(q) == "prezzo"

# utile: prova i sinonimi FUORI dalla lista
@pytest.mark.parametrize("q", ["quanto viene", "quanto mi costa", "che cifra"])
def test_riconosce_intento_prezzo_anche_senza_keyword(q):
    assert intento(q) == "prezzo"
```

Il secondo test **oggi fallisce**, ed è giusto così: sta dicendo che il matching per keyword non
regge il linguaggio reale. È un rosso che significa qualcosa.

---

## 4. Fixture inventate invece di dati veri

Le fixture scritte a mano tendono a somigliare all'implementazione, perché le scrivi dopo averla
letta. Prendi almeno cinque casi da una fonte reale:

- i **record passati** con lo stesso `dominio` (`.fix/records/*.md`) — sono difetti veri già visti
- le **trace** di produzione, se il percorso le attraversa
- l'**eval corpus** del progetto, se esiste
- i **log di errore** che hanno originato il bug

Un caso vero porta con sé le sbavature che nessuno inventa: campi vuoti, unicode, ordini strani,
valori al limite. Quelle sbavature sono esattamente dove i bug vivono.

---

## La verifica finale, che vale più delle altre quattro

**Rimetti il difetto e rilancia.** Se il test resta verde, non prova niente — e adesso lo sai prima
di fidartene, invece che fra sei mesi.

```bash
python3 <bugfix>/scripts/mutation.py run \
  --repo . --fix-sha <sha-del-fix> --suite "<comando>" --out <mutation-log>
```

Esce **1** se la suite resta verde col bug rimesso. Quel `1` è la cosa più utile che riceverai
oggi.
