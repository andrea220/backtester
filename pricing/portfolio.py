from .positions import Position

class Portfolio:
    def __init__(self):
        self.positions = []  # Lista delle posizioni attive
        self.open_pnl = 0
        self.closed_pnl = 0

    def add_position(self, position: Position):
        """Aggiunge una posizione al portafoglio."""
        self.positions.append(position)

    def remove_position(self, position: Position):
        """Rimuove una posizione dal portafoglio."""
        if position in self.positions:
            self.positions.remove(position)

    def calculate_total_value(self, market_data: dict) -> float:
        """Calcola il valore totale del portafoglio sommando il valore di tutte le posizioni."""
        return sum(position.calculate_value(market_data) * position.quantity * position.position_type.value for position in self.positions)
    
    def get_closed_pnl(self) -> float:
        """Calcola il profit and loss totale del portafoglio."""
        return sum(position.closed_pnl for position in self.positions)
    
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
                "trade_date": position.trade_date,
                "symbol": position.symbol,
                "type": position.asset_type.value,
                "side": position.position_type.value,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "current_value": position.calculate_value(market_data),
                "open_pnl": open_pnl,
                "closed_pnl": position.closed_pnl,
                "global_pnl": open_pnl + position.closed_pnl
            })
        return summary
    
    def update_portfolio(self, market_data):
        # controlla se c'è un expiry o esercizio o un evento che genera pnl (es coupon)
        pass

    def close_all_positions(self):
        """Chiude tutte le posizioni rimuovendole dal portafoglio."""
        self.positions.clear()
