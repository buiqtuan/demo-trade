"""
CoinGecko data provider implementation.
Provides cryptocurrency market data using CoinGecko API.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pycoingecko import CoinGeckoAPI

from .base import BaseDataProvider, ProviderError
from ..api.schemas import Asset, Quote, AssetType, DataProvider
from ..core.config import settings
from ..core.logging_config import create_logger

logger = create_logger(__name__)


class CoinGeckoProvider(BaseDataProvider):
    """CoinGecko data provider for cryptocurrency data."""
    
    def __init__(self):
        super().__init__(
            name="coingecko",
            base_url=settings.coingecko_api_url
        )
        self._client = None
    
    def _get_rate_limit(self) -> int:
        """CoinGecko free tier allows 50 calls per minute."""
        return 40  # Conservative: 40 requests per minute
    
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """CoinGecko free tier doesn't require authentication."""
        return None
    
    def get_provider_name(self) -> DataProvider:
        """Get provider enum value."""
        return DataProvider.COINGECKO
    
    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """CoinGecko supports crypto only."""
        return asset_type == AssetType.CRYPTO
    
    async def connect(self) -> None:
        """Initialize CoinGecko client."""
        await super().connect()
        self._client = CoinGeckoAPI()
        logger.debug("Connected to CoinGecko", extra={"provider": self.name})
    
    def _normalize_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """Normalize crypto symbol for CoinGecko format."""
        symbol = symbol.upper().strip()
        
        # Remove common suffixes that CoinGecko doesn't use
        if symbol.endswith('-USD'):
            symbol = symbol[:-4]
        elif symbol.endswith('USD'):
            symbol = symbol[:-3]
        elif symbol.endswith('-USDT'):
            symbol = symbol[:-5]
        
        return symbol
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes from CoinGecko."""
        if not symbols:
            return {}
        
        if not self._client:
            await self.connect()
        
        try:
            # Normalize symbols to CoinGecko IDs
            symbol_ids = []
            symbol_map = {}  # Map CoinGecko ID to original symbol
            
            for symbol in symbols:
                normalized = self._normalize_symbol(symbol, AssetType.CRYPTO)
                # Convert common symbols to CoinGecko IDs
                coingecko_id = self._symbol_to_coingecko_id(normalized)
                if coingecko_id:
                    symbol_ids.append(coingecko_id)
                    symbol_map[coingecko_id] = symbol
            
            if not symbol_ids:
                return {}
            
            # Get price data from CoinGecko
            price_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/simple/price",
                params={
                    'ids': ','.join(symbol_ids),
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'true',
                    'include_24hr_vol': 'true',
                    'include_market_cap': 'true'
                }
            )
            
            quotes = {}
            for coingecko_id, data in price_data.items():
                original_symbol = symbol_map[coingecko_id]
                
                if 'usd' not in data:
                    continue
                
                price = data['usd']
                change_24h = data.get('usd_24h_change')
                volume_24h = data.get('usd_24h_vol')
                market_cap = data.get('usd_market_cap')
                
                quote = self._create_quote(
                    symbol=original_symbol,
                    price=price,
                    timestamp=datetime.utcnow(),
                    percent_change=change_24h,
                    volume=int(volume_24h) if volume_24h else None,
                    market_cap=market_cap,
                    currency="USD",
                    asset_type=AssetType.CRYPTO
                )
                
                quotes[original_symbol] = quote
            
            logger.info("Retrieved quotes from CoinGecko", extra={
                "provider": self.name,
                "requested": len(symbols),
                "successful": len(quotes)
            })
            
            return quotes
            
        except Exception as e:
            logger.error("Failed to fetch quotes from CoinGecko", extra={
                "provider": self.name,
                "symbols": symbols,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch quotes: {str(e)}", self.name)
    
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """Get list of available cryptocurrencies from CoinGecko."""
        if not self.supports_asset_type(asset_type):
            return []
        
        if not self._client:
            await self.connect()
        
        try:
            # Get list of all coins
            coins_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/coins/list"
            )
            
            if not coins_data:
                return []
            
            assets = []
            # Limit to top 500 coins for performance
            for coin_info in coins_data[:500]:
                try:
                    coin_id = coin_info.get('id', '').strip()
                    symbol = coin_info.get('symbol', '').strip().upper()
                    name = coin_info.get('name', '').strip()
                    
                    if not coin_id or not symbol or not name:
                        continue
                    
                    asset = self._create_asset(
                        symbol=symbol,
                        name=name,
                        asset_type=AssetType.CRYPTO,
                        exchange="Crypto",
                        currency="USD",
                        is_active=True,
                        metadata={
                            'coingecko_id': coin_id
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
            
            logger.info("Retrieved asset list from CoinGecko", extra={
                "provider": self.name,
                "count": len(assets)
            })
            
            return assets
            
        except Exception as e:
            logger.error("Failed to fetch asset list from CoinGecko", extra={
                "provider": self.name,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch asset list: {str(e)}", self.name)
    
    def _symbol_to_coingecko_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to CoinGecko ID."""
        # Common cryptocurrency symbol mappings
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'XRP': 'ripple',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'LINK': 'chainlink',
            'XLM': 'stellar',
            'DOGE': 'dogecoin',
            'UNI': 'uniswap',
            'AAVE': 'aave',
            'SUSHI': 'sushi',
            'COMP': 'compound-governance-token',
            'MKR': 'maker',
            'SNX': 'havven',
            'CRV': 'curve-dao-token',
            'YFI': 'yearn-finance',
            '1INCH': '1inch',
            'MATIC': 'matic-network',
            'AVAX': 'avalanche-2',
            'SOL': 'solana',
            'LUNA': 'terra-luna',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'ICP': 'internet-computer',
            'FIL': 'filecoin',
            'TRX': 'tron',
            'XTZ': 'tezos',
            'EOS': 'eos',
            'ATOM': 'cosmos',
            'XMR': 'monero',
            'NEO': 'neo',
            'IOTA': 'iota',
            'ZEC': 'zcash',
            'DASH': 'dash'
        }
        
        return symbol_map.get(symbol.upper())