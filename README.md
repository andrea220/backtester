
# 📊 Backtesting Data Structure

Questa documentazione descrive la struttura dei dati utilizzata per una libreria di backtesting finanziario ad alte prestazioni. I dati sono salvati in formato **Parquet** e organizzati per **ticker**, **anno**, **mese** e **giorno**, con supporto sia per dati **intraday** (1 minuto) che per dati **End Of Day (EOD)**.

---

## 📁 Struttura delle directory


## 🧾 Contenuto dei file `prices/{ticker}/{year}/{day}.parquet`

Ogni file contiene dati a 1 minuto e un record EOD per la giornata.

### Colonne:
- `timestamp`: datetime (UTC)
- `open`: prezzo di apertura
- `high`: prezzo massimo
- `low`: prezzo minimo
- `close`: prezzo di chiusura
- `volume`: volume scambiato
- `type`: `"intraday"` oppure `"eod"`

---

## 📄 File `dividends/{ticker}.parquet`

Contiene i dividendi storici per ciascun titolo.

### Colonne:
- `ex_date`
- `amount`
- `currency`
- `payment_date`

---

## 🏢 File `corporate_actions/{ticker}.parquet`

Contiene eventi societari come split, reverse split, spin-off, ecc.

### Colonne:
- `date`
- `type`
- `ratio`
- `notes`

---

## 🧠 File `metadata/tickers_info.parquet`

Contiene informazioni statiche sui titoli.

### Colonne:
- `ticker`
- `name`
- `isin`
- `sector`
- `exchange`

---

## ✅ Vantaggi

- Accesso veloce e selettivo ai dati
- Struttura scalabile e modulare
- Supporto per analisi miste intraday/EOD
- Compatibilità con Polars e Pandas