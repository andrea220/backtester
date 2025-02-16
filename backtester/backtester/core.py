import QuantLib as ql
from market.preprocessing import MarketData
from pricing.portfolio import Portfolio
from abc import ABC, abstractmethod
import pandas as pd
from datetime import timedelta 



def get_dates_between(start_date, end_date):
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates

def history_to_dataframe(history):
    data = {}
    
    for date, market_data in history.items():
        equity_data = market_data.get('equity', {})
        for symbol, values in equity_data.items():
            if symbol not in data:
                data[symbol] = {}
            data[symbol][date] = values.get('price', None)
    
    df = pd.DataFrame(data)
    df.index.name = "Date"
    return df 

class Indicator:
    def __init__(self):
        self.methods = {}

    def register(self, name=None):
        """
        A decorator to register an indicator method with a custom or derived name.
        """
        def decorator(func):
            indicator_name = name or func.__name__
            self.methods[indicator_name] = func
            return func
        return decorator

    def compute(self, name, *args, **kwargs):
        """
        Compute the registered indicator.
        """
        if name not in self.methods:
            raise ValueError(f"Indicator '{name}' is not registered.")
        return self.methods[name](*args, **kwargs)
    
class Backtester(ABC):
    def __init__(self, universe, start_date, end_date, starting_balance):
        self.starting_balance = starting_balance
        self.margin = starting_balance
        self.calendar = ql.TARGET()

        market = MarketData(start_date, end_date)
        self.portfolio = Portfolio()
        self.indicator = Indicator()
        self.indicator_symbols = None
        self.indicator_values = {}
        for symbol in universe:
            market.build(symbol)
        self.available_market_data = market.market_data

        self.backtest_dates = get_dates_between(start_date, end_date)
        self.history = {}
        self.ref_dates = []
        self.unprocessed_dates = []
        self.positions_summary = None
        self.period_pnl = None

    def backtest(self):
        """ chiama in automatico on_data a ogni iterazione e aggiorna history con i valori noti fino alla data"""
        self.positions_summary = pd.DataFrame()
        self.ref_dates = []
        for backtest_date in self.backtest_dates:
            try:
                if self.calendar.isHoliday(ql.Date.from_date(backtest_date)):
                    continue
                try: 
                    self.history[backtest_date] = self.available_market_data[backtest_date]
                    # aggiungere if is_valid anche come controllo da far fare in fase di preprocessing
                except:
                    self.unprocessed_dates.append(backtest_date)
                    continue
                self.ref_dates.append(backtest_date)
                self.on_data()
                summary = pd.DataFrame(self.portfolio.get_positions_summary(self.available_market_data[backtest_date]))
                self.positions_summary = pd.concat([self.positions_summary, summary], axis = 0)
                # funzione che aggiorna il portafoglio in automatico
            except:
                print("ERROR ON DATE: ", backtest_date)
        self.period_pnl = self.positions_summary.groupby('ref_date')['global_pnl'].sum().reset_index() 
        self.period_pnl = self.period_pnl.rename(columns={'global_pnl': 'daily_pnl'})
        self.period_pnl['daily_pnl'] = self.period_pnl['daily_pnl'] + self.starting_balance

    def get_data_at(self, ref_date):
        history = {}
        for backtest_date in self.backtest_dates:
            if backtest_date > ref_date:
                break
            if self.calendar.isHoliday(ql.Date.from_date(backtest_date)):
                continue
            try: 
                history[backtest_date] = self.available_market_data[backtest_date]
                # aggiungere if is_valid anche come controllo da far fare in fase di preprocessing
            except:
                continue
        return history
                
    @abstractmethod
    def on_data(self):
        """
        Implement trading logic.
        """
        pass