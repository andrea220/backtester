import pandas as pd 
from pathlib import Path
# from datetime import date
# import QuantLib as ql 
import json

DATA_PATH = "C:/Users/S542279/Desktop/backtester/backtester/data/"

def get_file_names(path):
    folder_path = Path(path)
    all_items = [item.name for item in folder_path.iterdir()]
    return all_items

class MarketData:

    def __init__(self):

        self.prices_path = DATA_PATH + "prices"
        self.vols_path = DATA_PATH + "volatilities"
        self.data_path = DATA_PATH
        
        self.market_data = {}

    def _fill_prices(self):
        """
        Generate a market data dictionary from a given prices DataFrame.
        The market data contains equity prices and dividend yields.
        """
        all_file_prices = get_file_names(self.prices_path)
        for file in all_file_prices:
            symbol = file.replace(".xlsx","")
            prices_df = pd.read_excel(f"{self.prices_path}/{file}", index_col=0)
            prices_df.index = pd.to_datetime(prices_df.index, format='%d/%m/%y').date
            prices_df.fillna(0, inplace=True)

            # Itera sul DataFrame per riempire il dizionario market_data
            for ix, row in prices_df.iterrows():
                current_date = ix.isoformat()
                
                # Inizializza la data se non esiste già nel dizionario
                if current_date not in self.market_data:
                    self.market_data[current_date] = {
                                                    "ref_date": current_date,
                                                    "equity": {},
                                                    "rate": {"riskfree": None},  
                                                    "volatility": {}
                                                }
                
                # Aggiungi i dati dell'equity
                self.market_data[current_date]["equity"][symbol] = {
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "div_yield": float(row["dividend"]),
                    "is_valid": True
                }

    def _fill_vols(self):
        all_file_vols = get_file_names(self.vols_path)
        for file in all_file_vols:
            symbol = file.replace(".xlsx","")
            symbol = symbol.replace("_ivol","")
            vols_df = pd.read_excel(f"{self.vols_path}/{file}", index_col=0)
            vols_df.index = pd.to_datetime(vols_df.index, format='%d/%m/%y').date

            available_dates = vols_df.index.unique().values
            for current_date in available_dates:
                if current_date.isoformat() not in self.market_data:
                    self.market_data[current_date.isoformat()] = {
                        "ref_date": current_date.isoformat(),
                        "equity": {},
                        "rate": {"riskfree": None},  # Default risk-free rate
                        "volatility": {}
                    }

                vols_df_tmp = vols_df.loc[current_date].copy()
                # vols_df_tmp.fillna("nan", inplace=True)
                vols_df_tmp["tenor"] = vols_df_tmp["tenor"].str.replace("D", "").astype(int)

                moneyness = vols_df_tmp['moneyness'].tolist()
                tenors = vols_df_tmp['tenor'].tolist()
                vol_pivot = vols_df_tmp.pivot(index="moneyness", columns="tenor", values="implied_vol")
                moneyness = vol_pivot.index.tolist()
                tenors = vol_pivot.columns.tolist()
                vols = vol_pivot.values.tolist()

                self.market_data[current_date.isoformat()]['volatility'][symbol] = {
                        "ref_date": current_date.isoformat(),
                        "moneyness": moneyness,
                        "tenor": tenors,
                        "volatility": vols,
                        "is_valid": True
                    }
                                                                        
    def build(self):
        self._fill_prices()
        self._fill_vols()

        with open(f"{self.data_path}MarketData.json", "w") as json_file:
            json.dump(self.market_data, json_file, indent=4)

    def load_market_data(self, rebuild=False):
        if rebuild:
            print("*****")
            print("Building MarketData...")
            self.build()
            print("Done!")
            print("*****")
            return 
        
        with open(self.data_path + "MarketData.json", "r", encoding="utf-8") as file:
            self.market_data = json.load(file)

        
    