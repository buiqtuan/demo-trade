"""
Market Data Aggregator Client for backend service.
Provides a client interface to interact with the Market Data Aggregator service.
"""

import httpx
import logging
import os
import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Import shared models with proper fallback
try:
    from shared_models.market_data import MarketQuote, QuoteResponse, MarketAsset, AssetListResponse, DataProvider
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from shared_models.market_data import MarketQuote, QuoteResponse, MarketAsset, AssetListResponse, DataProvider

logger = logging.getLogger(__name__)


# Custom exception classes
class MarketDataClientError(Exception):
    """Base exception for Market Data Client errors."""
    pass


class MarketDataConnectionError(MarketDataClientError):
    """Raised when connection to Market Data Aggregator fails."""
    pass


class MarketDataValidationError(MarketDataClientError):
    """Raised when input validation fails."""
    pass


class MarketDataClient:
    """Client for Market Data Aggregator service."""
    
    def __init__(self, base_url: str = None, timeout: float = 10.0, max_retries: int = 3):
        """
        Initialize the Market Data Client.
        
        Args:
            base_url: Base URL of the Market Data Aggregator service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url or os.getenv("MARKET_DATA_AGGREGATOR_URL", "http://localhost:8001")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Configure HTTP client with limits and timeouts
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            limits=limits,
            follow_redirects=True
        )
        
        logger.info(f"Initialized Market Data Client with base URL: {self.base_url}, timeout: {timeout}s, max_retries: {max_retries}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Market Data Client closed")
    
    def _validate_symbol(self, symbol: str) -> str:
        """
        Validate and normalize a stock symbol.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            Normalized symbol (uppercase, stripped)
            
        Raises:
            MarketDataValidationError: If symbol is invalid
        """
        if not symbol or not symbol.strip():
            raise MarketDataValidationError("Symbol cannot be empty")
        
        normalized = symbol.strip().upper()
        if not normalized.replace('-', '').replace('.', '').isalnum():
            raise MarketDataValidationError(f"Invalid symbol format: {symbol}")
            
        return normalized
    
    def _validate_symbols(self, symbols: List[str]) -> List[str]:
        """
        Validate and normalize a list of symbols.
        
        Args:
            symbols: List of symbols to validate
            
        Returns:
            List of normalized symbols
            
        Raises:
            MarketDataValidationError: If any symbol is invalid
        """
        if not symbols:
            raise MarketDataValidationError("Symbol list cannot be empty")
        
        normalized = []
        for symbol in symbols:
            try:
                normalized.append(self._validate_symbol(symbol))
            except MarketDataValidationError:
                logger.warning(f"Skipping invalid symbol: {symbol}")
                continue
        
        if not normalized:
            raise MarketDataValidationError("No valid symbols provided")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_symbols = []
        for symbol in normalized:
            if symbol not in seen:
                seen.add(symbol)
                unique_symbols.append(symbol)
        
        return unique_symbols
    
    async def _retry_request(self, func, *args, **kwargs):
        """
        Execute a request with exponential backoff retry logic.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result of func execution
            
        Raises:
            MarketDataConnectionError: If all retries failed
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    break
                
                # Exponential backoff: 1s, 2s, 4s
                delay = 2 ** attempt
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx), but retry server errors (5xx)
                if 400 <= e.response.status_code < 500:
                    raise
                last_exception = e
                if attempt == self.max_retries:
                    break
                    
                delay = 2 ** attempt
                logger.warning(f"Server error (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        raise MarketDataConnectionError(f"Failed to connect to Market Data Aggregator after {self.max_retries + 1} attempts: {last_exception}")
    
    async def health_check(self) -> bool:
        """
        Check if the Market Data Aggregator service is healthy.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            async def _health_request():
                response = await self.client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response
                
            response = await self._retry_request(_health_request)
            data = response.json()
            return data.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        """
        Get a single quote for a symbol.
        
        Args:
            symbol: Stock symbol to get quote for
            
        Returns:
            MarketQuote object or None if not found
            
        Raises:
            MarketDataValidationError: If symbol is invalid
            MarketDataConnectionError: If connection fails
        """
        try:
            # Validate and normalize symbol
            normalized_symbol = self._validate_symbol(symbol)
            
            async def _quote_request():
                response = await self.client.get(f"{self.base_url}/v1/quote/{normalized_symbol}")
                response.raise_for_status()
                return response
            
            response = await self._retry_request(_quote_request)
            data = response.json()
            return MarketQuote(**data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Quote not found for symbol: {normalized_symbol}")
                return None
            else:
                logger.error(f"HTTP error getting quote for {normalized_symbol}: {e}")
                raise MarketDataConnectionError(f"HTTP error getting quote for {normalized_symbol}: {e}")
        except MarketDataValidationError:
            raise
        except MarketDataConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise MarketDataClientError(f"Error getting quote for {symbol}: {e}")
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, MarketQuote]:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols: List of stock symbols to get quotes for
            
        Returns:
            Dictionary mapping symbols to MarketQuote objects
            
        Raises:
            MarketDataValidationError: If symbols are invalid
            MarketDataConnectionError: If connection fails
        """
        if not symbols:
            return {}
            
        try:
            # Validate and normalize symbols
            normalized_symbols = self._validate_symbols(symbols)
            
            async def _quotes_request():
                symbols_param = ','.join(normalized_symbols)
                response = await self.client.get(
                    f"{self.base_url}/v1/quotes",
                    params={"symbols": symbols_param}
                )
                response.raise_for_status()
                return response
            
            response = await self._retry_request(_quotes_request)
            data = response.json()
            quote_response = QuoteResponse(**data)
            
            # Convert to dictionary for easier access
            quotes_dict = {}
            for quote in quote_response.quotes:
                quotes_dict[quote.symbol] = quote
                
            logger.info(f"Retrieved {len(quotes_dict)} quotes for {len(normalized_symbols)} symbols")
            return quotes_dict
            
        except MarketDataValidationError:
            raise
        except MarketDataConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting quotes for symbols {symbols}: {e}")
            raise MarketDataClientError(f"Error getting quotes for symbols {symbols}: {e}")
    
    async def get_assets(self, asset_type: str = "stocks") -> List[MarketAsset]:
        """
        Get list of available assets.
        
        Args:
            asset_type: Type of assets to retrieve (stocks, crypto, forex)
            
        Returns:
            List of MarketAsset objects
            
        Raises:
            MarketDataConnectionError: If connection fails
        """
        try:
            async def _assets_request():
                response = await self.client.get(f"{self.base_url}/assets/{asset_type}")
                response.raise_for_status()
                return response
            
            response = await self._retry_request(_assets_request)
            data = response.json()
            asset_response = AssetListResponse(**data)
            
            logger.info(f"Retrieved {len(asset_response.assets)} {asset_type} assets")
            return asset_response.assets
            
        except MarketDataConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting {asset_type} assets: {e}")
            raise MarketDataClientError(f"Error getting {asset_type} assets: {e}")
    
    async def search_assets(self, query: str, asset_type: str = "stocks") -> List[MarketAsset]:
        """
        Search for assets by name or symbol.
        
        Args:
            query: Search query
            asset_type: Type of assets to search in
            
        Returns:
            List of matching MarketAsset objects
            
        Raises:
            MarketDataValidationError: If query is invalid
            MarketDataConnectionError: If connection fails
        """
        if not query or not query.strip():
            raise MarketDataValidationError("Search query cannot be empty")
            
        try:
            query_normalized = query.strip()
            
            async def _search_request():
                response = await self.client.get(
                    f"{self.base_url}/assets/{asset_type}/search",
                    params={"q": query_normalized}
                )
                response.raise_for_status()
                return response
            
            response = await self._retry_request(_search_request)
            data = response.json()
            asset_response = AssetListResponse(**data)
            
            logger.info(f"Found {len(asset_response.assets)} assets matching '{query_normalized}'")
            return asset_response.assets
            
        except MarketDataValidationError:
            raise
        except MarketDataConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error searching assets for '{query}': {e}")
            raise MarketDataClientError(f"Error searching assets for '{query}': {e}")
    
    async def get_general_news(self) -> List[Dict]:
        """Get general market news from aggregator."""
        try:
            async def _news_request():
                response = await self.client.get(f"{self.base_url}/v1/news/general")
                response.raise_for_status()
                return response
            
            response = await self._retry_request(_news_request)
            data = response.json()
            return data.get('articles', [])
        except Exception as e:
            logger.error(f"Error getting general news: {e}")
            return []

    async def get_company_news(self, symbol: str) -> List[Dict]:
        """Get company-specific news from aggregator."""
        try:
            normalized_symbol = self._validate_symbol(symbol)
            
            async def _news_request():
                response = await self.client.get(f"{self.base_url}/v1/news/{normalized_symbol}")
                response.raise_for_status()
                return response
            
            response = await self._retry_request(_news_request)
            data = response.json()
            return data.get('articles', [])
        except Exception as e:
            logger.error(f"Error getting company news for {symbol}: {e}")
            return []


# Global client instance
market_data_client = MarketDataClient()