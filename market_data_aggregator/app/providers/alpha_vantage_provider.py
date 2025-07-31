"""
Alpha Vantage data provider implementation.
Provides forex and stock market data using Alpha Vantage API.
"""

from datetime import datetime
from typing import Dict, List, Optional
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.timeseries import TimeSeries

from .base import BaseDataProvider, ProviderError, AuthenticationError
from ..api.schemas import Asset, Quote, AssetType, DataProvider
from ..core.config import settings
from ..core.logging_config import create_logger

logger = create_logger(__name__)


class AlphaVantageProvider(BaseDataProvider):
    """Alpha Vantage data provider for forex and stock data."""
    
    def __init__(self):
        super().__init__(
            name="alpha_vantage",
            api_key=settings.alpha_vantage_api_key,
            base_url="https://www.alphavantage.co/query"
        )
        self._fx_client = None
        self._ts_client = None
    
    def _get_rate_limit(self) -> int:
        """Alpha Vantage free tier allows 5 calls per minute."""
        return 4  # Conservative: 4 requests per minute
    
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Alpha Vantage uses API key in query parameters."""
        return None
    
    def get_provider_name(self) -> DataProvider:
        """Get provider enum value."""
        return DataProvider.ALPHA_VANTAGE
    
    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """Alpha Vantage supports forex and stocks."""
        return asset_type in [AssetType.FOREX, AssetType.STOCKS]
    
    async def connect(self) -> None:
        """Initialize Alpha Vantage clients."""
        await super().connect()
        
        if not self.api_key:
            raise AuthenticationError("Alpha Vantage API key is required", self.name)
        
        self._fx_client = ForeignExchange(key=self.api_key, output_format='json')
        self._ts_client = TimeSeries(key=self.api_key, output_format='json')
        
        logger.debug("Connected to Alpha Vantage", extra={"provider": self.name})
    
    def _normalize_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """Normalize symbol for Alpha Vantage format."""
        symbol = symbol.upper().strip()
        
        if asset_type == AssetType.FOREX:
            # Alpha Vantage expects forex pairs as from_currency and to_currency
            if '/' in symbol:
                return symbol  # Already in correct format
            elif len(symbol) == 6:
                # Assume EURUSD format, convert to EUR/USD
                return f"{symbol[:3]}/{symbol[3:]}"
        
        return symbol
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes from Alpha Vantage."""
        if not symbols:
            return {}
        
        if not self._fx_client or not self._ts_client:
            await self.connect()
        
        quotes = {}
        
        for symbol in symbols:
            try:
                # Determine asset type based on symbol
                if '/' in symbol or len(symbol.replace('/', '')) == 6:
                    asset_type = AssetType.FOREX
                    quote = await self._get_forex_quote(symbol)
                else:
                    asset_type = AssetType.STOCKS
                    quote = await self._get_stock_quote(symbol)
                
                if quote:
                    quotes[symbol] = quote
                    
            except Exception as e:
                logger.warning("Failed to fetch quote for symbol", extra={
                    "provider": self.name,
                    "symbol": symbol,
                    "error": str(e)
                })
                continue
        
        logger.info("Retrieved quotes from Alpha Vantage", extra={
            "provider": self.name,
            "requested": len(symbols),
            "successful": len(quotes)
        })
        
        return quotes
    
    async def _get_forex_quote(self, symbol: str) -> Optional[Quote]:
        """Get forex quote from Alpha Vantage."""
        try:
            # Parse currency pair
            if '/' in symbol:
                from_currency, to_currency = symbol.split('/')
            elif len(symbol) == 6:
                from_currency = symbol[:3]
                to_currency = symbol[3:]
            else:
                logger.warning("Invalid forex symbol format", extra={
                    "provider": self.name,
                    "symbol": symbol
                })
                return None
            
            # Get exchange rate data
            exchange_rate_data = await self._make_request(
                method="GET",
                url=self.base_url,
                params={
                    'function': 'CURRENCY_EXCHANGE_RATE',
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'apikey': self.api_key
                }
            )
            
            if not exchange_rate_data or 'Realtime Currency Exchange Rate' not in exchange_rate_data:
                return None
            
            rate_data = exchange_rate_data['Realtime Currency Exchange Rate']
            
            exchange_rate = float(rate_data.get('5. Exchange Rate', 0))
            if exchange_rate <= 0:
                return None
            
            bid_price = rate_data.get('8. Bid Price')
            ask_price = rate_data.get('9. Ask Price')
            
            quote = self._create_quote(
                symbol=symbol,
                price=exchange_rate,
                timestamp=datetime.utcnow(),
                bid=float(bid_price) if bid_price else None,
                ask=float(ask_price) if ask_price else None,
                currency=to_currency,
                asset_type=AssetType.FOREX
            )
            
            return quote
            
        except Exception as e:
            logger.error("Failed to fetch forex quote", extra={
                "provider": self.name,
                "symbol": symbol,
                "error": str(e)
            })
            return None
    
    async def _get_stock_quote(self, symbol: str) -> Optional[Quote]:
        """Get stock quote from Alpha Vantage."""
        try:
            # Get global quote data
            quote_data = await self._make_request(
                method="GET",
                url=self.base_url,
                params={
                    'function': 'GLOBAL_QUOTE',
                    'symbol': symbol,
                    'apikey': self.api_key
                }
            )
            
            if not quote_data or 'Global Quote' not in quote_data:
                return None
            
            global_quote = quote_data['Global Quote']
            
            price = float(global_quote.get('05. price', 0))
            if price <= 0:
                return None
            
            change = global_quote.get('09. change')
            change_percent = global_quote.get('10. change percent')
            
            # Parse change percent (remove % sign)
            if change_percent:
                change_percent = change_percent.replace('%', '').strip()
                try:
                    change_percent = float(change_percent)
                except ValueError:
                    change_percent = None
            
            quote = self._create_quote(
                symbol=symbol,
                price=price,
                timestamp=datetime.utcnow(),
                change=float(change) if change else None,
                percent_change=change_percent,
                volume=int(float(global_quote.get('06. volume', 0))),
                high_24h=float(global_quote.get('03. high', 0)) or None,
                low_24h=float(global_quote.get('04. low', 0)) or None,
                open_price=float(global_quote.get('02. open', 0)) or None,
                close_price=float(global_quote.get('08. previous close', 0)) or None,
                currency="USD",
                asset_type=AssetType.STOCKS
            )
            
            return quote
            
        except Exception as e:
            logger.error("Failed to fetch stock quote", extra={
                "provider": self.name,
                "symbol": symbol,
                "error": str(e)
            })
            return None
    
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """Get list of available assets from Alpha Vantage."""
        if not self.supports_asset_type(asset_type):
            return []
        
        try:
            if asset_type == AssetType.FOREX:
                return await self._get_forex_list()
            elif asset_type == AssetType.STOCKS:
                return await self._get_stock_list()
            else:
                return []
                
        except Exception as e:
            logger.error("Failed to fetch asset list from Alpha Vantage", extra={
                "provider": self.name,
                "asset_type": asset_type.value,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch asset list: {str(e)}", self.name)
    
    async def _get_forex_list(self) -> List[Asset]:
        """Get list of major forex pairs."""
        # Alpha Vantage doesn't provide a forex pairs listing API
        # Using a curated list of major and minor pairs
        forex_pairs = [
            ("EUR/USD", "Euro / US Dollar"),
            ("GBP/USD", "British Pound / US Dollar"),
            ("USD/JPY", "US Dollar / Japanese Yen"),
            ("USD/CHF", "US Dollar / Swiss Franc"),
            ("AUD/USD", "Australian Dollar / US Dollar"),
            ("USD/CAD", "US Dollar / Canadian Dollar"),
            ("NZD/USD", "New Zealand Dollar / US Dollar"),
            ("EUR/GBP", "Euro / British Pound"),
            ("EUR/JPY", "Euro / Japanese Yen"),
            ("GBP/JPY", "British Pound / Japanese Yen"),
            ("EUR/CHF", "Euro / Swiss Franc"),
            ("GBP/CHF", "British Pound / Swiss Franc"),
            ("AUD/JPY", "Australian Dollar / Japanese Yen"),
            ("CAD/JPY", "Canadian Dollar / Japanese Yen"),
            ("CHF/JPY", "Swiss Franc / Japanese Yen"),
            ("EUR/AUD", "Euro / Australian Dollar"),
            ("EUR/CAD", "Euro / Canadian Dollar"),
            ("GBP/AUD", "British Pound / Australian Dollar"),
            ("AUD/CAD", "Australian Dollar / Canadian Dollar"),
            ("NZD/JPY", "New Zealand Dollar / Japanese Yen")
        ]
        
        assets = []
        for symbol, name in forex_pairs:
            asset = self._create_asset(
                symbol=symbol,
                name=name,
                asset_type=AssetType.FOREX,
                exchange="Forex",
                currency="Various",
                is_active=True
            )
            assets.append(asset)
        
        logger.info("Retrieved forex list from Alpha Vantage", extra={
            "provider": self.name,
            "count": len(assets)
        })
        
        return assets
    
    async def _get_stock_list(self) -> List[Asset]:
        """Get list of popular stocks."""
        # Alpha Vantage doesn't provide a comprehensive stock listing API
        # Using a curated list of popular stocks
        popular_stocks = [
            ("AAPL", "Apple Inc."),
            ("MSFT", "Microsoft Corporation"),
            ("GOOGL", "Alphabet Inc."),
            ("AMZN", "Amazon.com Inc."),
            ("TSLA", "Tesla Inc."),
            ("META", "Meta Platforms Inc."),
            ("NVDA", "NVIDIA Corporation"),
            ("BRK.B", "Berkshire Hathaway Inc."),
            ("JNJ", "Johnson & Johnson"),
            ("V", "Visa Inc."),
            ("WMT", "Walmart Inc."),
            ("JPM", "JPMorgan Chase & Co."),
            ("MA", "Mastercard Incorporated"),
            ("PG", "The Procter & Gamble Company"),
            ("UNH", "UnitedHealth Group Incorporated"),
            ("DIS", "The Walt Disney Company"),
            ("HD", "The Home Depot Inc."),
            ("BAC", "Bank of America Corporation"),
            ("ADBE", "Adobe Inc."),
            ("CRM", "Salesforce Inc.")
        ]
        
        assets = []
        for symbol, name in popular_stocks:
            asset = self._create_asset(
                symbol=symbol,
                name=name,
                asset_type=AssetType.STOCKS,
                exchange="NASDAQ/NYSE",
                currency="USD",
                is_active=True
            )
            assets.append(asset)
        
        logger.info("Retrieved stock list from Alpha Vantage", extra={
            "provider": self.name,
            "count": len(assets)
        })
        
        return assets