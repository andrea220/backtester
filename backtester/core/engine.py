import QuantLib as ql
from ..data.build import MarketData
from .portfolio import Portfolio
from .position import *
from .utils import *
from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, date, timedelta 



def get_dates_between(start_date, end_date):
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates

def prices_to_df(history, field = 'close'):
    data = {}
    
    for date, market_data in history.items():
        equity_data = market_data.get('equity', {})
        for symbol, values in equity_data.items():
            if symbol not in data:
                data[symbol] = {}
            data[symbol][date] = values.get(field, None)
    
    df = pd.DataFrame(data)
    df.index.name = "Date"
    return df 


class Indicator(ABC):
    def __init__(self):
        self.methods = {}

    def register(self, name=None):
        """
        A decorator to register an indicator method with a custom or derived name.
        """
        def decorator(func):
            self.methods[name or func.__name__] = func
            return func
        return decorator

    def compute(self, name, *args, **kwargs):
        """
        Compute the registered indicator.
        """
        if name not in self.methods:
            raise ValueError(f"Indicator '{name}' is not registered.")
        return self.methods[name](*args, **kwargs)
    
    @abstractmethod
    def warmup(self, name, prices, window):
        """ Ensure there is enough historical data for the indicator """
        pass


class Backtester(ABC):
    def __init__(self, universe, start_date, end_date, starting_balance, rebuild = False):
        self.universe = universe
        self.start_iso = start_date
        self.end_iso = end_date
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        self.backtest_dates = get_dates_between(self.start_date, self.end_date)

        self.starting_balance = starting_balance
        self.leverage = 1.5 
        self.margin = {}
        self.calendar = ql.TARGET()

        self.rebuild = rebuild
        self.portfolio = Portfolio()

        # crea il grid di date in base alla necessità di input se presenti o no
        self.valid_dates = []
        self.unprocessed_dates = []
        self.price_tickers = [] # aggiornano in implementazione concreta
        self.vol_tickers = []

        self.history = {}
        self.positions_summary = pd.DataFrame()
        self.period_pnl = None

    def _on_start(self):
        ''' 
        carica i market data 
        crea il grid di date
        '''
        self.market = MarketData()
        self.market.load_market_data(self.rebuild)

        self._create_date_grid()
        if self.valid_dates == []:
            raise ValueError("No date available")
        self.first_date = self.valid_dates[0]
        self.last_date = self.valid_dates[-1]

    def backtest(self):
        """ chiama in automatico on_data a ogni iterazione e aggiorna history con i valori noti fino alla data"""
        self._on_start()
        self.positions_summary = pd.DataFrame()
        self.ref_dates = []
        self.ref_date = self.first_date
        for i, backtest_date in enumerate(self.valid_dates):
            self.history[backtest_date.isoformat()] = self.market.market_data[backtest_date.isoformat()]
            if backtest_date == self.first_date:
                self.margin[backtest_date.isoformat()] = self.starting_balance
            else:
                self.margin[backtest_date.isoformat()] = self.margin[self.valid_dates[i-1].isoformat()]

            if backtest_date == self.last_date:
                self.ref_dates.append(backtest_date)
                self.portfolio.close_all_positions(self.market.market_data[backtest_date.isoformat()])
                self.margin[backtest_date.isoformat()] = 0
            else:
                self.ref_dates.append(backtest_date.isoformat())
                self.ref_date = self.ref_dates[-1] 
                self.on_data()
            summary = pd.DataFrame(self.portfolio.get_positions_summary(self.market.market_data[backtest_date.isoformat()]))
            self.positions_summary = pd.concat([self.positions_summary, summary], axis = 0)
        if self.positions_summary.empty:
            return
        self.period_pnl = self.positions_summary.groupby('ref_date')['global_pnl'].sum().reset_index() 
        self.period_pnl = self.period_pnl.rename(columns={'global_pnl': 'daily_pnl'})
        self.period_pnl['daily_pnl'] = self.period_pnl['daily_pnl'] + self.starting_balance

    def _create_date_grid(self):
        for backtest_date in self.backtest_dates:
            if self.calendar.isHoliday(ql.Date.from_date(backtest_date)):
                continue
            try:
                [self.market.market_data[backtest_date.isoformat()]['equity'][p]['close'] for p in self.price_tickers]
            except:
                self.unprocessed_dates.append(backtest_date)
                continue
            try:
                [self.market.market_data[backtest_date.isoformat()]['volatility'][p] for p in self.vol_tickers]
            except:
                self.unprocessed_dates.append(backtest_date)
                continue
            self.valid_dates.append(backtest_date)

    def get_data_at(self, ref_date: str):
        history = {}
        for backtest_date in self.valid_dates:
            if backtest_date > datetime.strptime(ref_date, '%Y-%m-%d').date():
                break 
            history[backtest_date.isoformat()] = self.market.market_data[backtest_date.isoformat()]
        return history

    def close_trade(self, position, market):
        self.margin[market['ref_date'].isoformat()] = self.margin[market['ref_date'].isoformat()] + position.calculate_ctv(market)
        position.close_position(market)
        return    
    
    def trade(self, ticker, quantity, market, assettype= AssetType.EQUITY, side=PositionType.LONG, **kwargs):
        """ Compra o vendi se c'è margine disponibile. """
        
        if assettype == AssetType.EQUITY:
            position = EquityPosition(ticker, quantity, market, side)
        elif assettype == AssetType.OPTION:  # Aggiusta opzioni e bond
            required_keys = {'strike_price', 'expiry_date', 'option_type'}
            if not required_keys.issubset(kwargs):
                raise ValueError("Per le opzioni, strike_price, expiry_date e option_type devono essere specificati.")
            position = OptionPosition(ticker, quantity, market, 
                                        kwargs['strike_price'], kwargs['expiry_date'], kwargs['option_type'], side)
        # elif assettype == AssetType.BOND:
        #     position = BondPosition(ticker, quantity, market, side)
        else:
            raise ValueError("Tipo di asset non supportato.")

        available_margin = self.margin.get(position.trade_date, 0) * self.leverage
        short_margin = 0.2

        ctv = position.initial_ctv if side == PositionType.LONG else position.initial_ctv * short_margin
        
        if ctv <= available_margin:
            self.portfolio.add_position(position)
            self.margin[position.trade_date] = available_margin - ctv
        else:
            print(f"Not enough margin to trade {ticker} on {position.trade_date}.")

    @abstractmethod
    def on_data(self):
        """
        Implement trading logic.
        """
        pass