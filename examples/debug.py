import sys 
sys.path.append("../")
import pandas as pd

#import backtester as bt
from backtester import backtester as bt

from abc import ABC, abstractmethod
import QuantLib as ql 
from datetime import date, datetime 
import matplotlib.pyplot as plt

class Backtester(ABC):
    def __init__(self, universe, start_date, end_date, starting_balance, rebuild = False):
        self.universe = universe
        self.start_iso = start_date
        self.end_iso = end_date
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        self.backtest_dates = bt.get_dates_between(self.start_date, self.end_date)

        self.starting_balance = starting_balance
        self.leverage = 1.5 
        self.margin = {}
        self.calendar = ql.TARGET()

        self.rebuild = rebuild

        self.portfolio = bt.Portfolio()
        self.indicator = bt.Indicator()

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
        self.market = bt.MarketData()
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
            try:
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

            except Exception as e:
                print("** ERROR INFO **")
                print(f"Pricing Date {backtest_date}, An error occurred: {e}")
                print("**")

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

    def close_Trade(self, position, market):
        self.margin[market['ref_date']] = self.margin[market['ref_date']] + position.calculate_ctv(market)
        position.close_position(market)
        return    
    
    def Trade(self, ticker, quantity, market, assettype = bt.AssetType.EQUITY, side = bt.PositionType.LONG, strike_price = 0, expiry_date = 0, option_type = 0):
        """ compra o vendi se c'è margine disponibile"""

        if assettype == bt.AssetType.EQUITY:
            position = bt.EquityPosition(ticker, quantity, market, side)
        elif assettype == bt.AssetType.OPTION:  #aggiusta opzioni e bond
            position = bt.OptionPosition(ticker, quantity, market, strike_price, expiry_date, option_type, side)
        elif assettype == bt.AssetType.BOND:
            position = bt.BondPosition(ticker, quantity, market, side)

        available_margin = self.margin[position.trade_date] * self.leverage
        short_margin = 0.2

        if side == 1:
            ctv = position.initial_ctv
        else:
            ctv = position.initial_ctv * short_margin
        
        if ctv <= available_margin:
            self.portfolio.add_position(position)
            self.margin[position.trade_date] = available_margin - ctv
        else:
            print(f"Not enough margin to trade {ticker} on {position.trade_date}.")
            exit()

    @abstractmethod
    def on_data(self):
        """
        Implement trading logic.
        """
        pass


class BuyHoldStrategy(Backtester):
    def __init__(self, universe, start_date, end_date, starting_balance):
        super().__init__(universe, start_date, end_date, starting_balance)
        self.position_open = False   
        self.price_tickers = ['ISP_IM_Equity']


    def on_data(self):
        mkt = self.history[self.ref_date]
        # close_price = mkt['equity']['ISP_IM_Equity']['close']

        if not self.position_open:
            self.Trade(ticker='ISP_IM_Equity', quantity=2, market=mkt, side = bt.PositionType.LONG)
            self.position_open = True

        if self.ref_date == "2023-12-27":
            eq_position = self.portfolio.get_positions('ISP_IM_Equity', bt.AssetType.EQUITY)[0]
            self.close_Trade(eq_position, mkt)


class SellHoldStrategy(Backtester):
    def __init__(self, universe, start_date, end_date, starting_balance):
        super().__init__(universe, start_date, end_date, starting_balance)
        self.position_open = False   
        self.price_tickers = ['ISP_IM_Equity']


    def on_data(self):
        mkt = self.history[self.ref_date]
        # close_price = mkt['equity']['ISP_IM_Equity']['close']

        if not self.position_open:
            self.Trade(ticker='ISP_IM_Equity', quantity=2, market=mkt,
                        side = bt.PositionType.SHORT, assettype = bt.AssetType.OPTION,  strike_price = 2.5, 
                        expiry_date = date(2024,10,10), option_type = bt.OptionType.CALL)
            self.position_open = True

        if self.ref_date == "2023-12-27":
            eq_position = self.portfolio.get_positions('ISP_IM_Equity', bt.AssetType.EQUITY)[0]
            self.close_Trade(eq_position, mkt)

# class PAC(Backtester):
#     def __init__(self, universe, start_date, end_date, starting_balance):
#         super().__init__(universe, start_date, end_date, starting_balance)
#         self.position_open = False   
#         self.price_tickers = ['ISP_IM_Equity']


#     def on_data(self):

#         self.pac_time = 1 # in mesi
#         self.pac_qty = 10

#         for i, data in enumerate(self.valid_dates):
#             mkt = self.history[data.isoformat()]
#             self.Trade(ticker='ISP_IM_Equity', quantity=self.pac_qty, market=mkt, side = bt.PositionType.LONG)
#             self.position_open = True

#             if self.ref_date == "2023-12-27":
#                 eq_position = self.portfolio.get_positions('ISP_IM_Equity', bt.AssetType.EQUITY)[0]
              
#                 self.close_Trade(eq_position, mkt)

        

universe = ['ISP_IM_Equity']
backtester = SellHoldStrategy(universe, '2015-01-01', '2024-12-31', starting_balance=10 )
backtester.backtest()
res = bt.ResultAnalyzer(backtester.positions_summary, backtester.period_pnl)
res.get_trade_log()
res.plot_pnl()
plt.show()