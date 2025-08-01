"""
Pydantic schemas for Market Data Aggregator Service.
Uses shared models for consistency across services.
"""

# Import shared models with proper fallback
try:
    from shared_models.market_data import (
        AssetType, DataProvider, MarketAsset as Asset, MarketQuote as Quote,
        QuoteResponse, AssetListResponse
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from shared_models.market_data import (
        AssetType, DataProvider, MarketAsset as Asset, MarketQuote as Quote,
        QuoteResponse, AssetListResponse
    )
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator

# Keep the remaining schemas that are specific to the aggregator
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