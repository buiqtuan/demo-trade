"""
Pydantic schemas for Market Data Aggregator Service.
Defines standardized data structures for assets and quotes.
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


class Asset(BaseModel):
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


class Quote(BaseModel):
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


class QuoteRequest(BaseModel):
    """Model for quote request parameters."""
    symbols: List[str] = Field(..., min_items=1, max_items=100, description="List of symbols to quote")
    
    @validator('symbols')
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Validate and normalize symbols."""
        if not v:
            raise ValueError("At least one symbol is required")
        
        normalized = []
        for symbol in v:
            if not symbol or not symbol.strip():
                continue
            normalized.append(symbol.strip().upper())
        
        if not normalized:
            raise ValueError("At least one valid symbol is required")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_symbols = []
        for symbol in normalized:
            if symbol not in seen:
                seen.add(symbol)
                unique_symbols.append(symbol)
        
        return unique_symbols


class QuoteResponse(BaseModel):
    """Model for quote response."""
    quotes: List[Quote] = Field(..., description="List of quotes")
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


class AssetListResponse(BaseModel):
    """Model for asset list response."""
    assets: List[Asset] = Field(..., description="List of assets")
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


class HealthResponse(BaseModel):
    """Model for health check response."""
    status: Literal["healthy", "unhealthy"] = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    redis_connected: bool = Field(..., description="Redis connection status")
    active_circuits: Dict[str, bool] = Field(default_factory=dict, description="Circuit breaker status")
    background_tasks_running: bool = Field(..., description="Background tasks status")
    last_data_update: Optional[datetime] = Field(None, description="Last successful data update")


class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class CircuitBreakerStatus(BaseModel):
    """Model for circuit breaker status."""
    provider: DataProvider = Field(..., description="Data provider")
    is_open: bool = Field(..., description="Whether circuit is open")
    failure_count: int = Field(0, description="Number of consecutive failures")
    last_failure: Optional[datetime] = Field(None, description="Last failure timestamp")
    next_attempt: Optional[datetime] = Field(None, description="Next attempt timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


# Type aliases for convenience
QuoteDict = Dict[str, Quote]
AssetDict = Dict[str, Asset]