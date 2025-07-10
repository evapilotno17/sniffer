from enum import Enum

BASE_URL = "https://data-api.polymarket.com"

class Endpoint(str, Enum):
    def __str__(self) -> str: 
        return self.value

    def __repr__(self) -> str:
        return self.value

    POSITIONS = "positions"
    ACTIVITY  = "activity"
    HOLDERS   = "holders"
    VALUE     = "value"
    TRADES    = "trades"



class SortDir(str, Enum):
    ASC  = "ASC"
    DESC = "DESC"


class PosSortBy(str, Enum):
    TOKENS       = "TOKENS"
    CURRENT      = "CURRENT"
    INITIAL      = "INITIAL"
    CASHPNL      = "CASHPNL"
    PERCENTPNL   = "PERCENTPNL"
    TITLE        = "TITLE"
    RESOLVING    = "RESOLVING"
    PRICE        = "PRICE"


class ActType(str, Enum):
    TRADE     = "TRADE"
    SPLIT     = "SPLIT"
    MERGE     = "MERGE"
    REDEEM    = "REDEEM"
    REWARD    = "REWARD"
    CONVERSION = "CONVERSION"


class ActSortBy(str, Enum):
    TIMESTAMP = "TIMESTAMP"
    TOKENS    = "TOKENS"
    CASH      = "CASH"


class TradeSide(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"


class FilterType(str, Enum):
    CASH = "CASH"
    TOKENS = "TOKENS"
