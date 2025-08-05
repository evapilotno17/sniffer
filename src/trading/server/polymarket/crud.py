from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Type, Dict, Any
from trading.db import polymarket as db_models
from trading.datamodel import strategy as strategy_datamodel
from trading.datamodel import polymarket as polymarket_datamodel

# region Asset
def get_asset(db: Session, asset_id: str) -> Optional[db_models.Asset]:
    return db.query(db_models.Asset).filter(db_models.Asset.asset_id == asset_id).first()

def get_all_assets(db: Session, skip: int = 0, limit: int = 100) -> List[db_models.Asset]:
    return db.query(db_models.Asset).offset(skip).limit(limit).all()

def create_asset(db: Session, asset_id: str, event_id: str, last_price: Optional[float] = None, condition_id: Optional[str] = None, slug: Optional[str] = None, outcome: Optional[str] = None, end_date: Optional[str] = None) -> db_models.Asset:
    db_asset = db_models.Asset(
        asset_id=asset_id,
        last_price=last_price,
        event_id=event_id,
        condition_id=condition_id,
        slug=slug,
        outcome=outcome,
        end_date=end_date
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

def update_asset(db: Session, asset_id: str, update_data: Dict[str, Any]) -> Optional[db_models.Asset]:
    db_asset = get_asset(db, asset_id)
    if db_asset:
        for key, value in update_data.items():
            if hasattr(db_asset, key):
                setattr(db_asset, key, value)
        db.commit()
        db.refresh(db_asset)
    return db_asset
# endregion

# region OrderResult
def create_order_result(db: Session, order: polymarket_datamodel.OrderResult, portfolio_id: str) -> db_models.OrderResult:
    order_data = order.order
    db_order = db_models.OrderResult(
        asset_id=order_data.token_id,
        expected_price=order_data.expected_price,
        actual_price=float(order.takingAmount) / float(order.makingAmount) if order.success else 0,
        amount_usd=order_data.amount_usd if isinstance(order_data, polymarket_datamodel.MarketBuy) else 0,
        amount_shares=order_data.amount_shares if isinstance(order_data, polymarket_datamodel.MarketSell) else 0,
        side=db_models.OrderSide.BUY if isinstance(order_data, polymarket_datamodel.MarketBuy) else db_models.OrderSide.SELL,
        type=db_models.OrderType.FOK, 
        paper=order_data.virtual,
        success=order.success,
        error_msg=order.errorMsg,
        portfolio_id=portfolio_id,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def get_order_result(db: Session, order_id: str) -> Optional[db_models.OrderResult]:
    return db.query(db_models.OrderResult).filter(db_models.OrderResult.id == order_id).first()

def get_all_order_results_for_portfolio(db: Session, portfolio_id: str, skip: int = 0, limit: int = 100) -> List[db_models.OrderResult]:
    return db.query(db_models.OrderResult).filter(db_models.OrderResult.portfolio_id == portfolio_id).offset(skip).limit(limit).all()
# endregion

# region Position
def get_position(db: Session, portfolio_id: str, asset_id: str) -> Optional[db_models.Position]:
    return db.query(db_models.Position).filter(
        db_models.Position.portfolio_id == portfolio_id,
        db_models.Position.asset_id == asset_id
    ).first()

def get_all_positions_for_portfolio(db: Session, portfolio_id: str) -> List[db_models.Position]:
    return db.query(db_models.Position).filter(db_models.Position.portfolio_id == portfolio_id).all()

def create_or_update_position(db: Session, portfolio_id: str, asset_id: str, amount_shares: float, avg_price: float, paper: bool) -> db_models.Position:
    db_position = get_position(db, portfolio_id, asset_id)
    if db_position:
        db_position.amount_shares += amount_shares
        # Update avg_price logic might be more complex, this is a simplification
        db_position.avg_price = avg_price 
    else:
        db_position = db_models.Position(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            amount_shares=amount_shares,
            avg_price=avg_price,
            paper=paper
        )
        db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

def delete_position(db: Session, portfolio_id: str, asset_id: str) -> bool:
    db_position = get_position(db, portfolio_id, asset_id)
    if db_position:
        db.delete(db_position)
        db.commit()
        return True
    return False
# endregion

# region Portfolio
def get_portfolio(db: Session, portfolio_id: str) -> Optional[db_models.Portfolio]:
    return db.query(db_models.Portfolio).filter(db_models.Portfolio.id == portfolio_id).first()

def get_all_portfolios(db: Session, skip: int = 0, limit: int = 100) -> List[db_models.Portfolio]:
    return db.query(db_models.Portfolio).offset(skip).limit(limit).all()

def update_portfolio(db: Session, portfolio_id: str, update_data: Dict[str, Any]) -> Optional[db_models.Portfolio]:
    db_portfolio = get_portfolio(db, portfolio_id)
    if db_portfolio:
        for key, value in update_data.items():
            setattr(db_portfolio, key, value)
        db.commit()
        db.refresh(db_portfolio)
    return db_portfolio

def delete_portfolio(db: Session, portfolio_id: str) -> bool:
    db_portfolio = get_portfolio(db, portfolio_id)
    if db_portfolio:
        db.delete(db_portfolio)
        db.commit()
        return True
    return False
# endregion

# region PortfolioSnapshot
def create_portfolio_snapshot(db: Session, portfolio_id: str) -> db_models.PortfolioSnapshot:
    portfolio = get_portfolio(db, portfolio_id)
    if not portfolio:
        raise ValueError(f"Portfolio with id {portfolio_id} not found")

    snapshot = db_models.PortfolioSnapshot(
        portfolio_id=portfolio.id,
        cash_usd=portfolio.cash_usd,
        holdings_value_usd=portfolio.holdings_value_usd,
        total_value_usd=portfolio.total_value_usd,
        pnl=portfolio.pnl
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot

def get_all_snapshots_for_portfolio(db: Session, portfolio_id: str, skip: int = 0, limit: int = 100) -> List[db_models.PortfolioSnapshot]:
    return db.query(db_models.PortfolioSnapshot).filter(db_models.PortfolioSnapshot.portfolio_id == portfolio_id).offset(skip).limit(limit).all()
# endregion

# region Strategy
def get_strategy(db: Session, strategy_id: str) -> Optional[db_models.Strategy]:
    return db.query(db_models.Strategy).filter(db_models.Strategy.id == strategy_id).first()

def get_strategy_by_name(db: Session, name: str) -> Optional[db_models.Strategy]:
    return db.query(db_models.Strategy).filter(db_models.Strategy.name == name).first()

def get_all_strategies(db: Session, skip: int = 0, limit: int = 100) -> List[db_models.Strategy]:
    return db.query(db_models.Strategy).options(joinedload(db_models.Strategy.portfolio)).offset(skip).limit(limit).all()

def create_strategy(db: Session, strategy: strategy_datamodel.StrategyState) -> db_models.Strategy:
    # Create the portfolio first
    db_portfolio = db_models.Portfolio(
        allocation_usd=strategy.allocation_usd,
        cash_usd=strategy.allocation_usd, # Initially cash is full allocation
        paper=strategy.paper,
        is_active=True
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)

    # Then create the strategy and link it
    db_strategy = db_models.Strategy(
        name=strategy.name,
        strategy_class=strategy.strategy_path,
        spec=strategy.spec,
        portfolio_id=db_portfolio.id,
        is_active=True
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

def update_strategy(db: Session, strategy_id: str, update_data: Dict[str, Any]) -> Optional[db_models.Strategy]:
    db_strategy = get_strategy(db, strategy_id)
    if db_strategy:
        # Separate portfolio updates from strategy updates
        portfolio_updates = {}
        strategy_updates = {}

        portfolio_keys = [c.name for c in db_models.Portfolio.__table__.columns]
        
        for key, value in update_data.items():
            if key in portfolio_keys and key != 'id':
                portfolio_updates[key] = value
            else:
                strategy_updates[key] = value

        if strategy_updates:
            for key, value in strategy_updates.items():
                setattr(db_strategy, key, value)
        
        if portfolio_updates:
            update_portfolio(db, db_strategy.portfolio_id, portfolio_updates)

        db.commit()
        db.refresh(db_strategy)
    return db_strategy

def delete_strategy(db: Session, strategy_id: str) -> bool:
    db_strategy = get_strategy(db, strategy_id)
    if db_strategy:
        # The portfolio is deleted via CASCADE on the foreign key
        db.delete(db_strategy)
        db.commit()
        return True
    return False
# endregion