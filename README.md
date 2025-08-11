

## Indice
- [Data Structure](#data-structure)  
- [Backtesting](#backtesting)  
- [Roadmap](#roadmap)  


## Data Structure

I dati sono salvati in formato **Parquet** e organizzati per **ticker**, **anno**, **mese** e **giorno**, con supporto sia per dati **intraday** (1 minuto) che per dati **End Of Day (EOD)**.

---

### 📁 Struttura delle directory

La cartella `data/` è organizzata così:

```text
data/
├── prices/
│   ├── AAPL/
│   │   ├── 2024.parquet
│   │   └── 2025.parquet
│   └── MSFT/
│       └── 2025.parquet
├── dividends/
│   ├── AAPL.parquet
│   └── MSFT.parquet
├── corporate_actions/
│   ├── AAPL.parquet
│   └── MSFT.parquet
└── metadata/
    └── tickers_info.parquet
```

---

### 🧾 Contenuto dei file `prices/{ticker}/{year}.parquet`

Ogni file **annuale** contiene:
- barre **intraday a 1 minuto**
- un record **EOD** per ciascun giorno  
I due tipi sono distinguibili dalla colonna `type` (`"intraday"` | `"eod"`).

**Colonne**
- `date` — data di riferimento (tipo data)
- `time` — orario **Europe/Rome** (gestisce il DST)
- `ticker` — simbolo del titolo
- `open`, `high`, `low`, `close` — prezzi
- `volume` — volume scambiato
- `insertion_time` — timestamp di salvataggio (timezone del sistema)
- `type` — `"intraday"` oppure `"eod"`

**Note operative**
- Dati salvati **per anno** (`{ticker}/{YYYY}.parquet`) con compressione **ZSTD**.
- In aggiornamento:
  - i nuovi record vengono **uniti** a quelli esistenti;
  - in caso di duplicati su `['date','time','type']` si mantiene **l’ultima occorrenza**;
  - la **giornata dell’ultima data** già presente viene **riscritta** (overwrite) per allineare eventuali correzioni del provider.
- Gli anni precedenti non vengono modificati (salvo backfill esplicito).

---

### 📄 File `dividends/{ticker}.parquet`

Contiene i dividendi storici per ciascun titolo.

**Colonne**
- `ex_date`
- `amount`
- `currency`
- `payment_date`

---

### 📄 File `corporate_actions/{ticker}.parquet`

Contiene le azioni societarie (es. split, reverse split, ecc.).

**Colonne (tipiche)**
- `ca_type` (es. `DIVIDEND`, `SPLIT`, …)
- `ex_date`, `record_date`, `payment_date`
- `amount` (per dividendi), `split_ratio` (per split)
- `currency`


## Backtesting
TBD

## Roadmap
- Data Structure
    - creazione ETL da Polygon
- Backtester
    - creazione script che legge tutti i file prices/{ticker}/{year}/{day}.parquet dell'universo, aggrega i dati per giorno e salva un file cache/daily_snapshots/{year}/{month}/{day}.parquet
    - backtester intraday e daily
