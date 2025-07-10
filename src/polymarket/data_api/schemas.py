from pydantic import BaseModel
from typing import Optional, Union
from polymarket.data_api.constants import (
    PosSortBy,
    SortDir,
    ActType,
    ActSortBy,
    TradeSide,
    FilterType,
)

class PositionRequest(BaseModel):
    user: str
    market: Optional[str] = None
    event_id: Optional[str] = None
    size_threshold: Optional[float] = None
    redeemable: Optional[bool] = None
    mergeable: Optional[bool] = None
    title: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_by: Optional[Union[str, PosSortBy]] = None
    sort_dir: Optional[Union[str, SortDir]] = None


class HoldersRequest(BaseModel):
    market: str
    limit: Optional[int] = None
    

class ActivityRequest(BaseModel):
    user: str
    limit: Optional[int] = None
    offset: Optional[int] = None
    market: Optional[str] = None
    type_: Optional[Union[str, ActType]] = None 
    start: Optional[int] = None
    end: Optional[int] = None
    side: Optional[Union[str, TradeSide]] = None
    sort_by: Optional[Union[str, ActSortBy]] = None
    sort_dir: Optional[Union[str, SortDir]] = None

class HoldingsValueRequest(BaseModel):
    user: str
    market: Optional[str] = None


class TradesRequest(BaseModel):
    user: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    taker_only: Optional[bool] = None
    filter_type: Optional[Union[str, FilterType]] = None
    filter_amount: Optional[float] = None
    market: Optional[str] = None
    side: Optional[Union[str, TradeSide]] = None


class Trade(BaseModel):
    proxy_wallet: str
    side: str
    asset: str
    condition_id: str
    size: float
    price: float
    timestamp: int
    title: str
    slug: str
    icon: str
    event_slug: str
    outcome: str
    outcome_index: int
    name: str
    pseudonym: str
    bio: str
    profile_image: str
    profile_image_optimized: str
    transaction_hash: str