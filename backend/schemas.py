from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# User Schemas
class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="User's username")

class UserCreate(UserBase):
    user_id: str = Field(..., description="Firebase UID")
    display_name: Optional[str] = Field(None, description="User's display name")
    avatar_url: Optional[str] = Field(None, description="User's avatar URL")

class UserResponse(UserBase):
    user_id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

# Asset Schemas
class AssetBase(BaseModel):
    symbol: str = Field(..., max_length=10, description="Stock symbol")
    name: str = Field(..., max_length=255, description="Company name")
    asset_type: str = Field(default="STOCK", description="Asset type")
    exchange: Optional[str] = Field(None, description="Exchange name")

class AssetCreate(AssetBase):
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[Decimal] = None
    description: Optional[str] = None

class AssetResponse(AssetBase):
    asset_id: int
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[Decimal]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Portfolio Schemas
class PortfolioBase(BaseModel):
    cash_balance: Decimal = Field(..., ge=0, description="Current cash balance")
    initial_balance: Decimal = Field(default=Decimal("100000.00"), description="Initial balance")

class PortfolioCreate(PortfolioBase):
    user_id: str

class PortfolioResponse(PortfolioBase):
    portfolio_id: int
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Holding Schemas
class HoldingBase(BaseModel):
    quantity: Decimal = Field(..., ge=0, description="Number of shares")
    average_cost_basis: Decimal = Field(..., gt=0, description="Average cost per share")

class HoldingCreate(HoldingBase):
    portfolio_id: int
    asset_id: int
    total_cost: Decimal

class HoldingResponse(HoldingBase):
    holding_id: int
    portfolio_id: int
    asset_id: int
    total_cost: Decimal
    symbol: str = Field(..., description="Stock symbol from asset")
    name: str = Field(..., description="Company name from asset")
    current_price: Optional[Decimal] = Field(default=Decimal("0.0"), description="Current market price")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionBase(BaseModel):
    transaction_type: str = Field(..., pattern="^(BUY|SELL)$", description="Transaction type")
    quantity: Decimal = Field(..., gt=0, description="Number of shares")
    price_per_unit: Decimal = Field(..., gt=0, description="Price per share")
    total_amount: Decimal = Field(..., description="Total transaction amount")

class TransactionCreate(TransactionBase):
    portfolio_id: int
    asset_id: int
    fees: Optional[Decimal] = Field(default=Decimal("0.00"), description="Transaction fees")
    market_price_at_execution: Optional[Decimal] = None
    execution_notes: Optional[str] = None

class TransactionResponse(TransactionBase):
    transaction_id: int
    portfolio_id: int
    asset_id: int
    fees: Decimal
    timestamp: datetime
    symbol: str = Field(..., description="Stock symbol from asset")
    name: str = Field(..., description="Company name from asset")
    market_price_at_execution: Optional[Decimal]
    execution_notes: Optional[str]

    class Config:
        from_attributes = True

# Trade Request Schema
class TradeRequest(BaseModel):
    ticker: str = Field(..., max_length=10, description="Stock symbol to trade")
    quantity: Decimal = Field(..., gt=0, description="Number of shares to trade")
    action: str = Field(..., pattern="^(BUY|SELL)$", description="Trade action")

class TradeResponse(BaseModel):
    message: str
    transaction_id: int
    execution_price: Decimal
    total_amount: Decimal
    new_cash_balance: Decimal
    total_portfolio_value: Decimal
    symbol: str
    quantity: Decimal
    action: str

# Portfolio Summary Schema
class PortfolioSummary(BaseModel):
    user_id: str
    cash_balance: Decimal
    initial_balance: Decimal
    total_portfolio_value: Decimal
    total_return: Decimal
    total_return_percentage: Decimal
    holdings: List[HoldingResponse]

    class Config:
        from_attributes = True

# Market Data Schemas
class MarketDataBase(BaseModel):
    symbol: str
    timestamp: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Optional[Decimal] = None

class MarketDataResponse(MarketDataBase):
    id: int

    class Config:
        from_attributes = True

# User Statistics Schemas
class UserStatsBase(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_return: Decimal = Decimal("0.0000")
    total_return_percentage: Decimal = Decimal("0.0000")

class UserStatsResponse(UserStatsBase):
    stats_id: int
    user_id: str
    win_rate: float
    max_drawdown: Decimal
    current_rank: Optional[int]
    best_rank: Optional[int]
    streak_days: int
    last_trade_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Leaderboard Schema
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    total_return_percentage: Decimal
    portfolio_value: Decimal
    win_rate: float
    total_trades: int

class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    total_users: int
    user_rank: Optional[int] = None

# Watchlist Schemas
class WatchlistBase(BaseModel):
    notes: Optional[str] = None

class WatchlistCreate(WatchlistBase):
    user_id: str
    asset_id: int

class WatchlistResponse(WatchlistBase):
    watchlist_id: int
    user_id: str
    asset_id: int
    symbol: str
    name: str
    current_price: Optional[Decimal]
    added_at: datetime

    class Config:
        from_attributes = True

# Stock Search Schema
class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str]
    asset_type: str
    current_price: Optional[Decimal]

class StockSearchResponse(BaseModel):
    results: List[StockSearchResult]
    total_results: int

# Price Update Schema
class PriceUpdate(BaseModel):
    symbol: str
    price: Decimal
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    timestamp: datetime
    volume: Optional[int] = None

# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Optional[dict] = None

class PriceUpdateMessage(WebSocketMessage):
    type: str = "price_update"
    prices: dict[str, Decimal]

class ErrorMessage(WebSocketMessage):
    type: str = "error"
    message: str
    code: Optional[str] = None

# API Response Schemas
class APIResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None

# Sync Schemas for Local-First Architecture
class SyncPortfolioData(BaseModel):
    user_id: str
    cash_balance: Decimal
    initial_balance: Decimal

class SyncHoldingData(BaseModel):
    symbol: str
    name: str
    quantity: Decimal
    average_cost_basis: Decimal
    current_price: Optional[Decimal] = None

class SyncTransactionData(BaseModel):
    id: str  # UUID from frontend
    user_id: str
    symbol: str
    type: str  # 'buy' or 'sell'
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    total_value: Decimal

class SyncWatchlistData(BaseModel):
    symbol: str
    name: str
    added_at: datetime
    current_price: Optional[Decimal] = None
    daily_change: Optional[Decimal] = None
    daily_change_percentage: Optional[Decimal] = None

class LocalDataPayload(BaseModel):
    portfolio: Optional[SyncPortfolioData] = None
    holdings: List[SyncHoldingData] = []
    transactions: List[SyncTransactionData] = []
    watchlist: List[SyncWatchlistData] = []

class SyncMigrateRequest(BaseModel):
    anonymous_user_id: str = Field(..., description="The anonymous user ID from the device")
    firebase_user_id: str = Field(..., description="The Firebase user ID after authentication")
    sync_timestamp: datetime = Field(..., description="When the sync was initiated")
    data: LocalDataPayload = Field(..., description="The local data to migrate")

class SyncMigrateResponse(BaseModel):
    success: bool = True
    message: str = "Data migrated successfully"
    migrated_items: dict = Field(default_factory=dict, description="Count of migrated items by type")
    user_id: str = Field(..., description="The Firebase user ID")
    migration_timestamp: datetime = Field(default_factory=datetime.now) 