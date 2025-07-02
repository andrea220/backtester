# import QuantLib as ql
from ..data_handler import MarketDataHandler
from .portfolio import Portfolio
from .position import *
from .utils import *
from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, date, timedelta 
from typing import List, Dict, Any

class Backtester(ABC):
    def __init__(self, universe, start_date, end_date,
                 starting_balance, max_leverage, 
                 frequency = 'EOD', rebuild = False):
        self.universe = universe
        self.start_iso = start_date
        self.end_iso = end_date
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        self.backtest_dates = self.get_dates_between(self.start_date, self.end_date)

        self.starting_balance = starting_balance
        self.balance = {}           
        self.max_leverage = max_leverage 
        self.frequency = frequency
        self.margin = {}
        self.calendar = ql.TARGET()

        self.rebuild = rebuild
        self.portfolio = Portfolio()

        # crea il grid di date in base alla necessità di input se presenti o no
        self.valid_dates = []
        self.unprocessed_dates = []

        self.history = {}
        self.positions_summary = pd.DataFrame()
        self.period_pnl = None

        self.price_tickers = universe
        self.vol_tickers = []
        self.market =  MarketDataHandler()
        self.market.load_market(self.universe, self.start_iso, self.end_iso, self.rebuild)
        self.factors = []
        self.factors_df = pd.DataFrame()

    @abstractmethod
    def on_data(self):
        """
        Implement trading logic.
        """
        pass

    @staticmethod
    def get_dates_between(start_date, end_date):
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        return dates
    
    def prices_to_df(self, field = 'close'):
        data = {}
        
        for date, market_data in self.history.items():
            # market_data = market_data[self.frequency]
            equity_data = market_data.get('equity', {})
            for symbol, values in equity_data.items():
                if symbol not in data:
                    data[symbol] = {}
                data[symbol][date] = values.get(field, None)
        
        df = pd.DataFrame(data)
        df.index.name = "Date"
        return df 

    def _create_date_grid(self):
        """ 
        crea la griglia di date per il backtest escludendo i festivi e i giorni non presenti in database
        """
        if self.frequency == 'EOD':
            for backtest_date in self.backtest_dates:
                if self.calendar.isHoliday(ql.Date.from_date(backtest_date)):
                    continue
                try:
                    [self.market.market_data[backtest_date.isoformat()]['EOD']['equity'][p]['close'] for p in self.price_tickers]
                except:
                    self.unprocessed_dates.append(backtest_date)
                    continue
                try:
                    [self.market.market_data[backtest_date.isoformat()]['EOD']['volatility'][p] for p in self.vol_tickers]
                except:
                    self.unprocessed_dates.append(backtest_date)
                    continue
                self.valid_dates.append(backtest_date)

    def _on_start(self):
        ''' 
        carica i market data 
        crea il grid di date
        '''
        # self.market =  MarketDataHandler()
        # self.market.load_market(self.universe, self.start_iso, self.end_iso, self.rebuild)
        self._create_date_grid()
        if self.valid_dates == []:
            raise ValueError("No date available")
        self.first_date = self.valid_dates[0]
        self.last_date = self.valid_dates[-1]
        self._compute_all_factors()

    def _compute_all_factors(self) -> pd.DataFrame: ## da aggiungere in on_start, aggiungere self.factors = []
        """
        Calcola tutti i fattori, produce un unico DataFrame a MultiIndex:
        livello 0 = nome del fattore, livello 1 = simbolo.
        """
        if self.factors == []:
            return
        # 1) calcola ciascun DataFrame
        factor_dfs = {
            # uso il nome classe minuscolo come chiave del fattore
            f.__class__.__name__.lower(): f.compute()
            for f in self.factors
        }
        # 2) concatena orizzontalmente con MultiIndex sulle colonne
        self.factors_df = pd.concat(factor_dfs, axis=1, names=['factor', 'symbol'])

    def factor_data(self, ticker: str) -> pd.DataFrame:
        """
        Calcola tutti i fattori e restituisce il DataFrame
        con le colonne di tutti i fattori, filtrato per un singolo ticker.
        """
        if self.factors_df.empty:
            return
        # Se il ticker non esiste nelle colonne, solleva errore
        if ticker not in self.factors_df.columns.get_level_values('symbol'):
            raise KeyError(f"Ticker '{ticker}' non trovato nei risultati dei fattori.")
        # Estrai il sotto‐DataFrame e rimuovi il livello 'symbol'
        return self.factors_df.xs(ticker, axis=1, level='symbol')

    def trade(self, ticker, quantity, market, assettype, side, **kwargs):
        """ Compra o vendi se c'è margine disponibile. """
        
        if assettype == AssetType.EQUITY:
            position = EquityPosition(ticker, quantity, market, side)
        else:
            raise ValueError("Tipo di asset non supportato.")
        self.portfolio.add_position(position)
        
    def get_history(self, ref_date: str):
        ''' 
        ritorna tutti i dati disponibili fino alla ref_date in formato history come viene passato al backtester
        '''
        history = {}
        for backtest_date in self.valid_dates:
            if backtest_date > datetime.strptime(ref_date, '%Y-%m-%d').date():
                break 
            history[backtest_date.isoformat()] = self.market.market_data[backtest_date.isoformat()]
        return history
    
    def backtest(self):
        """ chiama in automatico on_data a ogni iterazione e aggiorna history con i valori noti fino alla data"""
        self._on_start()
        self.positions_summary = pd.DataFrame()
        self.ref_dates = []
        self.ref_date = self.first_date
        self.balance[self.first_date.isoformat()] = self.starting_balance

        for i, backtest_date in enumerate(self.valid_dates):
            self.history[backtest_date.isoformat()] = self.market.market_data[backtest_date.isoformat()][self.frequency]
            if backtest_date == self.last_date:
                self.ref_dates.append(backtest_date)
                self.portfolio.close_all_positions(self.history[backtest_date.isoformat()])
                self.factors_history = self.factors_df.loc[self.first_date.isoformat():self.last_date.isoformat()]
            else:
                self.ref_dates.append(backtest_date.isoformat())
                self.ref_date = self.ref_dates[-1] 
                self.factors_history = self.factors_df.loc[self.first_date.isoformat():self.ref_date]
                self.on_data()
            summary = pd.DataFrame(self.portfolio.get_positions_summary(self.history[backtest_date.isoformat()]))
            self.positions_summary = pd.concat([self.positions_summary, summary], axis = 0)
            if summary.empty:
                pnl = 0
            else:
                pnl = summary['global_pnl'].sum()
            self.balance[backtest_date.isoformat()] = self.starting_balance + pnl
        if self.positions_summary.empty:
            return
        self.period_pnl = self.positions_summary.groupby('ref_date')['global_pnl'].sum().reset_index() 
        self.period_pnl = self.period_pnl.rename(columns={'global_pnl': 'daily_pnl'})
        self.period_pnl['daily_pnl'] = self.period_pnl['daily_pnl'] + self.starting_balance



class Factor(ABC):
    def __init__(self, history: Dict[date, Any], frequency):
        self.methods = {}
        self.history = history
        self.frequency = frequency

    @abstractmethod
    def compute(self, name: str, **params):
        return