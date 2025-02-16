import pandas as pd
import matplotlib.pyplot as plt
import numpy as np 

class ResultAnalyzer:
    def __init__(self, trades_df, period_pnl):
        """
        Inizializza l'analizzatore con i dati delle posizioni del backtester.
        
        :param trades_df: DataFrame delle posizioni di backtest con colonne come 'ref_date', 'global_pnl', etc.
        """
        self.trades_df = trades_df.copy()
        self.period_pnl = period_pnl.copy()
        # self.period_pnl = self.trades_df.groupby('ref_date')['portfolio_value'].sum().reset_index()
        # self.trades_df['ref_date'] = pd.to_datetime(self.trades_df['ref_date'])  # Converte in datetime se non lo è già

    def compute_aggregated_pnl(self):
        """
        Aggrega il P&L per data per ottenere il P&L giornaliero del portafoglio.
        
        :return: DataFrame con il P&L giornaliero aggregato.
        """
        # daily_pnl = self.trades_df.groupby('ref_date')['global_pnl'].sum().reset_index()
        # daily_pnl = daily_pnl.rename(columns={'global_pnl': 'daily_pnl'})
        return self.period_pnl

    def max_drawdown(self):
        """
        Calcola il massimo drawdown del portafoglio basato su global_pnl.
        
        :return: Valore massimo del drawdown.
        """
        daily_pnl = self.compute_aggregated_pnl()
        pnl_series = daily_pnl['daily_pnl']

        # Calcola il massimo storico fino a quel punto
        running_max = pnl_series.cummax()
        # Evitiamo la divisione per zero sostituendo gli zeri con NaN temporaneamente
        running_max[running_max == 0] = np.nan  
        drawdown = (pnl_series - running_max) / running_max  

        return drawdown.min()  # Il valore minimo è il drawdown massimo

    def plot_pnl(self):
        """
        Plotta il P&L totale del portafoglio nel tempo.
        """
        daily_pnl = self.compute_aggregated_pnl()

        plt.figure(figsize=(12, 6))
        plt.plot(daily_pnl['ref_date'], daily_pnl['daily_pnl'], label="Global P&L", color="blue")
        plt.axhline(self.period_pnl.iloc[0,1], color='black', linestyle='--', linewidth=1)
        plt.xlabel("Date")
        plt.ylabel("Total P&L")
        plt.title("Portfolio P&L Over Time")
        plt.legend()
        plt.grid(True)
        plt.show()

    def get_trade_log(self):
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

                # return pd.DataFrame(trade_log)

            return pd.DataFrame(trade_log)

    def expected_return(self):
        """ Calcola il rendimento medio giornaliero. """
        daily_pnl = self.compute_aggregated_pnl()
        daily_pnl[daily_pnl == 0] = np.nan  
        returns = daily_pnl['daily_pnl'].pct_change().dropna()
        return returns.mean()

    def std_deviation(self):
        """ Calcola la std dev dei rendimento medi giornalieri. """
        daily_pnl = self.compute_aggregated_pnl()
        daily_pnl[daily_pnl == 0] = np.nan  
        returns = daily_pnl['daily_pnl'].pct_change().dropna()
        return returns.std()
    
    def sharpe_ratio(self):
        """ Calcola lo Sharpe Ratio del portafoglio con riskfree=0. """
        daily_pnl = self.compute_aggregated_pnl()
        daily_pnl[daily_pnl == 0] = np.nan  
        returns = daily_pnl['daily_pnl'].pct_change().dropna()
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
        return wins['closed_pnl'].mean()

    def average_loss(self):
        """ Calcola il P&L medio dei trade perdenti. """
        closed_trades = self.trades_df[self.trades_df['is_alive'] == False]
        losses = closed_trades[closed_trades['closed_pnl'] < 0]
        return losses['closed_pnl'].mean()

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

    def summary(self):
        """ Restituisce un riassunto delle metriche di performance. """
        return {
            "Expected Return": self.expected_return(),
            "Sharpe Ratio": self.sharpe_ratio(),
            "Win Rate": self.win_rate(),
            "Average P&L": self.average_pnl(),
            "Average Win": self.average_win(),
            "Average Loss": self.average_loss(),
            "Max Profit": self.max_profit(),
            "Max Loss": self.max_loss(),
            "Profit Factor": self.profit_factor(),
            "Max Drawdown": self.max_drawdown(),
        }

