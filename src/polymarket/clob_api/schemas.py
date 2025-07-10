from typing import Any, Optional, Literal
from pydantic import BaseModel
from py_order_utils.model import SignedOrder
from polymarket.clob_api.constants import (
    OrderType,
    AssetType,
    ZERO_ADDRESS
)

TickSize = Literal["0.1", "0.01", "0.001", "0.0001"]

class ApiCreds(BaseModel):
    api_key: str
    api_secret: str
    api_passphrase: str


class RequestArgs(BaseModel):
    method: str
    request_path: str
    body: Any = None


class BookParams(BaseModel):
    token_id: str
    side: str = ""


class OrderArgs(BaseModel):
    token_id: str
    price: float
    size: float
    side: str
    fee_rate_bps: int = 0
    nonce: int = 0
    expiration: int = 0
    taker: str = ZERO_ADDRESS


class MarketOrderArgs(BaseModel):
    token_id: str
    amount: float
    side: str
    price: float = 0
    fee_rate_bps: int = 0
    nonce: int = 0
    taker: str = ZERO_ADDRESS
    order_type: OrderType = OrderType.FOK


class TradeParams(BaseModel):
    id: Optional[str] = None
    maker_address: Optional[str] = None
    market: Optional[str] = None
    asset_id: Optional[str] = None
    before: Optional[int] = None
    after: Optional[int] = None


class OpenOrderParams(BaseModel):
    id: Optional[str] = None
    market: Optional[str] = None
    asset_id: Optional[str] = None


class DropNotificationParams(BaseModel):
    ids: Optional[list[str]] = None


class OrderSummary(BaseModel):
    price: Optional[str] = None
    size: Optional[str] = None


class OrderBookSummary(BaseModel):
    market: Optional[str] = None
    asset_id: Optional[str] = None
    timestamp: Optional[str] = None
    bids: Optional[list[OrderSummary]] = None
    asks: Optional[list[OrderSummary]] = None
    hash: Optional[str] = None


class BalanceAllowanceParams(BaseModel):
    asset_type: Optional[AssetType] = None
    token_id: Optional[str] = None
    signature_type: int = -1


class OrderScoringParams(BaseModel):
    orderId: str


class OrdersScoringParams(BaseModel):
    orderIds: list[str]


class CreateOrderOptions(BaseModel):
    tick_size: TickSize
    neg_risk: bool


class PartialCreateOrderOptions(BaseModel):
    tick_size: Optional[TickSize] = None
    neg_risk: Optional[bool] = None


class RoundConfig(BaseModel):
    price: float
    size: float
    amount: float


class ContractConfig(BaseModel):
    exchange: str
    collateral: str
    conditional_tokens: str


class PostOrdersArgs(BaseModel):
    order: SignedOrder
    orderType: OrderType = OrderType.GTC
