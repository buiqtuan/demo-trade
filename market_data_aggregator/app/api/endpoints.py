"""
FastAPI endpoints for Market Data Aggregator Service.
Serves cached market data with high performance.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from ..api.schemas import (
    AssetType, QuoteResponse, AssetListResponse, HealthResponse, 
    ErrorResponse, Quote, Asset
)
from ..core.config import settings
from ..core.logging_config import create_logger
from ..services.cache import cache_service
from ..services.data_aggregator import aggregator_service

logger = create_logger(__name__)

# Create API router
router = APIRouter()

# Application startup time for uptime calculation
app_start_time = datetime.utcnow()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns overall service health status including Redis connectivity and background tasks.
    """
    try:
        # Check Redis connectivity
        redis_healthy = await cache_service.health_check()
        
        # Check background tasks
        tasks_running = aggregator_service.are_background_tasks_running()
        
        # Get circuit breaker status
        circuit_status = await aggregator_service.get_circuit_breaker_status()
        
        # Get last update times
        last_updates = aggregator_service.get_last_update_times()
        last_data_update = max(
            last_updates.get('asset_list_update') or datetime.min,
            last_updates.get('price_fetch') or datetime.min
        )
        last_data_update = last_data_update if last_data_update != datetime.min else None
        
        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - app_start_time).total_seconds()
        
        # Determine overall health status
        is_healthy = redis_healthy and tasks_running
        status = "healthy" if is_healthy else "unhealthy"
        
        return HealthResponse(
            status=status,
            version=settings.app_version,
            uptime_seconds=uptime_seconds,
            redis_connected=redis_healthy,
            active_circuits=circuit_status,
            background_tasks_running=tasks_running,
            last_data_update=last_data_update
        )
        
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )


@router.get("/v1/assets/{asset_type}", response_model=AssetListResponse)
async def get_assets(asset_type: AssetType):
    """
    Get all available assets for a specific asset type.
    
    Args:
        asset_type: Type of assets to retrieve (stocks, crypto, forex)
    
    Returns:
        List of available assets with metadata
    """
    try:
        logger.info("Assets request received", extra={
            "asset_type": asset_type.value
        })
        
        # Get assets from cache
        assets = await cache_service.get_asset_list(asset_type)
        
        # Log cache performance
        cache_hit = len(assets) > 0
        logger.info("Assets retrieved from cache", extra={
            "asset_type": asset_type.value,
            "count": len(assets),
            "cache_hit": cache_hit
        })
        
        return AssetListResponse(
            assets=assets,
            asset_type=asset_type,
            total=len(assets),
            cache_hit=cache_hit
        )
        
    except Exception as e:
        logger.error("Failed to retrieve assets", extra={
            "asset_type": asset_type.value,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve assets: {str(e)}"
        )


@router.get("/v1/quotes", response_model=QuoteResponse)
async def get_quotes(
    symbols: str = Query(
        ...,
        description="Comma-separated list of symbols to get quotes for",
        example="AAPL,GOOGL,BTC-USD,EUR/USD"
    )
):
    """
    Get real-time quotes for specified symbols.
    
    Args:
        symbols: Comma-separated list of symbols (e.g., "AAPL,GOOGL,BTC-USD,EUR/USD")
    
    Returns:
        List of quotes for the requested symbols
    """
    try:
        # Parse and validate symbols
        if not symbols or not symbols.strip():
            raise HTTPException(
                status_code=400,
                detail="Symbols parameter is required"
            )
        
        symbol_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]
        
        if not symbol_list:
            raise HTTPException(
                status_code=400,
                detail="At least one valid symbol is required"
            )
        
        if len(symbol_list) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 symbols allowed per request"
            )
        
        logger.info("Quotes request received", extra={
            "symbols": symbol_list,
            "count": len(symbol_list)
        })
        
        # Get quotes from cache
        quotes_dict = await cache_service.get_quotes_from_cache(symbol_list)
        
        # Convert to list
        quotes_list = list(quotes_dict.values())
        
        # Log cache performance
        cache_hit = len(quotes_list) > 0
        logger.info("Quotes retrieved from cache", extra={
            "requested_symbols": len(symbol_list),
            "found_quotes": len(quotes_list),
            "cache_hit": cache_hit,
            "missing_symbols": [s for s in symbol_list if s not in quotes_dict]
        })
        
        return QuoteResponse(
            quotes=quotes_list,
            total=len(quotes_list),
            cache_hit=cache_hit
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error("Failed to retrieve quotes", extra={
            "symbols": symbols,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve quotes: {str(e)}"
        )


@router.get("/v1/quote/{symbol}", response_model=Quote)
async def get_single_quote(symbol: str):
    """
    Get real-time quote for a single symbol.
    
    Args:
        symbol: Symbol to get quote for (e.g., "AAPL", "BTC-USD", "EUR/USD")
    
    Returns:
        Quote for the requested symbol
    """
    try:
        symbol = symbol.strip().upper()
        
        if not symbol:
            raise HTTPException(
                status_code=400,
                detail="Symbol is required"
            )
        
        logger.info("Single quote request received", extra={"symbol": symbol})
        
        # Get quote from cache
        quotes_dict = await cache_service.get_quotes_from_cache([symbol])
        
        if symbol not in quotes_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Quote not found for symbol: {symbol}"
            )
        
        quote = quotes_dict[symbol]
        
        logger.info("Single quote retrieved", extra={
            "symbol": symbol,
            "price": quote.price,
            "source": quote.source.value
        })
        
        return quote
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error("Failed to retrieve single quote", extra={
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve quote: {str(e)}"
        )


@router.get("/v1/symbols/active")
async def get_active_symbols():
    """
    Get the list of actively tracked symbols.
    
    Returns:
        List of symbols that are being actively tracked for price updates
    """
    try:
        logger.info("Active symbols request received")
        
        # Get active symbols from cache
        active_symbols = await cache_service.get_active_symbols()
        
        logger.info("Active symbols retrieved", extra={
            "count": len(active_symbols)
        })
        
        return {
            "symbols": active_symbols,
            "total": len(active_symbols),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Failed to retrieve active symbols", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active symbols: {str(e)}"
        )


@router.get("/v1/providers/status")
async def get_provider_status():
    """
    Get status information about all data providers.
    
    Returns:
        Status of all data providers including circuit breaker states
    """
    try:
        logger.info("Provider status request received")
        
        # Get provider health status
        health_status = await aggregator_service.get_provider_health_status()
        
        # Get circuit breaker status
        circuit_status = await aggregator_service.get_circuit_breaker_status()
        
        # Combine status information
        provider_status = {}
        for provider_name in set(list(health_status.keys()) + list(circuit_status.keys())):
            provider_status[provider_name] = {
                "healthy": health_status.get(provider_name, False),
                "circuit_open": circuit_status.get(provider_name, False),
                "available": health_status.get(provider_name, False) and not circuit_status.get(provider_name, False)
            }
        
        logger.info("Provider status retrieved", extra={
            "providers": list(provider_status.keys())
        })
        
        return {
            "providers": provider_status,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Failed to retrieve provider status", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve provider status: {str(e)}"
        )


@router.get("/v1/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics and information.
    
    Returns:
        Information about cache performance and status
    """
    try:
        logger.info("Cache stats request received")
        
        # Get last update times
        last_updates = aggregator_service.get_last_update_times()
        
        # Redis health check
        redis_healthy = await cache_service.health_check()
        
        cache_stats = {
            "redis_connected": redis_healthy,
            "last_asset_update": last_updates.get('asset_list_update'),
            "last_price_update": last_updates.get('price_fetch'),
            "cache_ttl_settings": {
                "quotes": settings.quotes_cache_ttl,
                "assets": settings.assets_cache_ttl
            },
            "timestamp": datetime.utcnow()
        }
        
        logger.info("Cache stats retrieved")
        
        return cache_stats
        
    except Exception as e:
        logger.error("Failed to retrieve cache stats", extra={
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cache stats: {str(e)}"
        )


# Custom exception handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with structured error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            details={"status_code": exc.status_code}
        ).dict()
    )


@router.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions with structured error response."""
    logger.error("Unhandled exception in API endpoint", extra={
        "error": str(exc),
        "path": request.url.path,
        "method": request.method
    })
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"message": "An unexpected error occurred"}
        ).dict()
    )