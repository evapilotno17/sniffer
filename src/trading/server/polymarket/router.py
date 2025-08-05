from fastapi import APIRouter, HTTPException, Depends
# from runtime.manager import StrategyManager
from trading.strategies.polymarket.nothing_ever_happens import NothingEverHappens
from pydantic import BaseModel
from typing import Dict, Optional
from trading.datamodel.strategy import StrategyState

"""
    
"""

router = APIRouter(prefix="/polymarket", tags=["Polymarket"])


# asset routes

@router.get("/asset")
def get_asset(asset_id: str):
    return {
        "todo": "implement"
    }

@router.get("/asset/list")
def list_assets():
    return {
        "todo": "implement"
    }


# strategy routes

@router.get("/strategy/list")
def list_strategies():
    return {
        "todo": "implement"
    }

@router.get("/strategy")
def get_strategy(strategy_id: str):
    return {
        "todo": "implement"
    }

@router.post("/strategy/create")
def create_strategy(strategy_id: str):
    return {
        "todo": "implement"
    }

@router.post("/strategy/update")
def update_strategy(strategy_id: str):
    return {
        "todo": "implement"
    }
