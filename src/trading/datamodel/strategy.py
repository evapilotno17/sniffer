from pydantic import BaseModel
from typing import List, Dict, Any, Union
from datetime import datetime


# combination of strategy and the portfolio that it controls
class StrategyState(BaseModel):
    name: str
    strategy_path: str
    allocation_usd: float 
    strategy_id: str = None
    cash_usd: float = None
    rebalance_interval_seconds: int = 60 * 60
    portfolio_id: str = None
    holdings_value_usd: float = None
    total_value_usd: float = None
    pnl: float = None
    max_pnl: float = None
    min_pnl: float = None
    paper: bool = True
    last_rebalance_at: datetime = None
    spec: Dict[str, Any] = None
