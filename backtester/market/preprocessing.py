import QuantLib as ql 
import pandas as pd 

DEFAULT_RISKFREE = 0.03



class MarketData:

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.market_data = {}
        
    def _fill_prices(self, symbol):
        """
        Generate a market data dictionary from a given prices DataFrame.
        The market data contains equity prices and dividend yields.
        """
        prices_df = pd.read_csv(f'../data/prices/{symbol}_prices.csv').iloc[:, 1:]
        prices_df['date'] = pd.to_datetime(prices_df['date'], format='%d/%m/%y').dt.date
        prices_df = prices_df[(prices_df['date'] >= self.start_date)& (prices_df['date'] <= self.end_date)].copy()

        # Itera sul DataFrame per riempire il dizionario market_data
        for _, row in prices_df.iterrows():
            current_date = row["date"]
            
            # Inizializza la data se non esiste già nel dizionario
            if current_date not in self.market_data:
                self.market_data[current_date] = {
                    "ref_date": current_date,
                    "equity": {},
                    "rate": {"riskfree": DEFAULT_RISKFREE},  # Default risk-free rate
                    "volatility": {}
                }
            
            # Aggiungi i dati dell'equity
            self.market_data[current_date]["equity"][symbol] = {
                "price": row["price"],
                "div_yield": row["dividend"],
                "is_valid": True
            }
        return self.market_data
    
    def _fill_vols(self, symbol):
        vols_df = pd.read_csv(f'../data/volatilities/{symbol}_ivol.csv').iloc[:, 1:]
        vols_df['reference_date'] = pd.to_datetime(vols_df['reference_date']).dt.date
        vols_df = vols_df[(vols_df['reference_date'] >= self.start_date)& (vols_df['reference_date'] <= self.end_date)].copy()

        day_count = ql.Actual365Fixed()
        calendar = ql.TARGET()

        available_dates = vols_df['reference_date'].unique()
        for current_date in available_dates:
            if current_date not in self.market_data:
                self.market_data[current_date] = {
                    "ref_date": current_date,
                    "equity": {},
                    "rate": {"riskfree": DEFAULT_RISKFREE},  # Default risk-free rate
                    "volatility": {}
                }
            vols_df_tmp = vols_df[vols_df['reference_date'] == current_date].copy().reset_index(drop=True)
            try:
                spot_price = self.market_data[current_date]['equity'][symbol]['price']
            except:
                self.market_data[current_date]["equity"][symbol] = {
                                                        "price": 0,
                                                        "div_yield": 0,
                                                        "is_valid": False
                    }
                continue
            try: 
                moneyness = vols_df_tmp['moneyness'].unique()
                strikes = (moneyness*spot_price).tolist()
                tenors = vols_df_tmp['tenor'].unique().tolist()
                expiration_dates = [ql.Date.from_date(current_date) + ql.Period(t) for t in tenors]
                implied_vols = ql.Matrix(len(strikes), len(expiration_dates))
                for i in range(implied_vols.rows()):
                    for j in range(implied_vols.columns()):
                        implied_vols[i][j] = vols_df_tmp[(vols_df_tmp['moneyness'] == moneyness[i])&(vols_df_tmp['tenor'] == tenors[j])]['implied_vol'].values[0]

                black_var_surface = ql.BlackVarianceSurface(ql.Date.from_date(current_date), calendar,
                                                            expiration_dates, strikes,
                                                            implied_vols, day_count)
                black_var_surface.setInterpolation("bicubic")
                black_var_surface.enableExtrapolation()

                self.market_data[current_date]['volatility'][symbol] = black_var_surface
            except:
                self.market_data[current_date]['volatility'][symbol] = None
    
    def build(self, symbol):
        self._fill_prices(symbol)
        self._fill_vols(symbol)


