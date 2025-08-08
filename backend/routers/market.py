from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from services.market_data_client import market_data_client
from schemas import StockSearchResult, StockSearchResponse, PriceUpdate
import crud

router = APIRouter()

@router.get("/stocks/search", response_model=StockSearchResponse)
async def search_stocks(
    query: str = Query(..., min_length=1, max_length=50, description="Search query for stock symbols or company names"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search for stocks by symbol or company name.
    Public endpoint - no authentication required.
    """
    try:
        # Search in local database first
        assets = crud.search_assets(db, query, limit)
        
        results = []
        for asset in assets:
            # Try to get current price from market data
            current_price = None
            try:
                quote = await market_data_client.get_quote(asset.symbol)
                if quote and quote.price > 0:
                    current_price = quote.price
            except Exception:
                pass  # Price not available
            
            results.append(StockSearchResult(
                symbol=asset.symbol,
                name=asset.name,
                exchange=asset.exchange,
                asset_type=asset.asset_type,
                current_price=current_price
            ))
        
        return StockSearchResponse(
            results=results,
            total_results=len(results)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search stocks: {str(e)}"
        )

@router.get("/stocks/{symbol}/quote")
async def get_stock_quote(symbol: str):
    """
    Get detailed quote information for a stock symbol.
    Public endpoint - no authentication required.
    """
    try:
        quote = await market_data_client.get_quote(symbol.upper())
        if not quote or quote.price <= 0:
            raise HTTPException(
                status_code=404,
                detail=f"Quote not found for symbol {symbol.upper()}"
            )
        
        return {
            "symbol": symbol.upper(),
            "price": float(quote.price),
            "source": quote.source,
            "timestamp": quote.timestamp.isoformat() if quote.timestamp else None,
            "change": float(quote.change) if quote.change else None,
            "change_percent": float(quote.change_percent) if quote.change_percent else None,
            "volume": quote.volume,
            "high": float(quote.high) if quote.high else None,
            "low": float(quote.low) if quote.low else None,
            "open": float(quote.open_price) if quote.open_price else None,
            "previous_close": float(quote.previous_close) if quote.previous_close else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quote for {symbol}: {str(e)}"
        )

@router.get("/stocks/trending")
async def get_trending_stocks():
    """
    Get list of trending/popular stock symbols.
    Public endpoint - no authentication required.
    """
    try:
        # Popular stocks list
        trending_symbols = [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", 
            "NVDA", "META", "NFLX", "AMD", "ADBE"
        ]
        
        trending_data = []
        for symbol in trending_symbols:
            try:
                quote = await market_data_client.get_quote(symbol)
                if quote and quote.price > 0:
                    trending_data.append({
                        "symbol": symbol,
                        "price": float(quote.price),
                        "change": float(quote.change) if quote.change else 0.0,
                        "change_percent": float(quote.change_percent) if quote.change_percent else 0.0,
                        "volume": quote.volume or 0
                    })
            except Exception:
                # Skip symbols that fail to load
                continue
        
        return {
            "trending_stocks": trending_data,
            "total": len(trending_data),
            "last_updated": "2025-08-08T10:00:00Z"  # Mock timestamp
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending stocks: {str(e)}"
        )

@router.get("/stocks/{symbol}/info")
async def get_stock_info(symbol: str, db: Session = Depends(get_db)):
    """
    Get detailed company information for a stock symbol.
    Public endpoint - no authentication required.
    """
    try:
        # Get asset from database
        asset = crud.get_asset_by_symbol(db, symbol.upper())
        if not asset:
            # Create a basic asset record if it doesn't exist
            asset = crud.get_or_create_asset(db, symbol.upper())
        
        # Get current quote
        current_price = None
        quote_data = {}
        try:
            quote = await market_data_client.get_quote(symbol.upper())
            if quote and quote.price > 0:
                current_price = quote.price
                quote_data = {
                    "price": float(quote.price),
                    "change": float(quote.change) if quote.change else None,
                    "change_percent": float(quote.change_percent) if quote.change_percent else None,
                    "volume": quote.volume,
                    "high": float(quote.high) if quote.high else None,
                    "low": float(quote.low) if quote.low else None,
                    "open": float(quote.open_price) if quote.open_price else None
                }
        except Exception:
            pass
        
        return {
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "sector": asset.sector,
            "industry": asset.industry,
            "exchange": asset.exchange,
            "market_cap": float(asset.market_cap) if asset.market_cap else None,
            "description": asset.description,
            "current_quote": quote_data,
            "is_active": asset.is_active
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stock info for {symbol}: {str(e)}"
        )

@router.get("/market/status")
async def get_market_status():
    """
    Get current market status and trading hours.
    Public endpoint - no authentication required.
    """
    try:
        # Mock market status for now
        # In a real implementation, this would check actual market hours
        from datetime import datetime, time
        import pytz
        
        # Get current time in EST
        est = pytz.timezone('US/Eastern')
        current_time = datetime.now(est)
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Market is open 9:30 AM - 4:00 PM EST on weekdays
        is_weekend = current_time.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        if is_weekend:
            status = "closed"
            reason = "Weekend"
        elif current_hour < 9 or (current_hour == 9 and current_minute < 30):
            status = "pre_market"
            reason = "Before market open (9:30 AM EST)"
        elif current_hour >= 16:
            status = "after_market"
            reason = "After market close (4:00 PM EST)"
        else:
            status = "open"
            reason = "Market is open"
        
        return {
            "status": status,
            "reason": reason,
            "current_time": current_time.isoformat(),
            "timezone": "US/Eastern",
            "next_open": "2025-08-08T09:30:00-05:00",  # Mock
            "next_close": "2025-08-08T16:00:00-05:00"   # Mock
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get market status: {str(e)}"
        )
