"""
CoinMarketCap data provider implementation.
Provides cryptocurrency market data using CoinMarketCap API.
"""

from datetime import datetime
from typing import Dict, List, Optional

from .base import BaseDataProvider, ProviderError, AuthenticationError
from ..api.schemas import Asset, Quote, AssetType, DataProvider
from ..core.config import settings
from ..core.logging_config import create_logger

logger = create_logger(__name__)


class CoinMarketCapProvider(BaseDataProvider):
    """CoinMarketCap data provider for cryptocurrency data."""
    
    def __init__(self):
        super().__init__(
            name="coinmarketcap",
            api_key=settings.coinmarketcap_api_key,
            base_url="https://pro-api.coinmarketcap.com/v1"
        )
    
    def _get_rate_limit(self) -> int:
        """CoinMarketCap basic plan allows 333 calls per day."""
        return 15  # Conservative: 15 requests per minute (about 21600 per day)
    
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """CoinMarketCap uses API key in headers."""
        if not self.api_key:
            return None
        
        return {
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json'
        }
    
    def get_provider_name(self) -> DataProvider:
        """Get provider enum value."""
        return DataProvider.COINMARKETCAP
    
    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """CoinMarketCap supports crypto only."""
        return asset_type == AssetType.CRYPTO
    
    async def connect(self) -> None:
        """Initialize connection and validate API key."""
        await super().connect()
        
        if not self.api_key:
            raise AuthenticationError("CoinMarketCap API key is required", self.name)
        
        # Test API key with a simple request
        try:
            await self._make_request(
                method="GET",
                url=f"{self.base_url}/key/info"
            )
            logger.debug("Connected to CoinMarketCap", extra={"provider": self.name})
        except Exception as e:
            raise AuthenticationError(f"CoinMarketCap API key validation failed: {str(e)}", self.name)
    
    def _normalize_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """Normalize crypto symbol for CoinMarketCap format."""
        symbol = symbol.upper().strip()
        
        # Remove common suffixes
        if symbol.endswith('-USD'):
            symbol = symbol[:-4]
        elif symbol.endswith('USD'):
            symbol = symbol[:-3]
        elif symbol.endswith('-USDT'):
            symbol = symbol[:-5]
        
        return symbol
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes from CoinMarketCap."""
        if not symbols:
            return {}
        
        try:
            # Normalize symbols
            normalized_symbols = [self._normalize_symbol(s, AssetType.CRYPTO) for s in symbols]
            
            # Get quotes from CoinMarketCap
            quotes_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/cryptocurrency/quotes/latest",
                params={
                    'symbol': ','.join(normalized_symbols),
                    'convert': 'USD'
                }
            )
            
            if not quotes_data or 'data' not in quotes_data:
                return {}
            
            quotes = {}
            data = quotes_data['data']
            
            for i, original_symbol in enumerate(symbols):
                normalized_symbol = normalized_symbols[i]
                
                if normalized_symbol not in data:
                    logger.warning("No data for symbol", extra={
                        "provider": self.name,
                        "symbol": original_symbol
                    })
                    continue
                
                coin_data = data[normalized_symbol]
                if not coin_data or 'quote' not in coin_data:
                    continue
                
                usd_quote = coin_data['quote'].get('USD', {})
                if not usd_quote:
                    continue
                
                price = usd_quote.get('price')
                if not price or price <= 0:
                    continue
                
                quote = self._create_quote(
                    symbol=original_symbol,
                    price=price,
                    timestamp=datetime.utcnow(),
                    change=usd_quote.get('change_24h'),
                    percent_change=usd_quote.get('percent_change_24h'),
                    volume=usd_quote.get('volume_24h'),
                    market_cap=usd_quote.get('market_cap'),
                    currency="USD",
                    asset_type=AssetType.CRYPTO
                )
                
                quotes[original_symbol] = quote
            
            logger.info("Retrieved quotes from CoinMarketCap", extra={
                "provider": self.name,
                "requested": len(symbols),
                "successful": len(quotes)
            })
            
            return quotes
            
        except Exception as e:
            logger.error("Failed to fetch quotes from CoinMarketCap", extra={
                "provider": self.name,
                "symbols": symbols,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch quotes: {str(e)}", self.name)
    
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """Get list of available cryptocurrencies from CoinMarketCap."""
        if not self.supports_asset_type(asset_type):
            return []
        
        try:
            # Get cryptocurrency listings
            listings_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/cryptocurrency/listings/latest",
                params={
                    'start': 1,
                    'limit': 500,  # Limit to top 500 for performance
                    'convert': 'USD'
                }
            )
            
            if not listings_data or 'data' not in listings_data:
                return []
            
            assets = []
            for coin_info in listings_data['data']:
                try:
                    symbol = coin_info.get('symbol', '').strip()
                    name = coin_info.get('name', '').strip()
                    
                    if not symbol or not name:
                        continue
                    
                    asset = self._create_asset(
                        symbol=symbol,
                        name=name,
                        asset_type=AssetType.CRYPTO,
                        exchange="Crypto",
                        currency="USD",
                        is_active=True,
                        metadata={
                            'cmc_id': coin_info.get('id'),
                            'slug': coin_info.get('slug'),
                            'cmc_rank': coin_info.get('cmc_rank'),
                            'platform': coin_info.get('platform')
                        }
                    )
                    assets.append(asset)
                    
                except Exception as e:
                    logger.warning("Failed to process crypto asset", extra={
                        "provider": self.name,
                        "coin_info": coin_info,
                        "error": str(e)
                    })
                    continue
            
            logger.info("Retrieved asset list from CoinMarketCap", extra={
                "provider": self.name,
                "count": len(assets)
            })
            
            return assets
            
        except Exception as e:
            logger.error("Failed to fetch asset list from CoinMarketCap", extra={
                "provider": self.name,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch asset list: {str(e)}", self.name)