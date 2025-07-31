"""
Data aggregator service for Market Data Aggregator.
Orchestrates background tasks for asset list updates and price fetching.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Type
from collections import defaultdict

from ..core.config import settings, provider_config
from ..core.logging_config import create_logger
from ..api.schemas import AssetType, DataProvider, Quote, Asset
from ..services.cache import cache_service
from ..providers.base import BaseDataProvider, ProviderError
from ..providers.yfinance_provider import YFinanceProvider
from ..providers.finnhub_provider import FinnhubProvider
from ..providers.coingecko_provider import CoinGeckoProvider
from ..providers.coinmarketcap_provider import CoinMarketCapProvider
from ..providers.alpha_vantage_provider import AlphaVantageProvider

logger = create_logger(__name__)


class DataAggregatorService:
    """Service that orchestrates data fetching from multiple providers."""
    
    def __init__(self):
        self._providers: Dict[str, BaseDataProvider] = {}
        self._running_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._last_asset_update: Optional[datetime] = None
        self._last_price_update: Optional[datetime] = None
        
    async def initialize(self) -> None:
        """Initialize all data providers."""
        try:
            logger.info("Initializing data aggregator service")
            
            # Initialize providers
            provider_classes = {
                'yfinance': YFinanceProvider,
                'finnhub': FinnhubProvider,
                'coingecko': CoinGeckoProvider,
                'coinmarketcap': CoinMarketCapProvider,
                'alpha_vantage': AlphaVantageProvider
            }
            
            for name, provider_class in provider_classes.items():
                try:
                    provider = provider_class()
                    await provider.connect()
                    self._providers[name] = provider
                    logger.info("Initialized provider", extra={"provider": name})
                    
                except Exception as e:
                    logger.error("Failed to initialize provider", extra={
                        "provider": name,
                        "error": str(e)
                    })
                    # Continue with other providers even if one fails
                    continue
            
            # Ensure cache service is connected
            await cache_service.connect()
            
            logger.info("Data aggregator service initialized successfully", extra={
                "active_providers": list(self._providers.keys())
            })
            
        except Exception as e:
            logger.error("Failed to initialize data aggregator service", extra={
                "error": str(e)
            })
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the data aggregator service."""
        logger.info("Shutting down data aggregator service")
        
        # Signal shutdown to all tasks
        self._shutdown_event.set()
        
        # Cancel all running tasks
        for task in self._running_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        # Disconnect all providers
        for provider in self._providers.values():
            try:
                await provider.disconnect()
            except Exception as e:
                logger.warning("Error disconnecting provider", extra={
                    "provider": provider.name,
                    "error": str(e)
                })
        
        # Disconnect cache service
        await cache_service.disconnect()
        
        logger.info("Data aggregator service shutdown complete")
    
    async def start_background_tasks(self) -> None:
        """Start background tasks for data fetching."""
        logger.info("Starting background tasks")
        
        # Start asset list update task (slow loop)
        asset_task = asyncio.create_task(self.run_asset_list_update())
        self._running_tasks.append(asset_task)
        
        # Start price fetch task (fast loop)
        price_task = asyncio.create_task(self.run_price_fetch_loop())
        self._running_tasks.append(price_task)
        
        logger.info("Background tasks started", extra={
            "tasks": len(self._running_tasks)
        })
    
    async def run_asset_list_update(self) -> None:
        """Background task to update asset lists from all providers."""
        logger.info("Starting asset list update loop", extra={
            "interval": settings.asset_list_update_interval
        })
        
        while not self._shutdown_event.is_set():
            try:
                start_time = datetime.utcnow()
                
                # Update asset lists for all supported asset types
                for asset_type in AssetType:
                    await self._update_asset_list_for_type(asset_type)
                
                self._last_asset_update = datetime.utcnow()
                update_duration = (self._last_asset_update - start_time).total_seconds()
                
                logger.info("Asset list update completed", extra={
                    "duration_seconds": update_duration,
                    "next_update": self._last_asset_update + timedelta(seconds=settings.asset_list_update_interval)
                })
                
                # Set last update time in cache
                await cache_service.set_last_update_time("asset_list_update", self._last_asset_update)
                
            except Exception as e:
                logger.error("Error in asset list update loop", extra={
                    "error": str(e)
                })
            
            # Wait for next update cycle
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=settings.asset_list_update_interval
                )
                break  # Shutdown event was set
            except asyncio.TimeoutError:
                continue  # Continue with next update cycle
    
    async def _update_asset_list_for_type(self, asset_type: AssetType) -> None:
        """Update asset list for a specific asset type."""
        try:
            # Get primary provider for this asset type
            primary_provider_name = provider_config.PRIMARY_PROVIDERS.get(asset_type.value)
            if not primary_provider_name or primary_provider_name not in self._providers:
                logger.warning("No primary provider available for asset type", extra={
                    "asset_type": asset_type.value
                })
                return
            
            primary_provider = self._providers[primary_provider_name]
            
            # Check if primary provider supports this asset type
            if not primary_provider.supports_asset_type(asset_type):
                logger.warning("Primary provider does not support asset type", extra={
                    "provider": primary_provider_name,
                    "asset_type": asset_type.value
                })
                return
            
            # Check circuit breaker
            provider_enum = primary_provider.get_provider_name()
            is_circuit_open = await cache_service.is_circuit_open(provider_enum)
            
            if is_circuit_open:
                logger.info("Circuit breaker is open, using fallback provider", extra={
                    "primary_provider": primary_provider_name,
                    "asset_type": asset_type.value
                })
                
                # Try fallback provider
                fallback_provider_name = provider_config.FALLBACK_PROVIDERS.get(asset_type.value)
                if fallback_provider_name and fallback_provider_name in self._providers:
                    primary_provider = self._providers[fallback_provider_name]
                    if not primary_provider.supports_asset_type(asset_type):
                        logger.warning("Fallback provider does not support asset type", extra={
                            "provider": fallback_provider_name,
                            "asset_type": asset_type.value
                        })
                        return
                else:
                    logger.warning("No fallback provider available", extra={
                        "asset_type": asset_type.value
                    })
                    return
            
            # Fetch asset list from provider
            try:
                assets = await primary_provider.get_asset_list(asset_type)
                
                if assets:
                    # Store in cache
                    await cache_service.set_asset_list(asset_type, assets)
                    logger.info("Updated asset list", extra={
                        "asset_type": asset_type.value,
                        "provider": primary_provider.name,
                        "count": len(assets)
                    })
                else:
                    logger.warning("No assets received from provider", extra={
                        "asset_type": asset_type.value,
                        "provider": primary_provider.name
                    })
                
            except ProviderError as e:
                logger.error("Provider error while fetching asset list", extra={
                    "asset_type": asset_type.value,
                    "provider": primary_provider.name,
                    "error": str(e)
                })
                
                # Trip circuit breaker
                await cache_service.trip_circuit(provider_enum, str(e))
                
        except Exception as e:
            logger.error("Unexpected error updating asset list", extra={
                "asset_type": asset_type.value,
                "error": str(e)
            })
    
    async def run_price_fetch_loop(self) -> None:
        """Background task to fetch price updates for active symbols."""
        logger.info("Starting price fetch loop", extra={
            "interval": settings.price_fetch_interval
        })
        
        while not self._shutdown_event.is_set():
            try:
                start_time = datetime.utcnow()
                
                # Get active symbols to track
                active_symbols = await cache_service.get_active_symbols()
                
                if not active_symbols:
                    logger.warning("No active symbols to track")
                else:
                    # Group symbols by asset type
                    symbol_groups = self._group_symbols_by_asset_type(active_symbols)
                    
                    # Fetch quotes for each group
                    all_quotes = {}
                    for asset_type, symbols in symbol_groups.items():
                        quotes = await self._fetch_quotes_for_asset_type(asset_type, symbols)
                        all_quotes.update(quotes)
                    
                    # Store quotes in cache
                    if all_quotes:
                        await cache_service.set_quotes_in_cache(all_quotes)
                    
                    self._last_price_update = datetime.utcnow()
                    update_duration = (self._last_price_update - start_time).total_seconds()
                    
                    logger.info("Price fetch completed", extra={
                        "symbols_requested": len(active_symbols),
                        "quotes_received": len(all_quotes),
                        "duration_seconds": update_duration
                    })
                    
                    # Set last update time in cache
                    await cache_service.set_last_update_time("price_fetch", self._last_price_update)
                
            except Exception as e:
                logger.error("Error in price fetch loop", extra={
                    "error": str(e)
                })
            
            # Wait for next update cycle
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=settings.price_fetch_interval
                )
                break  # Shutdown event was set
            except asyncio.TimeoutError:
                continue  # Continue with next update cycle
    
    def _group_symbols_by_asset_type(self, symbols: List[str]) -> Dict[AssetType, List[str]]:
        """Group symbols by their asset type."""
        groups = defaultdict(list)
        
        for symbol in symbols:
            # Determine asset type based on symbol format
            if '/' in symbol or symbol.endswith('=X'):
                asset_type = AssetType.FOREX
            elif any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'ADA', 'DOT', 'XRP', 'LTC', 'DOGE']):
                asset_type = AssetType.CRYPTO
            else:
                asset_type = AssetType.STOCKS
            
            groups[asset_type].append(symbol)
        
        return dict(groups)
    
    async def _fetch_quotes_for_asset_type(self, asset_type: AssetType, symbols: List[str]) -> Dict[str, Quote]:
        """Fetch quotes for symbols of a specific asset type."""
        if not symbols:
            return {}
        
        # Get primary provider for this asset type
        primary_provider_name = provider_config.PRIMARY_PROVIDERS.get(asset_type.value)
        if not primary_provider_name or primary_provider_name not in self._providers:
            logger.warning("No primary provider available for asset type", extra={
                "asset_type": asset_type.value
            })
            return {}
        
        primary_provider = self._providers[primary_provider_name]
        provider_enum = primary_provider.get_provider_name()
        
        # Check circuit breaker
        is_circuit_open = await cache_service.is_circuit_open(provider_enum)
        
        if is_circuit_open:
            logger.info("Circuit breaker is open, using fallback provider", extra={
                "primary_provider": primary_provider_name,
                "asset_type": asset_type.value
            })
            
            # Try fallback provider
            fallback_provider_name = provider_config.FALLBACK_PROVIDERS.get(asset_type.value)
            if fallback_provider_name and fallback_provider_name in self._providers:
                primary_provider = self._providers[fallback_provider_name]
                provider_enum = primary_provider.get_provider_name()
            else:
                logger.warning("No fallback provider available", extra={
                    "asset_type": asset_type.value
                })
                return {}
        
        # Fetch quotes from provider
        try:
            quotes = await primary_provider.get_quotes(symbols)
            
            logger.debug("Fetched quotes from provider", extra={
                "asset_type": asset_type.value,
                "provider": primary_provider.name,
                "symbols_requested": len(symbols),
                "quotes_received": len(quotes)
            })
            
            return quotes
            
        except ProviderError as e:
            logger.error("Provider error while fetching quotes", extra={
                "asset_type": asset_type.value,
                "provider": primary_provider.name,
                "symbols": symbols,
                "error": str(e)
            })
            
            # Trip circuit breaker
            await cache_service.trip_circuit(provider_enum, str(e))
            
            return {}
        
        except Exception as e:
            logger.error("Unexpected error fetching quotes", extra={
                "asset_type": asset_type.value,
                "provider": primary_provider.name,
                "symbols": symbols,
                "error": str(e)
            })
            
            return {}
    
    async def get_provider_health_status(self) -> Dict[str, bool]:
        """Get health status of all providers."""
        health_status = {}
        
        for name, provider in self._providers.items():
            try:
                is_healthy = await provider.health_check()
                health_status[name] = is_healthy
            except Exception as e:
                logger.warning("Health check failed for provider", extra={
                    "provider": name,
                    "error": str(e)
                })
                health_status[name] = False
        
        return health_status
    
    async def get_circuit_breaker_status(self) -> Dict[str, bool]:
        """Get circuit breaker status for all providers."""
        circuit_status = {}
        
        for provider_name in DataProvider:
            try:
                is_open = await cache_service.is_circuit_open(provider_name)
                circuit_status[provider_name.value] = is_open
            except Exception as e:
                logger.warning("Failed to get circuit breaker status", extra={
                    "provider": provider_name.value,
                    "error": str(e)
                })
                circuit_status[provider_name.value] = False
        
        return circuit_status
    
    def get_last_update_times(self) -> Dict[str, Optional[datetime]]:
        """Get timestamps of last successful updates."""
        return {
            'asset_list_update': self._last_asset_update,
            'price_fetch': self._last_price_update
        }
    
    def are_background_tasks_running(self) -> bool:
        """Check if background tasks are running."""
        if not self._running_tasks:
            return False
        
        # Check if any tasks are still running
        return any(not task.done() for task in self._running_tasks)


# Global aggregator service instance
aggregator_service = DataAggregatorService()