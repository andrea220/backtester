import QuantLib as ql
# from market.preprocessing import MarketData
from .portfolio import Portfolio
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
 