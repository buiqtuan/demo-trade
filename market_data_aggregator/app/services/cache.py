"""
Redis cache service with circuit breaker logic for Market Data Aggregator.
Handles caching of quotes, assets, and circuit breaker state management.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from ..core.config import settings, provider_config
from ..core.logging_config import create_logger
from ..api.schemas import Quote, Asset, AssetType, DataProvider, CircuitBreakerStatus

logger = create_logger(__name__)


class CacheService:
    """Redis cache service with circuit breaker functionality."""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
        self._connection_lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        async with self._connection_lock:
            if self._pool is None:
                try:
                    self._pool = ConnectionPool.from_url(
                        settings.get_redis_url(),
                        max_connections=20,
                        retry_on_timeout=True,
                        socket_keepalive=True,
                        socket_keepalive_options={},
                        health_check_interval=30
                    )
                    self._redis = redis.Redis(connection_pool=self._pool)
                    
                    # Test connection
                    await self._redis.ping()
                    logger.info("Successfully connected to Redis", extra={
                        "redis_host": settings.redis_host,
                        "redis_port": settings.redis_port,
                        "redis_db": settings.redis_db
                    })
                    
                except Exception as e:
                    logger.error("Failed to connect to Redis", extra={
                        "error": str(e),
                        "redis_host": settings.redis_host,
                        "redis_port": settings.redis_port
                    })
                    raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        async with self._connection_lock:
            if self._redis:
                await self._redis.close()
                self._redis = None
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
            logger.info("Disconnected from Redis")
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self._redis:
                return False
            await self._redis.ping()
            return True
        except Exception as e:
            logger.warning("Redis health check failed", extra={"error": str(e)})
            return False
    
    # Circuit Breaker Methods
    
    async def is_circuit_open(self, provider: DataProvider) -> bool:
        """Check if circuit breaker is open for a provider."""
        try:
            key = provider_config.CIRCUIT_BREAKER_KEYS[provider.value]
            circuit_data = await self._redis.get(key)
            
            if not circuit_data:
                return False
            
            circuit_info = json.loads(circuit_data)
            
            # Check if circuit should be closed based on timeout
            if circuit_info.get('is_open', False):
                trip_time = datetime.fromisoformat(circuit_info['trip_time'])
                timeout_duration = timedelta(seconds=settings.circuit_breaker_timeout)
                
                if datetime.utcnow() > trip_time + timeout_duration:
                    # Circuit timeout expired, close it
                    await self.close_circuit(provider)
                    return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to check circuit breaker status", extra={
                "provider": provider.value,
                "error": str(e)
            })
            return False
    
    async def trip_circuit(self, provider: DataProvider, error_message: str = "") -> None:
        """Trip (open) the circuit breaker for a provider."""
        try:
            key = provider_config.CIRCUIT_BREAKER_KEYS[provider.value]
            circuit_info = {
                'is_open': True,
                'trip_time': datetime.utcnow().isoformat(),
                'error_message': error_message,
                'failure_count': await self._increment_failure_count(provider)
            }
            
            # Store circuit breaker state with TTL
            await self._redis.setex(
                key,
                settings.circuit_breaker_timeout + 60,  # Extra 60 seconds for cleanup
                json.dumps(circuit_info)
            )
            
            logger.warning("Circuit breaker tripped", extra={
                "provider": provider.value,
                "error_message": error_message,
                "failure_count": circuit_info['failure_count']
            })
            
        except Exception as e:
            logger.error("Failed to trip circuit breaker", extra={
                "provider": provider.value,
                "error": str(e)
            })
    
    async def close_circuit(self, provider: DataProvider) -> None:
        """Close (reset) the circuit breaker for a provider."""
        try:
            key = provider_config.CIRCUIT_BREAKER_KEYS[provider.value]
            await self._redis.delete(key)
            await self._reset_failure_count(provider)
            
            logger.info("Circuit breaker closed", extra={
                "provider": provider.value
            })
            
        except Exception as e:
            logger.error("Failed to close circuit breaker", extra={
                "provider": provider.value,
                "error": str(e)
            })
    
    async def get_circuit_status(self, provider: DataProvider) -> CircuitBreakerStatus:
        """Get detailed circuit breaker status for a provider."""
        try:
            key = provider_config.CIRCUIT_BREAKER_KEYS[provider.value]
            circuit_data = await self._redis.get(key)
            
            if not circuit_data:
                return CircuitBreakerStatus(
                    provider=provider,
                    is_open=False,
                    failure_count=0
                )
            
            circuit_info = json.loads(circuit_data)
            
            return CircuitBreakerStatus(
                provider=provider,
                is_open=circuit_info.get('is_open', False),
                failure_count=circuit_info.get('failure_count', 0),
                last_failure=datetime.fromisoformat(circuit_info['trip_time']) if circuit_info.get('trip_time') else None,
                next_attempt=datetime.fromisoformat(circuit_info['trip_time']) + timedelta(seconds=settings.circuit_breaker_timeout) if circuit_info.get('trip_time') else None
            )
            
        except Exception as e:
            logger.error("Failed to get circuit status", extra={
                "provider": provider.value,
                "error": str(e)
            })
            return CircuitBreakerStatus(
                provider=provider,
                is_open=False,
                failure_count=0
            )
    
    async def _increment_failure_count(self, provider: DataProvider) -> int:
        """Increment failure count for a provider."""
        key = f"failures:{provider.value}"
        count = await self._redis.incr(key)
        await self._redis.expire(key, 3600)  # Reset count after 1 hour
        return count
    
    async def _reset_failure_count(self, provider: DataProvider) -> None:
        """Reset failure count for a provider."""
        key = f"failures:{provider.value}"
        await self._redis.delete(key)
    
    # Quote Caching Methods
    
    async def get_quotes_from_cache(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for symbols from cache."""
        try:
            if not symbols:
                return {}
            
            # Prepare Redis keys
            keys = [provider_config.CACHE_KEYS['quotes'].format(symbol=symbol) for symbol in symbols]
            
            # Use pipeline for efficiency
            pipe = self._redis.pipeline()
            for key in keys:
                pipe.get(key)
            
            results = await pipe.execute()
            
            quotes = {}
            for i, result in enumerate(results):
                if result:
                    try:
                        quote_data = json.loads(result)
                        quote = Quote(**quote_data)
                        quotes[symbols[i]] = quote
                    except Exception as e:
                        logger.warning("Failed to deserialize quote from cache", extra={
                            "symbol": symbols[i],
                            "error": str(e)
                        })
            
            logger.debug("Retrieved quotes from cache", extra={
                "requested_symbols": len(symbols),
                "cached_symbols": len(quotes)
            })
            
            return quotes
            
        except Exception as e:
            logger.error("Failed to get quotes from cache", extra={
                "symbols": symbols,
                "error": str(e)
            })
            return {}
    
    async def set_quotes_in_cache(self, quotes: Dict[str, Quote]) -> None:
        """Store quotes in cache with TTL."""
        try:
            if not quotes:
                return
            
            pipe = self._redis.pipeline()
            
            for symbol, quote in quotes.items():
                key = provider_config.CACHE_KEYS['quotes'].format(symbol=symbol)
                quote_json = quote.json()
                pipe.setex(key, settings.quotes_cache_ttl, quote_json)
            
            await pipe.execute()
            
            logger.debug("Stored quotes in cache", extra={
                "symbols": list(quotes.keys()),
                "ttl": settings.quotes_cache_ttl
            })
            
        except Exception as e:
            logger.error("Failed to store quotes in cache", extra={
                "symbols": list(quotes.keys()) if quotes else [],
                "error": str(e)
            })
    
    # Asset List Caching Methods
    
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """Get asset list from cache."""
        try:
            key = provider_config.CACHE_KEYS[f'assets_{asset_type.value}']
            assets_data = await self._redis.get(key)
            
            if not assets_data:
                return []
            
            assets_list = json.loads(assets_data)
            assets = [Asset(**asset_data) for asset_data in assets_list]
            
            logger.debug("Retrieved asset list from cache", extra={
                "asset_type": asset_type.value,
                "count": len(assets)
            })
            
            return assets
            
        except Exception as e:
            logger.error("Failed to get asset list from cache", extra={
                "asset_type": asset_type.value,
                "error": str(e)
            })
            return []
    
    async def set_asset_list(self, asset_type: AssetType, assets: List[Asset]) -> None:
        """Store asset list in cache with TTL."""
        try:
            key = provider_config.CACHE_KEYS[f'assets_{asset_type.value}']
            assets_data = [asset.dict() for asset in assets]
            assets_json = json.dumps(assets_data, default=str)
            
            await self._redis.setex(key, settings.assets_cache_ttl, assets_json)
            
            logger.info("Stored asset list in cache", extra={
                "asset_type": asset_type.value,
                "count": len(assets),
                "ttl": settings.assets_cache_ttl
            })
            
        except Exception as e:
            logger.error("Failed to store asset list in cache", extra={
                "asset_type": asset_type.value,
                "count": len(assets) if assets else 0,
                "error": str(e)
            })
    
    # Configuration Methods
    
    async def get_active_symbols(self) -> List[str]:
        """Get active symbols list from cache or config."""
        try:
            key = provider_config.CACHE_KEYS['active_symbols']
            symbols_data = await self._redis.get(key)
            
            if symbols_data:
                return json.loads(symbols_data)
            
            # Fallback to config
            symbols = settings.get_active_symbols_list()
            await self.set_active_symbols(symbols)
            return symbols
            
        except Exception as e:
            logger.error("Failed to get active symbols", extra={"error": str(e)})
            return settings.get_active_symbols_list()
    
    async def set_active_symbols(self, symbols: List[str]) -> None:
        """Store active symbols list in cache."""
        try:
            key = provider_config.CACHE_KEYS['active_symbols']
            symbols_json = json.dumps(symbols)
            await self._redis.setex(key, 3600, symbols_json)  # 1 hour TTL
            
            logger.debug("Stored active symbols in cache", extra={
                "count": len(symbols)
            })
            
        except Exception as e:
            logger.error("Failed to store active symbols", extra={
                "symbols": symbols,
                "error": str(e)
            })
    
    # Utility Methods
    
    async def get_last_update_time(self, key: str) -> Optional[datetime]:
        """Get last update timestamp for a cache key."""
        try:
            timestamp_key = f"last_update:{key}"
            timestamp_data = await self._redis.get(timestamp_key)
            
            if timestamp_data:
                return datetime.fromisoformat(timestamp_data.decode())
            
            return None
            
        except Exception as e:
            logger.error("Failed to get last update time", extra={
                "key": key,
                "error": str(e)
            })
            return None
    
    async def set_last_update_time(self, key: str, timestamp: Optional[datetime] = None) -> None:
        """Set last update timestamp for a cache key."""
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            timestamp_key = f"last_update:{key}"
            await self._redis.setex(timestamp_key, 86400, timestamp.isoformat())  # 24 hour TTL
            
        except Exception as e:
            logger.error("Failed to set last update time", extra={
                "key": key,
                "error": str(e)
            })


# Global cache service instance
cache_service = CacheService()