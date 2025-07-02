from enum import Enum


class OrderType(Enum):
    BUY = "buy"
    SELL = "sell"

class PositionType(Enum):
    LONG = 1
    SHORT = -1

class OptionType(Enum):
    CALL = 1
    PUT = 0

class AssetType(Enum):
    EQUITY = 'equity'
    BOND = "bond"
    OPTION = "option"