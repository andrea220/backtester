

## Indice
- [Data Structure](#data-structure)  
- [Backtesting](#backtesting)  
- [Roadmap](#roadmap)  


## Data Structure

I dati sono salvati in formato **Parquet** e organizzati per **ticker**, **anno**, **mese** e **giorno**, con supporto sia per dati **intraday** (1 minuto) che per dati **End Of Day (EOD)**.

---

### 📁 Struttura delle directory

La cartella `data/` è organizzata nel modo seguente:

```text
data/
├── prices/
│   ├── AAPL/
│   │      └── 2025/
│   │          └── 07/
│   │              └── 01.parquet
│   └── MSFT/
│           └── 2025/
│               └── 07/
│                   └── 01.parquet
├── dividends/
│   ├── AAPL.parquet
│   └── MSFT.parquet
├── corporate_actions/
│   ├── AAPL.parquet
│   └── MSFT.parquet
└── metadata/
    └── tickers_info.parquet
```

### 🧾 Contenuto dei file `prices/{ticker}/{year}/{day}.parquet`

Ogni file contiene dati a 1 minuto e un record EOD per la giornata.

#### Colonne:
- `date`: data di riferimento
- `time`: time (UTC+2)
- `ticker`: ticker del sottostante
- `open`: prezzo di apertura
- `high`: prezzo massimo
- `low`: prezzo minimo
- `close`: prezzo di chiusura
- `volume`: volume scambiato
- `insertion_time`: timestamp di salvataggio
- `type`: `"intraday"` oppure `"eod"`

---

### 📄 File `dividends/{ticker}.parquet`

Contiene i dividendi storici per ciascun titolo.

#### Colonne:
- `ex_date`
- `amount`
- `currency`
- `payment_date`

---

### 🏢 File `corporate_actions/{ticker}.parquet`

Contiene eventi societari come split, reverse split, spin-off, ecc.

#### Colonne:
- `date`
- `type`
- `ratio`
- `notes`

---

### 🧠 File `metadata/tickers_info.parquet`

Contiene informazioni statiche sui titoli.

#### Colonne:
- `ticker`
- `name`
- `isin`
- `sector`
- `exchange`

---

## Backtesting
TBD

## Roadmap
- Data Structure
    - creazione ETL da Polygon
- Backtester
    - creazione script che legge tutti i file prices/{ticker}/{year}/{day}.parquet dell'universo, aggrega i dati per giorno e salva un file cache/daily_snapshots/{year}/{month}/{day}.parquet
    - backtester intraday e daily
