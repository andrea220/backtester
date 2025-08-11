

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

### 🧾 Prezzi `prices/{ticker}/{year}.parquet`

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
### 📄 Dividendi (`data/dividends/{ticker}.parquet`)

Questa sezione descrive come vengono salvati e aggiornati i **dividendi** per ciascun titolo.

**Percorso file**
```
data/dividends/{TICKER}.parquet
```

**Origine dati**
- Bloomberg via `xbbg` (funzione `BDS('DVD_HIST_ALL')`).

**Schema colonne (tipico)**
- `ex_date` — data ex-dividend (datetime)
- `payment_date` — data pagamento (datetime)
- `amount` — importo dividendo per azione (float)
- `currency` — valuta (string)
- `ticker` — simbolo (string)
- `insertion_time` — timestamp di salvataggio (datetime)

**Politiche di scrittura/aggiornamento**
- Salvataggio **incrementale** in Parquet con compressione **ZSTD**.
- **Merge** con il file esistente e **deduplica** su chiavi robuste:
  `['ticker', 'ex_date', 'payment_date', 'amount', 'currency']` (keep='last').
- Possibile filtro per periodo in input (su `ex_date`) prima del salvataggio.

**Note**
- Le colonne disponibili possono variare a seconda del provider/strumento (lo schema è unione dei campi disponibili).
- Per backtest “as-of” considera di congelare snapshot periodici della cartella `data/dividends/` (es. `revisions/snapshot=YYYY-MM-DD/`).




## Backtesting
TBD

## Roadmap
- Data Structure
    - creazione ETL da Polygon
- Backtester
    - creazione script che legge tutti i file prices/{ticker}/{year}/{day}.parquet dell'universo, aggrega i dati per giorno e salva un file cache/daily_snapshots/{year}/{month}/{day}.parquet
    - backtester intraday e daily
