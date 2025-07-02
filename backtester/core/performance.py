import pandas as pd
import matplotlib.pyplot as plt
import numpy as np 
from datetime import datetime 



class Analytics:
    def __init__(self, backtester):
        """
        Inizializza l'analizzatore con i dati delle posizioni del backtester.
        
        :param trades_df: DataFrame delle posizioni di backtest con colonne come 'ref_date', 'global_pnl', etc.
        """
        self.backtester = backtester
        self.trades_df = backtester.positions_summary.copy()
        self.period_pnl = backtester.period_pnl.copy()

    def plot_pnl(self, benchmark=None):
        """
        Plotta il P&L totale del portafoglio nel tempo.
        """
        dates = pd.to_datetime(self.period_pnl['ref_date']).to_list()
        plt.figure(figsize=(12, 6))
        plt.plot(dates, self.period_pnl['daily_pnl'], label="Global P&L", color="blue")
        if benchmark is not None:
            dates2 = pd.to_datetime(benchmark.period_pnl['ref_date']).to_list()
            plt.plot(dates2, benchmark.period_pnl['daily_pnl'], label="Benchmark P&L", color="green")
        plt.axhline(self.period_pnl.iloc[0,1], color='black', linestyle='--', linewidth=1)
        plt.xlabel("Date")
        plt.ylabel("Total P&L")
        plt.title("Portfolio P&L Over Time")
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_price(self, ticker,
               plot_signals=True,
               factor=None,
               start_date=None,
               end_date=None):
        # Serie dei prezzi di chiusura
        price_series = self.backtester.prices_to_df('close')[ticker]
        price_series.index = pd.to_datetime(price_series.index)

        # Filtro per date se richiesto
        if start_date is not None or end_date is not None:
            sd = pd.to_datetime(start_date) if start_date is not None else price_series.index.min()
            ed = pd.to_datetime(end_date)   if end_date   is not None else price_series.index.max()
            price_series = price_series.loc[sd:ed]

        plt.figure(figsize=(12, 6))
        plt.plot(price_series.index, price_series.values,
                label=ticker, color="black")

        # Fattore aggiuntivo (se richiesto)
        if factor is not None:
            factor_series = self.backtester.factors_history[factor][ticker]
            factor_series.index = pd.to_datetime(factor_series.index)
            if start_date is not None or end_date is not None:
                factor_series = factor_series.loc[sd:ed]
            plt.plot(factor_series.index, factor_series.values,
                    label=factor, color="blue")

        if plot_signals:
            # recupero df dei segnali: indice a date, colonna 'signal' con -1,0,+1
            signal_df = self.signals(ticker)
            signal_df.index = pd.to_datetime(signal_df.index)

            # filtro segnali per date
            if start_date is not None or end_date is not None:
                signal_df = signal_df.loc[sd:ed]

            # riallineo i segnali ai prezzi (inner join)
            aligned = signal_df.join(price_series.rename("price"), how="inner")

            # separo i 3 casi
            buys   = aligned[ aligned['signal'] ==  1 ]
            closes = aligned[ aligned['signal'] ==  0 ]
            sells  = aligned[ aligned['signal'] == -1 ]

            # plotto i marker
            plt.scatter(buys.index,   buys['price'],   marker='^', s=100,
                        label="Buy",  c='green', edgecolors='green')
            plt.scatter(sells.index,  sells['price'],  marker='v', s=100,
                        label="Sell", c='red',  edgecolors='red')
            plt.scatter(closes.index, closes['price'], marker='o', s=100,
                        label="Close", c='gray', edgecolors='gray')

        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.title(f"{ticker} price with signals")
        plt.legend()
        plt.grid(True)
        plt.show()

    def trade_log(self):
        """
        Genera un DataFrame con due righe per ogni trade: una per l'apertura e una per la chiusura.

        :return: DataFrame con trade log dettagliato.
        """
        closed_trades = self.trades_df
        closed_trades['trade_id'].unique()
        trade_log = []

        for trade_id in closed_trades['trade_id'].unique():
            entry_row = closed_trades[(closed_trades['trade_id'] == trade_id) & (closed_trades['is_alive'] == True)].iloc[0]
            exit_row = closed_trades[(closed_trades['trade_id'] == trade_id) & (closed_trades['is_alive'] == False)].iloc[0]

            trade_log.append(entry_row.to_dict())
            trade_log.append(exit_row.to_dict())
        return pd.DataFrame(trade_log)
    
    def signals(self, symbol: str) -> pd.DataFrame:
        """
        Restituisce un DataFrame dei segnali per il simbolo specificato:
        1  = apertura long (buy)
        0  = chiusura di posizione (close)
        -1  = apertura short (sell)
        """
        # 1) filtro per symbol
        df = self.trade_log()
        df_sym = df[df['symbol'] == symbol].copy()
        
        # 2) calcolo del segnale:
        #    quantity == 0 => close (0)
        #    quantity > 0  => apertura: segnale = side (1 per buy, -1 per sell)
        df_sym['signal'] = np.where(
            df_sym['quantity'] == 0,
            0,
            df_sym['side'].clip(-1, 1)  # garantisce -1 o +1
        )
        
        # 3) imposto ref_date come indice e ordino
        df_signals = df_sym.set_index('ref_date').sort_index()[['signal']]
        return df_signals

    def expected_return(self):
            """ Calcola il rendimento medio giornaliero. """
            self.period_pnl[self.period_pnl == 0] = np.nan  
            returns = self.period_pnl['daily_pnl'].pct_change().dropna()
            return returns.mean()

    def std_deviation(self):
        """ Calcola la std dev dei rendimento medi giornalieri. """
        self.period_pnl[self.period_pnl == 0] = np.nan  
        returns = self.period_pnl['daily_pnl'].pct_change().dropna()
        return returns.std()
    
    def sharpe_ratio(self):
        """ Calcola lo Sharpe Ratio del portafoglio con riskfree=0. """
        self.period_pnl[self.period_pnl == 0] = np.nan  
        returns = self.period_pnl['daily_pnl'].pct_change().dropna()
        if returns.std() == 0:
            return np.nan
        return (returns.mean()) / returns.std()

    def win_rate(self):
        """ Calcola la percentuale di trade vincenti. """
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        wins = (closed_trades['closed_pnl'] > 0).sum()
        total = len(closed_trades)
        return wins / total if total > 0 else 0

    def average_pnl(self):
        """ Calcola il profitto medio per trade. """
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        return closed_trades['closed_pnl'].mean()

    def average_win(self):
        """ Calcola il P&L medio dei trade vincenti. """
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        wins = closed_trades[closed_trades['closed_pnl'] > 0]
        # return (wins['global_pnl']/1e6/wins['initial_spot'] ).mean()
        return wins['closed_pnl'].mean()

    def average_loss(self):
        """ Calcola il P&L medio dei trade perdenti. """
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        losses = closed_trades[closed_trades['closed_pnl'] < 0]
        return losses['closed_pnl'].mean()
        # return (losses['global_pnl']/1e6/losses['initial_spot'] ).mean()

    def max_profit(self):
        """ Trova il trade più redditizio. """
        return self.trades_df['closed_pnl'].max()

    def max_loss(self):
        """ Trova la peggior perdita. """
        return self.trades_df['closed_pnl'].min()

    def profit_factor(self):
        """ Calcola il profit factor (profitto totale / perdita totale). """
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        total_wins = closed_trades[closed_trades['closed_pnl'] > 0]['closed_pnl'].sum()
        total_losses = abs(closed_trades[closed_trades['closed_pnl'] < 0]['closed_pnl'].sum())
        return total_wins / total_losses if total_losses > 0 else 1

    def number_of_trades(self):
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        return len(closed_trades['trade_id'].unique())
    
    def max_drawdown(self):
        """
        Calcola il massimo drawdown del portafoglio basato su global_pnl.
        
        :return: Valore massimo del drawdown.
        """
        pnl_series = self.period_pnl['daily_pnl']

        # Calcola il massimo storico fino a quel punto
        running_max = pnl_series.cummax()
        # Evitiamo la divisione per zero sostituendo gli zeri con NaN temporaneamente
        running_max[running_max == 0] = np.nan  
        drawdown = (pnl_series - running_max) / running_max  
        return drawdown.min()
    
    def summary(self):
        """ Restituisce un riassunto delle metriche di performance con 6 decimali formattati come stringhe. """
        return {
            "Expected Return": f"{self.expected_return():.6f}",
            "Std Deviation": f"{self.std_deviation():.6f}",
            "Sharpe Ratio": f"{self.sharpe_ratio():.6f}",
            "N. Trade": self.number_of_trades(),  # Numero intero
            "Win Rate": f"{self.win_rate():.6f}",
            "Average P&L": f"{self.average_pnl():.6f}",
            "Average Win": f"{self.average_win():.6f}",
            "Average Loss": f"{self.average_loss():.6f}",
            "Max Profit": f"{self.max_profit():.6f}",
            "Max Loss": f"{self.max_loss():.6f}",
            "Profit Factor": f"{self.profit_factor():.6f}",
            "Max Drawdown": f"{self.max_drawdown():.6f}",
        }
