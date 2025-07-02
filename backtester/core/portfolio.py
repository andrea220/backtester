from .position import Position
from .utils import *
import numpy as np

class Portfolio:
    def __init__(self):
        self.positions = []  # Lista delle posizioni attive
        self.open_pnl = 0

    def add_position(self, position: Position):
        """Aggiunge una posizione al portafoglio."""
        self.positions.append(position)

    def calculate_total_value(self, market_data: dict) -> float:
        """Calcola il valore totale del portafoglio sommando il valore di tutte le posizioni."""
        return sum(position.calculate_value(market_data) * position.quantity * position.position_type.value for position in self.positions)
    
    def get_closed_pnl(self) -> float:
        """Calcola il profit and loss totale del portafoglio."""
        return sum(position.closed_pnl for position in self.positions)
    
    def get_initial_ctv(self) -> float:
        return sum(position.initial_ctv for position in self.positions)
    
    def calculate_open_pnl(self, market_data: dict) -> float:
        """Calcola il profit and loss totale del portafoglio."""
        return sum(position.calculate_pnl(market_data) for position in self.positions)
    
    def global_pnl(self, market_data: dict):
        open_pnl = sum(position.calculate_pnl(market_data) for position in self.positions)  
        closed_pnl = sum(position.closed_pnl for position in self.positions)
        return open_pnl + closed_pnl      

    def get_positions_summary(self, market_data: dict):
        """Restituisce un riepilogo delle posizioni nel portafoglio."""
        summary = []
        for position in self.positions:
            open_pnl = position.calculate_pnl(market_data)
            summary.append({
                "ref_date": market_data['ref_date'],
                "trade_date": position.trade_date,
                "trade_id": position.trade_id,
                "symbol": position.symbol,
                "type": position.asset_type.value,
                "side": position.position_type.value,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "is_alive": position.is_open,
                "current_value": position.calculate_value(market_data),
                "open_pnl": open_pnl,
                "closed_pnl": position.closed_pnl,
                "global_pnl": open_pnl + position.closed_pnl
            })
        return summary
    
    def get_positions(self, symbol: str, position_type: AssetType) -> list:
        """
        Restituisce tutte le posizioni associate a un determinato simbolo e tipo di posizione.

        :param positions: Lista di oggetti Position.
        :param symbol: Simbolo dell'asset da cercare.
        :param position_type: Tipo di posizione (LONG o SHORT).
        :return: Lista di posizioni con il simbolo e il tipo specificato.
        """
        filtered_positions = []
        for position in self.positions:
            if position.symbol == symbol and position.asset_type == position_type:
                filtered_positions.append(position)
        return filtered_positions
    
    def position_quantity(self, symbol: str, position_type: AssetType):
        ''' 
        restituisce la quantità totale delle posizioni per una tupla symbol-assettype
        '''
        positions = self.get_positions(symbol=symbol, position_type=position_type)
        return np.sum([pos.quantity for pos in positions])
        
    def close_all_positions(self, market_data: dict):
        for pos in self.positions:
            if pos.is_open:
                pos.close_position(market_data) 

    def close_positions(self, ticker, position_type, market_data: dict):
        positions = self.get_positions(symbol=ticker, position_type=position_type)
        for pos in positions:
            pos.close_position(market_data) 
