"""
Yahoo Finance data provider implementation.
Provides stock and forex market data using yfinance library.
"""

from datetime import datetime
from typing import Dict, List, Optional
import yfinance as yf
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import BaseDataProvider, ProviderError, DataNotFoundError
from ..api.schemas import Asset, Quote, AssetType, DataProvider
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


class YFinanceProvider(BaseDataProvider):
    """Yahoo Finance data provider."""
    
    def __init__(self):
        super().__init__(name="yfinance")
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def _get_rate_limit(self) -> int:
        """Yahoo Finance allows approximately 2000 requests per hour."""
        return 30  # Conservative: 30 requests per minute
    
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Yahoo Finance doesn't require authentication."""
        return None
    
    def get_provider_name(self) -> DataProvider:
        """Get provider enum value."""
        return DataProvider.YFINANCE
    
    def supports_asset_type(self, asset_type: AssetType) -> bool:
        """Yahoo Finance supports stocks and forex."""
        return asset_type in [AssetType.STOCKS, AssetType.FOREX]
    
    def _normalize_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """Normalize symbol for Yahoo Finance format."""
        symbol = symbol.upper().strip()
        
        if asset_type == AssetType.FOREX:
            # Convert standard forex notation to Yahoo format
            if '/' in symbol:
                base, quote = symbol.split('/')
                return f"{base}{quote}=X"
            elif symbol.endswith('=X'):
                return symbol
            else:
                # Assume it's already in correct format or needs =X suffix
                return f"{symbol}=X" if len(symbol) == 6 else symbol
        
        return symbol
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes from Yahoo Finance."""
        if not symbols:
            return {}
        
        try:
            # Normalize symbols
            normalized_symbols = []
            symbol_map = {}  # Map normalized -> original
            
            for symbol in symbols:
                # Detect asset type based on symbol
                if '/' in symbol or symbol.endswith('=X'):
                    asset_type = AssetType.FOREX
                else:
                    asset_type = AssetType.STOCKS
                
                normalized = self._normalize_symbol(symbol, asset_type)
                normalized_symbols.append(normalized)
                symbol_map[normalized] = symbol
            
            # Use thread pool to run synchronous yfinance code
            quotes_data = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._fetch_quotes_sync,
                normalized_symbols
            )
            
            quotes = {}
            for normalized_symbol, data in quotes_data.items():
                original_symbol = symbol_map[normalized_symbol]
                
                if data and 'price' in data:
                    # Determine asset type
                    asset_type = AssetType.FOREX if normalized_symbol.endswith('=X') else AssetType.STOCKS
                    
                    quote = self._create_quote(
                        symbol=original_symbol,
                        price=data['price'],
                        timestamp=data.get('timestamp', datetime.utcnow()),
                        change=data.get('change'),
                        percent_change=data.get('percent_change'),
                        volume=data.get('volume'),
                        high_24h=data.get('day_high'),
                        low_24h=data.get('day_low'),
                        open_price=data.get('open'),
                        close_price=data.get('previous_close'),
                        bid=data.get('bid'),
                        ask=data.get('ask'),
                        currency=data.get('currency'),
                        asset_type=asset_type
                    )
                    quotes[original_symbol] = quote
                else:
                    logger.warning("No data received for symbol", extra={
                        "provider": self.name,
                        "symbol": original_symbol
                    })
            
            logger.info("Retrieved quotes from Yahoo Finance", extra={
                "provider": self.name,
                "requested": len(symbols),
                "successful": len(quotes)
            })
            
            return quotes
            
        except Exception as e:
            logger.error("Failed to fetch quotes from Yahoo Finance", extra={
                "provider": self.name,
                "symbols": symbols,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch quotes: {str(e)}", self.name)
    
    def _fetch_quotes_sync(self, symbols: List[str]) -> Dict[str, Dict]:
        """Synchronous function to fetch quotes using yfinance."""
        try:
            # Create ticker objects
            tickers = yf.Tickers(' '.join(symbols))
            
            quotes_data = {}
            
            for symbol in symbols:
                try:
                    ticker = tickers.tickers[symbol]
                    info = ticker.info
                    
                    # Get current price
                    current_price = (
                        info.get('currentPrice') or 
                        info.get('regularMarketPrice') or 
                        info.get('price') or
                        info.get('bid')
                    )
                    
                    if not current_price:
                        logger.warning("No price data available", extra={
                            "symbol": symbol,
                            "provider": "yfinance"
                        })
                        continue
                    
                    # Calculate changes
                    previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                    change = None
                    percent_change = None
                    
                    if previous_close and previous_close > 0:
                        change = current_price - previous_close
                        percent_change = (change / previous_close) * 100
                    
                    quotes_data[symbol] = {
                        'price': float(current_price),
                        'change': float(change) if change is not None else None,
                        'percent_change': float(percent_change) if percent_change is not None else None,
                        'volume': info.get('volume') or info.get('regularMarketVolume'),
                        'day_high': info.get('dayHigh') or info.get('regularMarketDayHigh'),
                        'day_low': info.get('dayLow') or info.get('regularMarketDayLow'),
                        'open': info.get('open') or info.get('regularMarketOpen'),
                        'previous_close': previous_close,
                        'bid': info.get('bid'),
                        'ask': info.get('ask'),
                        'currency': info.get('currency'),
                        'timestamp': datetime.utcnow()
                    }
                    
                except Exception as e:
                    logger.warning("Failed to fetch data for symbol", extra={
                        "symbol": symbol,
                        "error": str(e),
                        "provider": "yfinance"
                    })
                    continue
            
            return quotes_data
            
        except Exception as e:
            logger.error("Error in synchronous fetch", extra={
                "error": str(e),
                "provider": "yfinance"
            })
            raise
    
    async def get_asset_list(self, asset_type: AssetType) -> List[Asset]:
        """Get list of available assets from Yahoo Finance."""
        if not self.supports_asset_type(asset_type):
            return []
        
        try:
            if asset_type == AssetType.STOCKS:
                return await self._get_stock_list()
            elif asset_type == AssetType.FOREX:
                return await self._get_forex_list()
            else:
                return []
                
        except Exception as e:
            logger.error("Failed to fetch asset list from Yahoo Finance", extra={
                "provider": self.name,
                "asset_type": asset_type.value,
                "error": str(e)
            })
            raise ProviderError(f"Failed to fetch asset list: {str(e)}", self.name)
    
    async def _get_stock_list(self) -> List[Asset]:
        """Get list of popular stocks."""
        # Yahoo Finance doesn't provide a direct API for all stocks
        # Using a curated list of popular stocks
        popular_stocks = [
            ("AAPL", "Apple Inc."),
            ("GOOGL", "Alphabet Inc."),
            ("MSFT", "Microsoft Corporation"),
            ("AMZN", "Amazon.com Inc."),
            ("TSLA", "Tesla Inc."),
            ("META", "Meta Platforms Inc."),
            ("NVDA", "NVIDIA Corporation"),
            ("NFLX", "Netflix Inc."),
            ("DIS", "The Walt Disney Company"),
            ("BABA", "Alibaba Group Holding Limited"),
            ("V", "Visa Inc."),
            ("JNJ", "Johnson & Johnson"),
            ("WMT", "Walmart Inc."),
            ("JPM", "JPMorgan Chase & Co."),
            ("MA", "Mastercard Incorporated"),
            ("PG", "The Procter & Gamble Company"),
            ("UNH", "UnitedHealth Group Incorporated"),
            ("HD", "The Home Depot Inc."),
            ("BAC", "Bank of America Corporation"),
            ("ADBE", "Adobe Inc.")
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
        
        logger.info("Retrieved stock list from Yahoo Finance", extra={
            "provider": self.name,
            "count": len(assets)
        })
        
        return assets
    
    async def _get_forex_list(self) -> List[Asset]:
        """Get list of major forex pairs."""
        major_pairs = [
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
            ("CHF/JPY", "Swiss Franc / Japanese Yen"),
            ("AUD/JPY", "Australian Dollar / Japanese Yen"),
            ("CAD/JPY", "Canadian Dollar / Japanese Yen"),
            ("NZD/JPY", "New Zealand Dollar / Japanese Yen"),
            ("EUR/CHF", "Euro / Swiss Franc"),
            ("GBP/CHF", "British Pound / Swiss Franc"),
            ("AUD/CHF", "Australian Dollar / Swiss Franc"),
            ("CAD/CHF", "Canadian Dollar / Swiss Franc"),
            ("EUR/AUD", "Euro / Australian Dollar"),
            ("GBP/AUD", "British Pound / Australian Dollar")
        ]
        
        assets = []
        for symbol, name in major_pairs:
            asset = self._create_asset(
                symbol=symbol,
                name=name,
                asset_type=AssetType.FOREX,
                exchange="Forex",
                currency="Various",
                is_active=True
            )
            assets.append(asset)
        
        logger.info("Retrieved forex list from Yahoo Finance", extra={
            "provider": self.name,
            "count": len(assets)
        })
        
        return assets
    
    async def get_company_news(self, symbol: str) -> List[NewsArticle]:
        """Get company-specific news from Yahoo Finance."""
        if not symbol or not symbol.strip():
            return []
        
        try:
            # Use thread pool to run synchronous yfinance code
            news_data = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._fetch_news_sync,
                symbol.upper()
            )
            
            if not news_data:
                logger.info("No company news data received from yfinance", extra={
                    "provider": self.name,
                    "symbol": symbol
                })
                return []
            
            articles = []
            for item in news_data[:20]:  # Limit to 20 articles
                try:
                    article = self._create_news_article_from_yfinance(item, symbol)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning("Failed to process yfinance news article", extra={
                        "provider": self.name,
                        "symbol": symbol,
                        "error": str(e),
                        "article_data": item
                    })
                    continue
            
            logger.info("Retrieved company news from yfinance", extra={
                "provider": self.name,
                "symbol": symbol,
                "count": len(articles)
            })
            
            return articles
            
        except Exception as e:
            logger.error("Failed to fetch company news from yfinance", extra={
                "provider": self.name,
                "symbol": symbol,
                "error": str(e)
            })
            # Don't raise ProviderError - just return empty list for graceful fallback
            return []
    
    def _fetch_news_sync(self, symbol: str) -> List[Dict]:
        """Synchronous function to fetch news using yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                logger.info("No news available for symbol", extra={
                    "symbol": symbol,
                    "provider": "yfinance"
                })
                return []
            
            return news
            
        except Exception as e:
            logger.warning("Error fetching news for symbol", extra={
                "symbol": symbol,
                "error": str(e),
                "provider": "yfinance"
            })
            return []
    
    def _create_news_article_from_yfinance(self, item: Dict, symbol: str) -> Optional[NewsArticle]:
        """Create NewsArticle from yfinance news data."""
        try:
            # yfinance news structure can vary, handle different possible field names
            title = None
            url = None
            timestamp = None
            summary = None
            source = None
            
            # Try different possible field names for title
            for title_field in ['title', 'headline', 'summary']:
                if title_field in item and item[title_field]:
                    title = item[title_field].strip()
                    break
            
            # Try different possible field names for URL
            for url_field in ['link', 'url', 'guid']:
                if url_field in item and item[url_field]:
                    url = item[url_field].strip()
                    break
            
            # Try different possible field names for timestamp
            for time_field in ['providerPublishTime', 'pubDate', 'published', 'timestamp']:
                if time_field in item and item[time_field]:
                    try:
                        if isinstance(item[time_field], (int, float)):
                            # Unix timestamp
                            timestamp = datetime.utcfromtimestamp(item[time_field])
                        elif isinstance(item[time_field], str):
                            # Try to parse as ISO format or other common formats
                            try:
                                from dateutil import parser
                                timestamp = parser.parse(item[time_field]).replace(tzinfo=None)
                            except ImportError:
                                # Fallback if dateutil is not available
                                timestamp = datetime.utcnow()
                        break
                    except Exception as e:
                        logger.debug("Failed to parse timestamp", extra={
                            "time_field": time_field,
                            "value": item[time_field],
                            "error": str(e)
                        })
                        continue
            
            # If no timestamp found, use current time
            if not timestamp:
                timestamp = datetime.utcnow()
            
            # Try to extract summary/description
            for summary_field in ['summary', 'description', 'content']:
                if summary_field in item and item[summary_field]:
                    summary = item[summary_field].strip()
                    break
            
            # Try to extract source
            for source_field in ['publisher', 'source', 'author']:
                if source_field in item and item[source_field]:
                    source = item[source_field].strip()
                    break
            
            # Default source if not found
            if not source:
                source = "Yahoo Finance"
            
            # Validate required fields
            if not title or not url:
                logger.debug("Missing required fields in yfinance news item", extra={
                    "provider": self.name,
                    "symbol": symbol,
                    "title": title,
                    "url": url,
                    "item_keys": list(item.keys())
                })
                return None
            
            return NewsArticle(
                title=title,
                summary=summary,
                url=url,
                source=source,
                published_at=timestamp,
                symbols=[symbol.upper()],
                category="company",
                sentiment=None
            )
            
        except Exception as e:
            logger.warning("Error creating news article from yfinance data", extra={
                "provider": self.name,
                "symbol": symbol,
                "error": str(e),
                "item": item
            })
            return None
    
    async def disconnect(self) -> None:
        """Close connections and clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        await super().disconnect()