"""
Abstract base class for data providers in Market Data Aggregator.
Defines the interface that all data providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
import httpx
import asyncio

from ..api.schemas import Asset, Quote, AssetType, DataProvider
from ..core.logging_config import create_logger

logger = create_logger(__name__)


class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, message: str, provider: str, symbol: Optional[str] = None):
        self.message = message
        self.provider = provider
        self.symbol = symbol
        super().__init__(self.message)


class RateLimitError(ProviderError):
    """Exception raised when provider rate limit is exceeded."""
    pass


class AuthenticationError(ProviderError):
    """Exception raised when provider authentication fails."""
    pass


class DataNotFoundError(ProviderError):
    """Exception raised when requested data is not found."""
    pass


class BaseDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    def __init__(self, name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_request_time = datetime.utcnow()
        self._rate_limit_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Initialize HTTP client connection."""
        if self.client is None:
            timeout = httpx.Timeout(30.0, connect=10.0)  # 30s total, 10s connect
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            
            self.client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers=self._get_default_headers(),
                follow_redirects=True
            )
            
            logger.debug("Connected to provider", extra={"provider": self.name})
    
    async def disconnect(self) -> None:
        """Close HTTP client connection."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("Disconnected from provider", extra={"provider": self.name})
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers for requests."""
        return {
            'User-Agent': 'Market-Data-Aggregator/1.0.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
    
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and error handling."""
        
        if not self.client:
            await self.connect()
        
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Merge headers
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)
        
        # Add authentication if available
        auth_headers = self._get_auth_headers()
        if auth_headers:
            request_headers.update(auth_headers)
        
        for attempt in range(retry_count):
            try:
                logger.debug("Making request to provider", extra={
                    "provider": self.name,
                    "method": method,
                    "url": url,
                    "attempt": attempt + 1
                })
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=request_headers,
                    json=data
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning("Rate limited by provider", extra={
                        "provider": self.name,
                        "retry_after": retry_after
                    })
                    
                    if attempt < retry_count - 1:
                        await asyncio.sleep(min(retry_after, 60))  # Max 60 seconds
                        continue
                    else:
                        raise RateLimitError(
                            f"Rate limited by {self.name}",
                            self.name
                        )
                
                # Check for authentication errors
                if response.status_code == 401:
                    raise AuthenticationError(
                        f"Authentication failed for {self.name}",
                        self.name
                    )
                
                # Check for other HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    data = response.json()
                    logger.debug("Received response from provider", extra={
                        "provider": self.name,
                        "status_code": response.status_code,
                        "response_size": len(response.content)
                    })
                    return data
                    
                except ValueError as e:
                    raise ProviderError(
                        f"Invalid JSON response from {self.name}: {str(e)}",
                        self.name
                    )
                
            except httpx.TimeoutException:
                logger.warning("Request timeout", extra={
                    "provider": self.name,
                    "attempt": attempt + 1,
                    "url": url
                })
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise ProviderError(
                        f"Request timeout for {self.name}",
                        self.name
                    )
                    
            except httpx.HTTPError as e:
                logger.warning("HTTP error", extra={
                    "provider": self.name,
                    "error": str(e),
                    "attempt": attempt + 1
                })
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise ProviderError(
                        f"HTTP error for {self.name}: {str(e)}",
                        self.name
                    )
        
        raise ProviderError(f"Max retries exceeded for {self.name}", self.name)
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting to requests."""
        async with self._rate_limit_lock:
            now = datetime.utcnow()
            
            # Reset counter if more than a minute has passed
            if (now - self._last_request_time).total_seconds() > 60:
                self._request_count = 0
                self._last_request_time = now
            
            # Check if we need to wait
            max_requests_per_minute = self._get_rate_limit()
            if self._request_count >= max_requests_per_minute:
                wait_time = 60 - (now - self._last_request_time).total_seconds()
                if wait_time > 0:
                    logger.debug("Rate limiting request", extra={
                        "provider": self.name,
                        "wait_time": wait_time
                    })
                    await asyncio.sleep(wait_time)
                    self._request_count = 0
                    self._last_request_time = datetime.utcnow()
            
            self._request_count += 1
    
    @abstractmethod
    def _get_rate_limit(self) -> int:
        """Get the rate limit for this provider (requests per minute)."""
        pass
    
    @abstractmethod
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Get authentication headers for this provider."""
        pass
    
    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """
        Get real-time quotes for the given symbols.
        
        Args:
            symbols: List of symbols to get quotes for
            
        Returns:
            Dictionary mapping symbols to Quote objects
            
        Raises:
            ProviderError: If unable to fetch quotes
        """
        pass
    
    @abstractmethod
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """
        Get list of available assets for the given type.
        
        Args:
            asset_type: Type of assets to retrieve
            
        Returns:
            List of Asset objects
            
        Raises:
            ProviderError: If unable to fetch asset list
        """
        pass
    
    @abstractmethod
    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """
        Check if this provider supports the given asset type.
        
        Args:
            asset_type: Asset type to check
            
        Returns:
            True if asset type is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> DataProvider:
        """Get the provider enum value."""
        pass
    
    def _normalize_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """
        Normalize symbol for this provider.
        Different providers may use different symbol formats.
        
        Args:
            symbol: Original symbol
            asset_type: Type of asset
            
        Returns:
            Normalized symbol for this provider
        """
        # Default implementation - return as-is
        return symbol.upper().strip()
    
    def _create_quote(
        self,
        symbol: str,
        price: float,
        timestamp: Optional[datetime] = None,
        **kwargs
    ) -> Quote:
        """
        Create a standardized Quote object.
        
        Args:
            symbol: Asset symbol
            price: Current price
            timestamp: Quote timestamp
            **kwargs: Additional quote data
            
        Returns:
            Quote object
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        return Quote(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
            source=self.get_provider_name(),
            change=kwargs.get('change'),
            percent_change=kwargs.get('percent_change'),
            volume=kwargs.get('volume'),
            market_cap=kwargs.get('market_cap'),
            high_24h=kwargs.get('high_24h'),
            low_24h=kwargs.get('low_24h'),
            open_price=kwargs.get('open_price'),
            close_price=kwargs.get('close_price'),
            bid=kwargs.get('bid'),
            ask=kwargs.get('ask'),
            currency=kwargs.get('currency'),
            asset_type=kwargs.get('asset_type')
        )
    
    def _create_asset(
        self,
        symbol: str,
        name: str,
        asset_type: AssetType,
        **kwargs
    ) -> Asset:
        """
        Create a standardized Asset object.
        
        Args:
            symbol: Asset symbol
            name: Asset name
            asset_type: Asset type
            **kwargs: Additional asset data
            
        Returns:
            Asset object
        """
        return Asset(
            symbol=symbol,
            name=name,
            asset_type=asset_type,
            exchange=kwargs.get('exchange'),
            currency=kwargs.get('currency'),
            is_active=kwargs.get('is_active', True),
            metadata=kwargs.get('metadata', {})
        )
    
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and responding.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Implement a simple health check - try to get a quote for a common symbol
            if self.supports_asset_type(AssetType.STOCKS):
                test_symbols = ['AAPL']
            elif self.supports_asset_type(AssetType.CRYPTO):
                test_symbols = ['BTC-USD']
            elif self.supports_asset_type(AssetType.FOREX):
                test_symbols = ['EUR/USD']
            else:
                return True  # If provider doesn't support any known asset types
            
            quotes = await self.get_quotes(test_symbols)
            return len(quotes) > 0
            
        except Exception as e:
            logger.warning("Provider health check failed", extra={
                "provider": self.name,
                "error": str(e)
            })
            return False