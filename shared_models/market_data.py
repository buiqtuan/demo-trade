"""
Shared market data models for demo-trade application.
Defines standardized data structures for assets and quotes used across services.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class AssetType(str, Enum):
    """Supported asset types."""
    STOCKS = "stocks"
    CRYPTO = "crypto"
    FOREX = "forex"


class DataProvider(str, Enum):
    """Supported data providers."""
    YFINANCE = "yfinance"
    FINNHUB = "finnhub"
    COINGECKO = "coingecko"
    COINMARKETCAP = "coinmarketcap"
    ALPHA_VANTAGE = "alpha_vantage"


class MarketAsset(BaseModel):
    """Model for financial asset information."""
    symbol: str = Field(..., description="Asset symbol/ticker")
    name: str = Field(..., description="Asset full name")
    asset_type: AssetType = Field(..., description="Type of asset")
    exchange: Optional[str] = Field(None, description="Exchange where asset is traded")
    currency: Optional[str] = Field(None, description="Base currency")
    is_active: bool = Field(True, description="Whether asset is actively traded")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional asset metadata")
    
    @validator('symbol')
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize symbol."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate asset name."""
        if not v or not v.strip():
            raise ValueError("Asset name cannot be empty")
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MarketQuote(BaseModel):
    """Model for real-time market quote."""
    symbol: str = Field(..., description="Asset symbol/ticker")
    price: float = Field(..., description="Current price")
    change: Optional[float] = Field(None, description="Absolute price change")
    percent_change: Optional[float] = Field(None, description="Percentage price change")
    volume: Optional[int] = Field(None, description="Trading volume")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    high_24h: Optional[float] = Field(None, description="24-hour high")
    low_24h: Optional[float] = Field(None, description="24-hour low")
    open_price: Optional[float] = Field(None, description="Opening price")
    close_price: Optional[float] = Field(None, description="Previous close price")
    bid: Optional[float] = Field(None, description="Bid price")
    ask: Optional[float] = Field(None, description="Ask price")
    source: DataProvider = Field(..., description="Data provider source")
    timestamp: datetime = Field(..., description="Quote timestamp")
    currency: Optional[str] = Field(None, description="Quote currency")
    asset_type: Optional[AssetType] = Field(None, description="Asset type")
    
    @validator('symbol')
    def validate_symbol(cls, v: str) -> str:
        """Validate and normalize symbol."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()
    
    @validator('price')
    def validate_price(cls, v: float) -> float:
        """Validate price is positive."""
        if v <= 0:
            raise ValueError("Price must be positive")
        return round(v, 8)  # Round to 8 decimal places for precision
    
    @validator('percent_change')
    def validate_percent_change(cls, v: Optional[float]) -> Optional[float]:
        """Validate and round percent change."""
        if v is not None:
            return round(v, 4)  # Round to 4 decimal places
        return v
    
    @validator('change')
    def validate_change(cls, v: Optional[float]) -> Optional[float]:
        """Validate and round price change."""
        if v is not None:
            return round(v, 8)  # Round to 8 decimal places
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class QuoteResponse(BaseModel):
    """Model for quote response."""
    quotes: List[MarketQuote] = Field(..., description="List of quotes")
    total: int = Field(..., description="Total number of quotes")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    cache_hit: bool = Field(False, description="Whether data was served from cache")
    
    @validator('total')
    def validate_total(cls, v: int, values: dict) -> int:
        """Validate total matches quotes length."""
        quotes = values.get('quotes', [])
        if v != len(quotes):
            raise ValueError("Total must match the number of quotes")
        return v


class NewsArticle(BaseModel):
    """Model for news articles."""
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary/description")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source")
    published_at: datetime = Field(..., description="Publication timestamp")
    symbols: Optional[List[str]] = Field(default_factory=list, description="Related symbols")
    category: Optional[str] = Field(None, description="News category")
    sentiment: Optional[str] = Field(None, description="Article sentiment")
    
    @validator('title')
    def validate_title(cls, v: str) -> str:
        """Validate article title."""
        if not v or not v.strip():
            raise ValueError("Article title cannot be empty")
        return v.strip()
    
    @validator('url')
    def validate_url(cls, v: str) -> str:
        """Validate article URL."""
        if not v or not v.strip():
            raise ValueError("Article URL cannot be empty")
        return v.strip()
    
    @validator('source')
    def validate_source(cls, v: str) -> str:
        """Validate news source."""
        if not v or not v.strip():
            raise ValueError("News source cannot be empty")
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class NewsResponse(BaseModel):
    """Model for news response."""
    articles: List[NewsArticle] = Field(..., description="List of news articles")
    total: int = Field(..., description="Total number of articles")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    cache_hit: bool = Field(False, description="Whether data was served from cache")
    symbol: Optional[str] = Field(None, description="Symbol for company-specific news")
    
    @validator('total')
    def validate_total(cls, v: int, values: dict) -> int:
        """Validate total matches articles length."""
        articles = values.get('articles', [])
        if v != len(articles):
            raise ValueError("Total must match the number of articles")
        return v


class AssetListResponse(BaseModel):
    """Model for asset list response."""
    assets: List[MarketAsset] = Field(..., description="List of assets")
    asset_type: AssetType = Field(..., description="Asset type")
    total: int = Field(..., description="Total number of assets")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    cache_hit: bool = Field(False, description="Whether data was served from cache")
    
    @validator('total')
    def validate_total(cls, v: int, values: dict) -> int:
        """Validate total matches assets length."""
        assets = values.get('assets', [])
        if v != len(assets):
            raise ValueError("Total must match the number of assets")
        return v


# Type aliases for convenience
QuoteDict = Dict[str, MarketQuote]
AssetDict = Dict[str, MarketAsset]
NewsDict = Dict[str, List[NewsArticle]]