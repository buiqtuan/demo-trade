from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class User(Base):
    """
    User model for storing user information from Firebase Auth
    """
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)  # Firebase UID
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"

class Portfolio(Base):
    """
    Portfolio model for storing user's portfolio information
    """
    __tablename__ = "portfolios"

    portfolio_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    cash_balance = Column(Numeric(precision=15, scale=2), nullable=False, default=100000.00)
    initial_balance = Column(Numeric(precision=15, scale=2), nullable=False, default=100000.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Portfolio(portfolio_id={self.portfolio_id}, user_id='{self.user_id}', cash_balance={self.cash_balance})>"

class Asset(Base):
    """
    Asset model for storing information about tradeable assets (stocks)
    """
    __tablename__ = "assets"

    asset_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False, default="STOCK")  # STOCK, ETF, etc.
    exchange = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Numeric(precision=20, scale=2))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    holdings = relationship("Holding", back_populates="asset")
    transactions = relationship("Transaction", back_populates="asset")
    
    def __repr__(self):
        return f"<Asset(symbol='{self.symbol}', name='{self.name}')>"

class Holding(Base):
    """
    Holding model for storing user's stock positions
    """
    __tablename__ = "holdings"

    holding_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.asset_id"), nullable=False, index=True)
    quantity = Column(Numeric(precision=15, scale=6), nullable=False, default=0)
    average_cost_basis = Column(Numeric(precision=15, scale=4), nullable=False)
    total_cost = Column(Numeric(precision=15, scale=2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    asset = relationship("Asset", back_populates="holdings")
    
    def __repr__(self):
        return f"<Holding(portfolio_id={self.portfolio_id}, asset_id={self.asset_id}, quantity={self.quantity})>"

class Transaction(Base):
    """
    Transaction model for storing all trading transactions
    """
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.asset_id"), nullable=False, index=True)
    transaction_type = Column(String(10), nullable=False)  # 'BUY' or 'SELL'
    quantity = Column(Numeric(precision=15, scale=6), nullable=False)
    price_per_unit = Column(Numeric(precision=15, scale=4), nullable=False)
    total_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    fees = Column(Numeric(precision=10, scale=2), default=0.00)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Optional fields for tracking performance
    market_price_at_execution = Column(Numeric(precision=15, scale=4))
    execution_notes = Column(Text)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    asset = relationship("Asset", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(transaction_id={self.transaction_id}, type='{self.transaction_type}', quantity={self.quantity})>"

class MarketData(Base):
    """
    MarketData model for storing historical price data
    """
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(10), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open_price = Column(Numeric(precision=15, scale=4), nullable=False)
    high_price = Column(Numeric(precision=15, scale=4), nullable=False)
    low_price = Column(Numeric(precision=15, scale=4), nullable=False)
    close_price = Column(Numeric(precision=15, scale=4), nullable=False)
    volume = Column(Numeric(precision=20, scale=0))
    adjusted_close = Column(Numeric(precision=15, scale=4))
    
    def __repr__(self):
        return f"<MarketData(symbol='{self.symbol}', timestamp='{self.timestamp}', close={self.close_price})>"

class UserStats(Base):
    """
    UserStats model for storing user performance statistics
    """
    __tablename__ = "user_stats"

    stats_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_return = Column(Numeric(precision=10, scale=4), default=0.0000)
    total_return_percentage = Column(Numeric(precision=8, scale=4), default=0.0000)
    max_drawdown = Column(Numeric(precision=8, scale=4), default=0.0000)
    current_rank = Column(Integer)
    best_rank = Column(Integer)
    streak_days = Column(Integer, default=0)
    last_trade_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    @property
    def win_rate(self):
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def __repr__(self):
        return f"<UserStats(user_id='{self.user_id}', total_return={self.total_return_percentage}%)>"

class Watchlist(Base):
    """
    Watchlist model for storing user's watched stocks
    """
    __tablename__ = "watchlists"

    watchlist_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.asset_id"), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User")
    asset = relationship("Asset")
    
    def __repr__(self):
        return f"<Watchlist(user_id='{self.user_id}', asset_id={self.asset_id})>" 