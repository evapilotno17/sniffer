from pydantic import BaseModel, Field
from typing import Optional, List
from polymarket.gamma_api.constants import SortDir

class MarketRequest(BaseModel):
    limit: Optional[int] = None
    offset: Optional[int] = None
    order: Optional[str] = None
    ascending: Optional[bool] = None
    id: Optional[List[int]] = None
    slug: Optional[List[str]] = None
    archived: Optional[bool] = None
    active: Optional[bool] = None
    closed: Optional[bool] = None
    clob_token_ids: Optional[List[str]] = Field(None, alias='clob_token_ids')
    condition_ids: Optional[List[str]] = Field(None, alias='condition_ids')
    liquidity_num_min: Optional[float] = Field(None, alias='liquidity_num_min')
    liquidity_num_max: Optional[float] = Field(None, alias='liquidity_num_max')
    volume_num_min: Optional[float] = Field(None, alias='volume_num_min')
    volume_num_max: Optional[float] = Field(None, alias='volume_num_max')
    start_date_min: Optional[str] = Field(None, alias='start_date_min')
    start_date_max: Optional[str] = Field(None, alias='start_date_max')
    end_date_min: Optional[str] = Field(None, alias='end_date_min')
    end_date_max: Optional[str] = Field(None, alias='end_date_max')
    tag_id: Optional[int] = Field(None, alias='tag_id')
    related_tags: Optional[bool] = Field(None, alias='related_tags')

class EventRequest(BaseModel):
    limit: Optional[int] = None
    offset: Optional[int] = None
    order: Optional[str] = None
    ascending: Optional[bool] = None
    id: Optional[List[int]] = None
    slug: Optional[List[str]] = None
    archived: Optional[bool] = None
    active: Optional[bool] = None
    closed: Optional[bool] = None
    liquidity_min: Optional[float] = Field(None, alias='liquidity_min')
    liquidity_max: Optional[float] = Field(None, alias='liquidity_max')
    volume_min: Optional[float] = Field(None, alias='volume_min')
    volume_max: Optional[float] = Field(None, alias='volume_max')
    start_date_min: Optional[str] = Field(None, alias='start_date_min')
    start_date_max: Optional[str] = Field(None, alias='start_date_max')
    end_date_min: Optional[str] = Field(None, alias='end_date_min')
    end_date_max: Optional[str] = Field(None, alias='end_date_max')
    tag: Optional[str] = None
    tag_id: Optional[int] = Field(None, alias='tag_id')
    related_tags: Optional[bool] = Field(None, alias='related_tags')
    tag_slug: Optional[str] = Field(None, alias='tag_slug')
