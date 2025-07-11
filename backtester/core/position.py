from abc import ABC, abstractmethod
from datetime import date 
import QuantLib as ql
from .utils import *
import random
from scipy.interpolate import RegularGridInterpolator

class TradeId:
    _existing_ids = set()

    @classmethod
    def generate(cls) -> int:
        """Genera un numero intero univoco di 5 cifre per identificare una posizione."""
        while True:
            trade_id = random.randint(10000, 99999)  # Genera un numero di 5 cifre
            if trade_id not in cls._existing_ids:
                cls._existing_ids.add(trade_id)
                return trade_id
            
class Position(ABC):
    def __init__(self, symbol: str, asset_type: AssetType, quantity: float, market_data: dict, position_type: PositionType):
        self.trade_id = TradeId.generate()
        self.is_open = True
        self.closed_pnl = 0
        self.symbol = symbol
        self.asset_type = asset_type  # "bond", "equity", "option"
        self.quantity = quantity
        self.trade_date = market_data['ref_date']
        self.entry_price = self.calculate_value(market_data) 
        self.initial_ctv = (self.entry_price * self.quantity)
        self.position_type = position_type

    @abstractmethod
    def calculate_value(self, market_data: dict) -> float:
        """Metodo astratto per calcolare il valore della posizione."""
        pass

    def calculate_pnl(self, market_data: dict) -> float:
        if self.is_open:
            return (self.calculate_value(market_data) - self.entry_price) * self.position_type.value * self.quantity 
        else:
            return 0
    
    def close_position(self, market_data: dict):
        if self.is_open:
            self.closed_pnl = self.calculate_pnl(market_data)
            self.quantity = 0 
            self.is_open = False
        return

    def calculate_ctv(self, market_data: dict):
        if self.is_open:
            return self.calculate_value(market_data) * self.position_type.value * self.quantity 
        else:
            return 0



class EquityPosition(Position):
    def __init__(self, symbol: str, quantity: float, market_data: dict, position_type: PositionType):
        super().__init__(symbol, AssetType.EQUITY, quantity, market_data, position_type)

    def calculate_value(self, market_data: dict) -> float:
        """Usa il prezzo di  chiusura dell'azione per calcolare il valore della posizione."""
        return market_data[self.asset_type.value][self.symbol]["close"]


class OptionPosition(Position):
    def __init__(self, symbol: str, quantity: float, market_data: dict, strike_price: float, expiry_date: date, option_type: OptionType, position_type: PositionType,
                 day_count = ql.Actual365Fixed(), calendar = ql.TARGET()):
        self.strike_price = strike_price
        self.expiry_date = expiry_date
        if option_type == OptionType.CALL:
            self.option_type = ql.Option.Call
        else:
            self.option_type = ql.Option.Put
        self.day_count = day_count
        self.calendar = calendar
        self.option = self._build_option()
        super().__init__(symbol, AssetType.OPTION, quantity, market_data, position_type)


    def calculate_value(self, market_data: dict):
        if self.is_expiry_date(market_data['ref_date']):
            if self.is_open:
                payoff = self._payoff(market_data)
                self.closed_pnl = (payoff - self.entry_price) * self.quantity * self.position_type.value
                self.quantity = 0 
                self.is_open = False
            return 0
        
        if market_data['ref_date'] > self.expiry_date:
            # se per qualche motivo è stata saltata l'expiry date senza chiudere/esercitare la posizione, approssima il payoff con la data successiva
            if self.is_open:
                payoff = self._payoff(market_data)
                self.closed_pnl = (payoff - self.entry_price) * self.quantity * self.position_type.value
                self.quantity = 0 
                self.is_open = False
            return 0
        spot_ref = market_data['equity'][self.symbol]['close']
        
        valuation_date = ql.Date.from_date(market_data['ref_date'])
        ql.Settings.instance().evaluationDate = valuation_date
        maturity_date = ql.Date.from_date(self.expiry_date)
        dtm = maturity_date - valuation_date

        tenor = market_data['volatility'][self.symbol]['tenor']
        moneyness = market_data['volatility'][self.symbol]['moneyness']
        vol = market_data['volatility'][self.symbol]['volatility']
        interp_surface = RegularGridInterpolator((moneyness, tenor), vol, bounds_error=False, fill_value=None)

        sigma = float(interp_surface((self.strike_price/spot_ref, dtm)))

        spot_handle = ql.QuoteHandle(
        ql.SimpleQuote(spot_ref)
        )
        flat_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(valuation_date, market_data['rate']['riskfree'], self.day_count)
        )
        dividend_yield = ql.YieldTermStructureHandle(
        ql.FlatForward(valuation_date, market_data['equity'][self.symbol]['div_yield'], self.day_count)
        )
        flat_vol_ts = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(valuation_date, self.calendar, sigma, self.day_count)
        )
        bsm_process = ql.BlackScholesMertonProcess(spot_handle,
                                                dividend_yield,
                                                flat_ts,
                                                flat_vol_ts)

        self.option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))
        return self.option.NPV()
    
    def _payoff(self, market_data: dict):
        return max((market_data['equity'][self.symbol]['close'] - self.strike_price) * self.option_type, 0) 

    def _build_option(self):
        maturity_date = ql.Date.from_date(self.expiry_date)
        payoff = ql.PlainVanillaPayoff(self.option_type, self.strike_price)
        exercise = ql.EuropeanExercise(maturity_date)
        return ql.VanillaOption(payoff, exercise)
    
    def is_expiry_date(self, ref_date: date):
        if ref_date == self.expiry_date:
            return True
        else:
            return False


