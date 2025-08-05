from pydantic import BaseModel
from typing import List, Dict, Any, Union

class PolymarketPosition(BaseModel):
    token_id: str
    event_id: str
    amount: float
    avg_price: float
    cur_price: float = None
    condition_id: str = None
    outcome: str = None
    slug: str = None
    end_date: str = None


class MarketBuy(BaseModel):
    token_id: str
    amount_usd: float
    expected_price: float = None # this is just for information transfer
    event_id: str = None
    condition_id: str = None
    slug: str = None
    end_date: str = None
    virtual: bool = False

class MarketSell(BaseModel):
    token_id: str
    amount_shares: float
    expected_price: float = None # this is just for information transfer
    event_id: str = None
    condition_id: str = None
    slug: str = None
    end_date: str = None
    virtual: bool = False

class LimitOrder(BaseModel):
    token_id: str
    price: float
    size: float
    side: str
    event_id: str = None
    condition_id: str = None
    slug: str = None
    end_date: str = None

class OrderResult(BaseModel):
    order: Union[LimitOrder, MarketBuy, MarketSell]
    errorMsg: str = None
    orderID: str = None
    takingAmount: str = None
    makingAmount: str = None
    status: str = None
    transactionsHashes: List[str] = None
    success: bool = None