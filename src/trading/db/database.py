from trading.db.config import engine, SessionLocal, Base, DATABASE_URL
from utils import logger, footprint
from contextlib import contextmanager
from sqlalchemy import text, create_engine
from trading.db.polymarket import (
    OrderResult,
    Position,
    Portfolio,
    PortfolioSnapshot,
    Strategy,
    Asset
)
import os
import duckdb
import pandas as pd

@footprint()
def create_tables():
    """Create all tables in the database"""
    logger.info("creating tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("tables created successfully!")

@footprint()
def drop_tables():
    """drop all tables in the database"""
    logger.info("dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("tables dropped successfully!")

@footprint()
def get_table(table_name: str):
    return pd.read_sql_table(table_name, engine)

def get_db_session():
    """get a new database session"""
    return SessionLocal()

@contextmanager
def get_db():
    """context manager for database sessions with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"database error: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

def init_db():
    """initialize the database with tables"""
    logger.info("initializing Polymarket Trader Database...")
    create_tables()
    
    # Test the connection
    try:
        with get_db() as db:
            result = db.execute(text("SELECT 1")).fetchone()
            print("database connection test successful!")
    except Exception as e:
        print(f"database connection test failed: {e}")
        raise
    
    print("database initialized and ready to uwax!")

def reset_db():
    """reset the database (drop and recreate tables)"""
    print("🔄 resetting database...")
    drop_tables()
    create_tables()
    print("database reset complete!")

def get_db_info():
    """get information about the database"""
    import sqlite3
    
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    if not os.path.exists(db_path):
        print(f"database file: {db_path} (not created yet)")
        return
    
    # Get file size
    file_size = os.path.getsize(db_path)
    print(f"database file: {db_path}")
    print(f"file size: {file_size:,} bytes")
    
    # Get table info
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"🗂️  Tables ({len(tables)}):")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   • {table_name}: {count:,} rows")

# Utility functions for common operations
def create_sample_portfolio(portfolio_name: str = "test_strategy", 
                          strategy_path: str = "strategies.test.TestStrategy",
                          initial_cash: float = 1000.0,
                          is_paper: bool = True):
    """Create a sample portfolio for testing"""
    from trading.db.polymarket import Portfolio

    with get_db() as db:
        portfolio = Portfolio(
            # strategy_path=strategy_path,
            allocation_usd=initial_cash,
            cash_usd=initial_cash,
            paper=is_paper
        )
        db.add(portfolio)
        db.flush()  # Get the ID without committing
        
        print(f"created portfolio: {portfolio.id}")
        print(f"   cash: ${portfolio.cash_usd:,.2f}")
        print(f"   paper trading: {portfolio.paper}")
        
        return portfolio

if __name__ == "__main__":
    print("polymarket trader database setup")
    print("=" * 50)
    
    # Initialize database
    init_db()

    print("\ndatabase info:")
    get_db_info()
    
    print("\ncreating sample portfolio...")
    sample_portfolio = create_sample_portfolio()
    
    print("\ndatabase setup complete")