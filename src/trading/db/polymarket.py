from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from trading.db.config import Base


def generate_prefixed_id(prefix: str):
    return lambda: f"{prefix}_{str(uuid.uuid4())}"

class PolymarketBase(Base):
    __abstract__ = True
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    additional_info = Column(JSON, nullable=True) 

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(enum.Enum):
    GTK = "GTK"  # Good Till Killed
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


class Asset(PolymarketBase):
    __tablename__ = "polymarket_assets"

    asset_id = Column(String, nullable=False, index=True, primary_key=True) # polymarket's asset id
    last_price = Column(Float, nullable=True, index=True)
    event_id = Column(String, nullable=False, index=True)
    condition_id = Column(String, nullable=True, index=True)
    slug = Column(String, nullable=True, index=True)
    outcome = Column(String, nullable=True, index=True) # "Yes" or "No"
    end_date = Column(String, nullable=True, index=True)
    

# i won't store ongoing orders -> only order results -> so there's no point in having an "order_status" attribute

class OrderResult(PolymarketBase):
    __tablename__ = "polymarket_orders"

    id = Column(String, primary_key=True, nullable=False, index=True, default=generate_prefixed_id("order"))
    
    asset_id = Column(String, ForeignKey("polymarket_assets.asset_id"), nullable=False, index=True)
    
    expected_price = Column(Float, nullable=True, index=True) # hopes and dreams
    actual_price = Column(Float, nullable=False, index=True) # reality
    amount_usd = Column(Float, nullable=False, index=True)
    amount_shares = Column(Float, nullable=False, index=True)
    
    side = Column(Enum(OrderSide), nullable=False)
    type = Column(Enum(OrderType), nullable=False)
    paper = Column(Boolean, nullable=False)
    success = Column(Boolean, nullable=False)
    error_msg = Column(String, nullable=True)
    fee_paid = Column(Float, nullable=True, default=0.0)
    
    # Relationships
    portfolio_id = Column(String, ForeignKey("polymarket_portfolios.id"), nullable=True, index=True)
    portfolio = relationship("Portfolio", back_populates="orders")

class Position(PolymarketBase):
    __tablename__ = "polymarket_positions"
    
    id = Column(String, primary_key=True, nullable=False, index=True, default=generate_prefixed_id("position"))
    asset_id = Column(String, ForeignKey("polymarket_assets.asset_id"), nullable=False, index=True)

    amount_shares = Column(Float, nullable=False, index=True, default=0.0)
    avg_price = Column(Float, nullable=False, index=True)
    paper = Column(Boolean, nullable=False)
    

    # Relationships
    portfolio_id = Column(String, ForeignKey("polymarket_portfolios.id"), nullable=True, index=True)
    portfolio = relationship("Portfolio", back_populates="positions")


# a portfolio can only be managed by atmost one strategy - a portfolio is never shared between strategies
class Portfolio(PolymarketBase):
    __tablename__ = "polymarket_portfolios" 
    
    id = Column(String, primary_key=True, nullable=False, index=True, default=generate_prefixed_id("portfolio"))
    allocation_usd = Column(Float, nullable=False, default=0.0)
    cash_usd = Column(Float, nullable=False, default=0.0)
    paper = Column(Boolean, nullable=False)
    
    # Additional info
    holdings_value_usd = Column(Float, nullable=True, index=True, default=0.0)
    total_value_usd = Column(Float, nullable=True, index=True, default=0.0)
    pnl = Column(Float, nullable=True, index=True, default=0.0)
    max_pnl = Column(Float, nullable=True, index=True, default=0.0)
    min_pnl = Column(Float, nullable=True, index=True, default=0.0)
    
    # Strategy configuration
    is_active = Column(Boolean, nullable=False, default=True)
    last_rebalance_at = Column(DateTime, nullable=True)
    
    # Relationships
    strategy = relationship(
        "Strategy",
        back_populates="portfolio",
        uselist=False
    )
    orders = relationship("OrderResult", back_populates="portfolio")
    positions = relationship("Position", back_populates="portfolio")
    snapshots = relationship("PortfolioSnapshot", back_populates="portfolio")

class PortfolioSnapshot(PolymarketBase):
    __tablename__ = "polymarket_portfolio_snapshots"
    
    id = Column(String, primary_key=True, nullable=False, index=True, default=generate_prefixed_id("portfolio_snapshot"))
    
    # Reference to original portfolio
    portfolio_id = Column(String, ForeignKey("polymarket_portfolios.id"), nullable=False, index=True)
    
    # Snapshot data
    cash_usd = Column(Float, nullable=False)
    holdings_value_usd = Column(Float, nullable=False)
    total_value_usd = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)
    
    portfolio = relationship("Portfolio")


# TODO: make strategies generic. but i'll do this when i add support for traditional markets - no point in making it too generic rn

class Strategy(PolymarketBase):
    __tablename__ = "polymarket_strategies"

    id = Column(String, primary_key=True, default=generate_prefixed_id("strat"))
    name = Column(String, nullable=False, unique=True, index=True)
    strategy_class = Column(String, nullable=False) # loadable pythonpath to strategy class
    
    # JSON blob to hold all strategy-specific parameters
    # e.g., {'look_back_days': 180, 'min_volume': 100000}
    spec = Column(JSON, nullable=False)
    
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Each strategy is linked to one portfolio
    portfolio_id = Column(
        String,
        ForeignKey("polymarket_portfolios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one‑to‑one
    )

    portfolio = relationship(
        "Portfolio",
        back_populates="strategy",
        uselist=False,
    )
