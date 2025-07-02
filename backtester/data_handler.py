import pandas as pd 
import numpy as np 
from datetime import datetime
from xbbg import blp
import os 
import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import json

class MarketDataHandler:
    
    def __init__(self):
        DATA_PATH = "C:/Users/S542279/Desktop/backtester/data/"
        self.prices_path = DATA_PATH + "prices"
        self.vols_path = DATA_PATH + "volatilities"
        self.data_path = DATA_PATH
        self.market_data = {}

    @staticmethod
    def _bbg_intraday_dump(ticker: str,
                        start_date: str,
                        end_date: str) -> pd.DataFrame:
        """
        Scarica i dati intraday bdib per un range di date.
        """      
        start_dt = pd.to_datetime(start_date)
        end_dt   = pd.to_datetime(end_date)
        if end_dt < start_dt:
            raise ValueError(f"end_date ({end_date}) deve essere maggiore o uguale a start_date ({start_date})")
 
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        df_list = []
        for dt in date_range:
            try:
                df_day = blp.bdib(ticker=ticker, dt=dt, ref='EquityAllDay', session='allday')
                df_list.append(df_day)
            except Exception as e:
                print(f"Errore per {dt.date()}: {e}")
        
        if df_list:
            df_all = pd.concat(df_list)
        else:
            df_all = pd.DataFrame()
        return df_all.get(ticker, df_all)
    
    @staticmethod
    def _bbg_daily_dump(ticker: str,
                        start_date: str,
                        end_date: str) -> pd.DataFrame:
        """
        Scarica i dati daily per un range di date.
        """      
        start_dt = pd.to_datetime(start_date)
        end_dt   = pd.to_datetime(end_date)
        if end_dt < start_dt:
            raise ValueError(f"end_date ({end_date}) deve essere maggiore o uguale a start_date ({start_date})")
 
        df_all= blp.bdh(ticker,
                flds=['open', 'high', 'low', 'px_last', 'volume'], 
                CshAdjNormal=True, CshAdjAbnormal=True, CapChg=True,
                start_date=start_date,
                end_date=end_date)
        
        df = df_all.get(ticker, df_all)
        df = df.rename(columns={'px_last': 'close'})
        return df.dropna()

    @staticmethod
    def create_table(df, ticker):
        # 1. Porta l'indice in colonna
        df = df.reset_index().rename(columns={'index': 'caldt'})
        # 2. Assicurati che caldt sia datetime
        df['caldt'] = pd.to_datetime(df['caldt'], utc=True)
        df['caldt'] = df['caldt'].dt.tz_convert('Europe/Rome')
        # 3. Estrai data e time
        df['date'] = df['caldt'].dt.date
        df['time'] = df['caldt'].dt.time

        # 4. Aggiungi ticker
        df['ticker'] = ticker

        # 5. Aggiungi insertion_time arrotondato al minuto
        now = datetime.now().replace(second=0, microsecond=0)
        df['insertion_time'] = now

        # 6. Riorganizza colonne, includendo num_trds e value
        df = df[['date',
                'time',
                'ticker',
                'open',
                'high',
                'low',
                'close',
                'volume',
                'insertion_time']] 
        return df

    def load_price(self, ticker: str, freq: str) -> pd.DataFrame:
        # 1. Costruisci il path in base alla frequenza
        if freq == '1m':
            file_path = os.path.join(self.prices_path, f"{ticker}.csv")
            converters = {
                'date': lambda x: datetime.strptime(x, "%Y-%m-%d").date(),
                'time': lambda x: datetime.strptime(x, "%H:%M:%S").time(),
                'insertion_time': lambda x: datetime.fromisoformat(x)
            }
        elif freq == '1d':
            file_path = os.path.join(self.data_path, "daily", f"{ticker}.csv")
            converters = {
                'date': lambda x: datetime.strptime(x, "%Y-%m-%d").date(),
                'insertion_time': lambda x: datetime.fromisoformat(x)
            }
        else:
            raise ValueError("freq deve essere '1m' o '1d'")

        # 2. Controllo esistenza file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Il file '{file_path}' non esiste. "
                                    "Esegui prima download_history o update_series.")

        # 3. Carica e ritorna
        df = pd.read_csv(file_path, converters=converters)
        return df         

    def download_history(self,
                ticker: str,
                start_date: str,
                end_date: str,
                intraday: bool = True):
        ''' 
        # scarica i dati da bbg chiamando _bbg_daily_dump (in self.prices_path +"/daily") e _bbg_intraday_dump (in self.prices_path)
        # se ticker già presente deve dare errore perché non si vuole sovrascrivere
        '''
        if intraday:
            timeframes = ['1d', '1m']
        else:
            timeframes = ['1d']

        for freq in timeframes:
            try:
                if freq == '1d':
                    out_dir = os.path.join(self.data_path, "daily")
                    fetch   = self._bbg_daily_dump
                elif freq == '1m':
                    out_dir = self.prices_path
                    start_date = '2024-09-01'
                    fetch   = self._bbg_intraday_dump
                file_path = os.path.join(out_dir, f"{ticker}.csv")
                if os.path.exists(file_path):
                    raise FileExistsError(f"Il file '{file_path}' esiste già, non sovrascrivo.")
                df = fetch(ticker, start_date, end_date)
                df = self.create_table(df, ticker)
                if freq == '1d':
                    df.drop('time', axis=1, inplace=True)
                df.to_csv(file_path, index=False)
                print(f"Scaricato {ticker} ({freq}) in '{file_path}'")
            except Exception as e:
                print(e)
                continue

    def update_series(self, ticker: str, freq: str):
        """
        Se esiste già il CSV per il ticker+freq, scarica solo i dati
        più recenti (da ultimo presente fino a oggi), unisce e salva.
        freq: '1d' o '1m'
        """
        # 1. Percorso e funzione di fetch
        if freq == '1d':
            folder = os.path.join(self.data_path, "daily")
            fetch = self._bbg_daily_dump
        elif freq == '1m':
            folder = self.prices_path
            fetch = self._bbg_intraday_dump
        else:
            raise ValueError("freq deve essere '1d' o '1m'")

        file_path = os.path.join(folder, f"{ticker}.csv")

        # 2. Se il file non esiste, fermati
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Il file '{file_path}' non esiste. Usa prima download_history.")

        df_old = self.load_price(ticker, freq)
        last_dt = df_old['date'].max()
        start_date = last_dt.isoformat()
        end_date = datetime.now().date().isoformat()

        # 5. Fetch nuovi dati
        df_new_raw = fetch(ticker, start_date, end_date)
        if df_new_raw.empty:
            print(f"Nessun dato scaricato da {start_date} a {end_date} per {ticker} ({freq})")
            # return
        df_new = self.create_table(df_new_raw, ticker)
        if freq == '1d':
            df_new = df_new.drop('time', axis=1)
        # 7. Unisci e rimuovi duplicati
        if freq == '1d':
            df_merged = pd.concat([df_old, df_new]).drop_duplicates(subset=['date'], keep='last')
            df_merged = df_merged.sort_values('date').reset_index(drop=True)
        else:
            df_merged = pd.concat([df_old, df_new]).drop_duplicates(subset=['date', 'time'], keep='last')
            df_merged = df_merged.sort_values(['date', 'time']).reset_index(drop=True)
        # 8. Salva CSV sovrascrivendo
        df_merged.to_csv(file_path, index=False)
        print(f"Aggiornato {ticker} ({freq}): da {start_date} a {end_date} in '{file_path}'")
   
    def build(self, ticker, start_date, end_date, intraday: bool = True):
        """ 
        fa il dump di tutti i dati per quel simbolo
        """
        self.download_history(ticker, start_date, end_date, intraday)
        self.update_series(ticker, '1d')
        if intraday:
            self.update_series(ticker, '1m') 
     
    def _prepare_df(self, ticker: str, start_date: str, end_date: str, freq: str) -> pd.DataFrame:
        """Carica, indicizza e filtra il DataFrame."""
        df = self.load_price(ticker, freq)
        df['date'] = pd.to_datetime(df['date'])
        if freq == '1m':
            df['time'] = df['time'].astype(str)
            df['datetime'] = pd.to_datetime(df['date'].dt.strftime('%Y-%m-%d') + ' ' + df['time'])
            df = df.set_index('datetime')
        else:
            df = df.set_index('date')

        mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
        return df.loc[mask]

    def _plot_line(self, df: pd.DataFrame, ticker: str, start_date: str, end_date: str):
        """Grafico a linea + % change, layout ottimizzato e griglia discreta."""
        first = df['close'].iloc[0]
        pct = (df['close'] / first - 1) * 100

        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax2 = ax1.twinx()

        # Serie
        ax1.plot(df.index, df['close'], label='Close', linewidth=1.5)
        ax2.plot(df.index, pct, label='% Change', linestyle='--', linewidth=1.2)

        # Titolo in suptitle per evitare overlap
        fig.suptitle(f"{ticker} ({start_date} – {end_date})", fontsize=10, y=0.97)
        fig.subplots_adjust(top=0.88, left=0.07, right=0.93, bottom=0.12)

        # Etichette assi
        ax1.set_ylabel('Close', fontsize=10)
        ax2.set_ylabel('% Change', fontsize=10)

        # Griglia: solo linee orizzontali su ax1, fine e sotto le linee
        ax2.set_axisbelow(True)
        ax2.yaxis.grid(True, linestyle='--', linewidth=0.6, color='gray')
        ax2.xaxis.grid(False)
        ax1.grid(False)

        # Formattazione date sull'asse X
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax1.xaxis.get_major_locator()))
        fig.autofmt_xdate(rotation=0)
        plt.show()

    def _plot_ohlc(self, df: pd.DataFrame, ticker: str, start_date: str, end_date: str, volume: bool):
        """
        Grafico candlestick (OHLC); se volume=True aggiunge il pannello dei volumi.
        Miglior layout: margini per il titolo e griglia tratteggiata sotto le candele.
        """
        # Preparo un style che definisce griglia tratteggiata
        mpf_style = mpf.make_mpf_style(
            base_mpf_style='yahoo',
            gridstyle='--',
            gridaxis='both',
            gridcolor='lightgray'
        )

        # Uso returnfig per poter regolare manualmente il titolo e i margini
        fig, axes = mpf.plot(
            df[['open','high','low','close','volume']] if volume else df[['open','high','low','close']],
            type='candle',
            volume=volume,
            style=mpf_style,
            figsize=(12, 5),
            returnfig=True
        )

        # Titolo in suptitle con spazio garantito
        fig.suptitle(f"{ticker} ({start_date} – {end_date})", fontsize=10, y=0.97)
        # Allargo il top margin per non sovrapporre
        fig.subplots_adjust(top=0.90, left=0.05, right=0.95, bottom=0.10)

        # Assicuro che la griglia stia sotto le candele
        for ax in axes:
            ax.set_axisbelow(True)
        plt.show()

    def _plot_volume_candles(self, df: pd.DataFrame, ticker: str, start_date: str, end_date: str):
        """
        Disegna volume candles:
        - Altezza = high - low
        - Larghezza ∝ volume
        - Corpo verde/rosso a seconda di close vs open
        Con layout ottimizzato per griglia e titolo.
        """
        dates = mdates.date2num(df.index.to_pydatetime())
        volumes = df['volume'].values
        max_vol = volumes.max()

        deltas = np.diff(dates)
        avg_delta = np.median(deltas) if len(deltas) > 0 else 1
        max_width = avg_delta * 0.8

        fig, ax = plt.subplots(figsize=(12, 5))
        
        # Title e margini
        ax.set_title(f"{ticker} Volume Candles ({start_date} – {end_date})", 
                     fontsize=14, y=1.02)
        fig.subplots_adjust(top=0.88, left=0.06, right=0.98, bottom=0.10)

        # Griglia tratteggiata solo sull'asse y (o entrambe se preferisci)
        ax.set_axisbelow(True)
        ax.grid(axis='y', linestyle='--', linewidth=0.5)

        for dt, o, h, l, c, vol in zip(dates,
                                       df['open'], df['high'],
                                       df['low'], df['close'],
                                       volumes):
            width = max_width * (vol / max_vol)
            color = 'green' if c >= o else 'red'

            # Corpo candela
            bottom = min(o, c)
            height = abs(c - o)
            rect = Rectangle(
                (dt - width/2, bottom),
                width, height,
                facecolor=color, edgecolor='black', linewidth=0.5
            )
            ax.add_patch(rect)

            # Wick
            ax.vlines(dt, l, h, color='black', linewidth=0.5)

        ax.xaxis_date()
        ax.set_xlim(dates.min() - avg_delta, dates.max() + avg_delta)
        ax.set_ylabel('Prezzo', fontsize=10)

        plt.tight_layout()
        plt.show()

    def plot(self,
             ticker: str,
             start_date: str,
             end_date: str,
             freq: str = '1d',
             kind: str = 'line'):
        """
        Wrapper per il plotting:
        kind = 'line' → prezzo + % change
               'ohlc' → candele OHLC (+ pannello volume se vol=True)
               'vol'  → volume candles (larghezza ∝ volume)
        """
        df_plot = self._prepare_df(ticker, start_date, end_date, freq)
        if df_plot.empty:
            print(f"Nessun dato disponibile per {ticker} tra {start_date} e {end_date}.")
            return

        if kind == 'line':
            self._plot_line(df_plot, ticker, start_date, end_date)
        elif kind == 'ohlc':
            self._plot_ohlc(df_plot, ticker, start_date, end_date, volume=True)
        elif kind == 'vol':
            self._plot_volume_candles(df_plot, ticker, start_date, end_date)
        else:
            raise ValueError("kind deve essere 'line', 'ohlc' o 'vol'")
        
    def load_universe(self, universe, start_date, end_date, frequency, rebuild):
        df_all = {}

        for ticker in universe:
            if rebuild:
                self.build(ticker, start_date, end_date)
            
            df_all[ticker] = self.load_price(ticker, frequency)
        return df_all
    
    def _fill_prices_old(self, universe, start_date, end_date, frequency, rebuild):
        for tk in universe:
            if rebuild:
                self.build(tk, start_date, end_date)

            df_prices = self.load_price(tk, frequency)

            for ix, row in df_prices.iterrows():
                current_date = row['date'].isoformat()

                if current_date not in self.market_data:
                    self.market_data[current_date] = {"ref_date": current_date,
                                                      "EOD": {
                                                                "ref_date": current_date,
                                                                "equity": {},
                                                                "rate": {},  
                                                                "volatility": {}
                                                            }}
                    
                # Aggiungi i dati dell'equity
                if frequency == '1d':
                    self.market_data[current_date]['EOD']["equity"][tk] = {
                                                                        "open": float(row["open"]),
                                                                        "high": float(row["high"]),
                                                                        "low": float(row["low"]),
                                                                        "close": float(row["close"]),
                                                                        "volume": float(row["volume"]),
                                                                        "is_valid": True
                                                                    }
                else:
                    return
                
    def _fill_prices(self, universe, start_date, end_date, frequency, rebuild):
        for tk in universe:
            if rebuild:
                self.build(tk, start_date, end_date)

            # prima loop sul giornaliero
            df_prices_daily = self.load_price(tk, '1d')
            for ix, row in df_prices_daily.iterrows():
                current_date = row['date'].isoformat()

                if current_date not in self.market_data:
                    self.market_data[current_date] = {"ref_date": current_date,
                                                        "EOD": {
                                                                "ref_date": current_date,
                                                                "equity": {},
                                                                "rate": {},  
                                                                "volatility": {}
                                                            }}
                self.market_data[current_date]['EOD']["equity"][tk] = {
                                                                        "open": float(row["open"]),
                                                                        "high": float(row["high"]),
                                                                        "low": float(row["low"]),
                                                                        "close": float(row["close"]),
                                                                        "volume": float(row["volume"]),
                                                                        "is_valid": True
                                                                    }
            # se specificato intraday allora lo crea
            if frequency == '1m':
                df_prices = self.load_price(tk, '1m')
                for ix, row in df_prices.iterrows():
                    current_date = row['date'].isoformat()
                    time = row['time'].isoformat()
                    if time not in self.market_data[current_date]:
                        self.market_data[current_date][time] = {
                                                                    "ref_date": current_date,
                                                                    "equity": {},
                                                                    "rate": {},  
                                                                    "volatility": {}
                                                                }
                    self.market_data[current_date][time]["equity"][tk] = {
                                                                            "open": float(row["open"]),
                                                                            "high": float(row["high"]),
                                                                            "low": float(row["low"]),
                                                                            "close": float(row["close"]),
                                                                            "volume": float(row["volume"]),
                                                                            "is_valid": True
                                                                        }
                    
    def _build_market(self, universe, start_date, end_date, frequency, rebuild):
        self._fill_prices(universe, start_date, end_date, frequency, rebuild)

        with open(f"{self.data_path}MarketData.json", "w") as json_file:
            json.dump(self.market_data, json_file, indent=4)

    def load_market(self, universe, start_date, end_date, frequency='1d', rebuild=False):
        if rebuild:
            print("*****")
            print("Building MarketData...")
            self._build_market(universe, start_date, end_date, frequency, rebuild)
            print("Done!")
            print("*****")
        
        else:
            with open(f"{self.data_path}MarketData.json", "r", encoding="utf-8") as file:
                self.market_data = json.load(file)

        # Convertire 'ref_date' in datetime.date
        for date_key, data in self.market_data.items():
            if "ref_date" in data:
                data["ref_date"] = datetime.strptime(data["ref_date"], "%Y-%m-%d").date()