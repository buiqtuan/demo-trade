"""
Finnhub data provider implementation.
Provides stock market data using Finnhub API.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import finnhub

from .base import BaseDataProvider, ProviderError, AuthenticationError
from ..api.schemas import Asset, Quote, AssetType, DataProvider
from ..core.config import settings
from ..core.logging_config import create_logger

# Import shared models with proper fallback
try:
    from shared_models.market_data import NewsArticle
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from shared_models.market_data import NewsArticle

logger = create_logger(__name__)


class FinnhubProvider(BaseDataProvider):
    """Finnhub data provider for stock market data."""
    
    def __init__(self):
        super().__init__(
            name="finnhub",
            api_key=settings.finnhub_api_key,
            base_url="https://finnhub.io/api/v1"
        )
        self._client = None
    
    def _get_rate_limit(self) -> int:
        """Finnhub free tier allows 60 calls per minute."""
        return 50  # Conservative: 50 requests per minute
    
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Finnhub uses API key in query parameters, not headers."""
        return None
    
    def get_provider_name(self) -> DataProvider:
        """Get provider enum value."""
        return DataProvider.FINNHUB
    
    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """Finnhub supports stocks only."""
        return asset_type == AssetType.STOCKS
    
    async def connect(self) -> None:
        """Initialize Finnhub client."""
        await super().connect()
        if not self.api_key:
            raise AuthenticationError("Finnhub API key is required", self.name)
        
        self._client = finnhub.Client(api_key=self.api_key)
        logger.debug("Connected to Finnhub", extra={"provider": self.name})
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes from Finnhub."""
        if not symbols:
            return {}
        
        if not self._client:
            await self.connect()
        
        quotes = {}
        
        for symbol in symbols:
            try:
                # Get real-time quote
                quote_data = await self._make_request(
                    method="GET",
                    url=f"{self.base_url}/quote",
                    params={
                        "symbol": symbol.upper(),
                        "token": self.api_key
                    }
                )
                
                if not quote_data or 'c' not in quote_data:
                    logger.warning("No quote data for symbol", extra={
                        "provider": self.name,
                        "symbol": symbol
                    })
                    continue
                
                current_price = quote_data['c']  # Current price
                if current_price <= 0:
                    continue
                
                # Calculate change and percent change
                previous_close = quote_data.get('pc', 0)  # Previous close
                change = current_price - previous_close if previous_close > 0 else None
                percent_change = (change / previous_close * 100) if change is not None and previous_close > 0 else None
                
                quote = self._create_quote(
                    symbol=symbol,
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    change=change,
                    percent_change=percent_change,
                    high_24h=quote_data.get('h'),  # High price of the day
                    low_24h=quote_data.get('l'),   # Low price of the day
                    open_price=quote_data.get('o'), # Open price of the day
                    close_price=previous_close,
                    currency="USD",
                    asset_type=AssetType.STOCKS
                )
                
                quotes[symbol] = quote
                
            except Exception as e:
                logger.warning("Failed to fetch quote for symbol", extra={
                    "provider": self.name,
                    "symbol": symbol,
                    "error": str(e)
                })
                continue
        
        logger.info("Retrieved quotes from Finnhub", extra={
            "provider": self.name,
            "requested": len(symbols),
            "successful": len(quotes)
        })
        
        return quotes
    
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """Get list of available stocks from Finnhub."""
        if not self.supports_asset_type(asset_type):
            return []
        
        if not self._client:
            await self.connect()
        
        try:
            # Get US stock symbols
            symbols_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/stock/symbol",
                params={
                    "exchange": "US",
                    "token": self.api_key
                }
            )
            
            if not symbols_data:
                return []
            
            assets = []
            for symbol_info in symbols_data[:1000]:  # Limit to first 1000 for performance
                try:
                    symbol = symbol_info.get('symbol', '').strip()
                    description = symbol_info.get('description', '').strip()
                    
                    if not symbol or not description:
                        continue
                    
                    # Filter out some unwanted symbol types
                    if any(x in symbol for x in ['.', '-', '/', '^']):
                        continue
                    
                    asset = self._create_asset(
                        symbol=symbol,
                        name=description,
                        asset_type=AssetType.STOCKS,
                        exchange="US",
                        currency=symbol_info.get('currency', 'USD'),
                        is_active=True,
                        metadata={
                            'figi': symbol_info.get('figi'),
                            'type': symbol_info.get('type')
                        }
                    )
                    assets.append(asset)
                    
                except Exception as e:
                    logger.warning("Failed to process asset", extra={
                        "provider": self.name,
                        "symbol_info": symbol_info,
                        "error": str(e)
                    })
                    continue
            
            logger.info("Retrieved asset list from Finnhub", extra={
                "provider": self.name,
                "count": len(assets)
            })
            
            return assets
            
        except Exception as e:
            logger.error("Failed to fetch asset list from Finnhub", extra={
                "provider": self.name,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch asset list: {str(e)}", self.name)
    
    async def get_general_news(self) -> List[NewsArticle]:
        """Get general market news from Finnhub."""
        if not self._client:
            await self.connect()
        
        try:
            # Get general market news
            news_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/news",
                params={
                    "category": "general",
                    "token": self.api_key
                }
            )
            
            if not news_data:
                logger.warning("No general news data received from Finnhub", extra={
                    "provider": self.name
                })
                return []
            
            articles = []
            for item in news_data[:50]:  # Limit to 50 articles
                try:
                    article = self._create_news_article_from_finnhub(item)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning("Failed to process news article", extra={
                        "provider": self.name,
                        "error": str(e),
                        "article_data": item
                    })
                    continue
            
            logger.info("Retrieved general news from Finnhub", extra={
                "provider": self.name,
                "count": len(articles)
            })
            
            return articles
            
        except Exception as e:
            logger.error("Failed to fetch general news from Finnhub", extra={
                "provider": self.name,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch general news: {str(e)}", self.name)
    
    async def get_company_news(self, symbol: str) -> List[NewsArticle]:
        """Get company-specific news from Finnhub."""
        if not symbol or not symbol.strip():
            return []
        
        if not self._client:
            await self.connect()
        
        try:
            # Calculate date range (last 30 days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            # Get company news
            news_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/company-news",
                params={
                    "symbol": symbol.upper(),
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "token": self.api_key
                }
            )
            
            if not news_data:
                logger.info("No company news data received from Finnhub", extra={
                    "provider": self.name,
                    "symbol": symbol
                })
                return []
            
            articles = []
            for item in news_data[:30]:  # Limit to 30 articles
                try:
                    article = self._create_news_article_from_finnhub(item, symbol)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning("Failed to process company news article", extra={
                        "provider": self.name,
                        "symbol": symbol,
                        "error": str(e),
                        "article_data": item
                    })
                    continue
            
            logger.info("Retrieved company news from Finnhub", extra={
                "provider": self.name,
                "symbol": symbol,
                "count": len(articles)
            })
            
            return articles
            
        except Exception as e:
            logger.error("Failed to fetch company news from Finnhub", extra={
                "provider": self.name,
                "symbol": symbol,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch company news for {symbol}: {str(e)}", self.name)
    
    def _create_news_article_from_finnhub(self, item: Dict, symbol: Optional[str] = None) -> Optional[NewsArticle]:
        """Create NewsArticle from Finnhub news data."""
        try:
            # Validate required fields
            if not all(key in item for key in ['headline', 'url', 'datetime']):
                logger.warning("Missing required fields in Finnhub news item", extra={
                    "provider": self.name,
                    "item": item
                })
                return None
            
            title = item.get('headline', '').strip()
            url = item.get('url', '').strip()
            
            if not title or not url:
                return None
            
            # Convert timestamp
            timestamp = datetime.utcfromtimestamp(item['datetime'])
            
            # Extract other fields
            summary = item.get('summary', '').strip() or None
            source = item.get('source', 'Finnhub').strip()
            category = item.get('category', 'general').strip()
            
            # Handle symbols
            symbols = []
            if symbol:
                symbols = [symbol.upper()]
            elif 'related' in item and item['related']:
                symbols = [s.upper() for s in item['related'] if s]
            
            return NewsArticle(
                title=title,
                summary=summary,
                url=url,
                source=source,
                published_at=timestamp,
                symbols=symbols,
                category=category,
                sentiment=None  # Finnhub doesn't provide sentiment in basic response
            )
            
        except Exception as e:
            logger.warning("Error creating news article from Finnhub data", extra={
                "provider": self.name,
                "error": str(e),
                "item": item
            })
            return None