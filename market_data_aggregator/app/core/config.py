"""
Configuration management for Market Data Aggregator Service.
Uses pydantic-settings for environment variable management.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application metadata
    app_name: str = Field(default="Market Data Aggregator", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Redis configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Circuit breaker configuration
    circuit_breaker_timeout: int = Field(default=300, env="CIRCUIT_BREAKER_TIMEOUT")
    
    # Background task intervals (in seconds)
    asset_list_update_interval: int = Field(default=86400, env="ASSET_LIST_UPDATE_INTERVAL")  # 24 hours
    price_fetch_interval: int = Field(default=5, env="PRICE_FETCH_INTERVAL")  # 5 seconds
    
    # API Keys for data providers
    finnhub_api_key: str = Field(env="FINNHUB_API_KEY")
    coinmarketcap_api_key: str = Field(env="COINMARKETCAP_API_KEY")
    alpha_vantage_api_key: str = Field(env="ALPHA_VANTAGE_API_KEY")
    
    # CoinGecko API (free tier - no key required)
    coingecko_api_url: str = Field(default="https://api.coingecko.com/api/v3", env="COINGECKO_API_URL")
    
    # Rate limiting configuration
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_second: int = Field(default=1, env="RATE_LIMIT_REQUESTS_PER_SECOND")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Cache TTL settings (in seconds)
    quotes_cache_ttl: int = Field(default=300, env="QUOTES_CACHE_TTL")  # 5 minutes
    assets_cache_ttl: int = Field(default=86400, env="ASSETS_CACHE_TTL")  # 24 hours
    
    # Active symbols configuration
    active_symbols: str = Field(
        default="AAPL,GOOGL,MSFT,TSLA,BTC-USD,ETH-USD,EUR/USD,GBP/USD",
        env="ACTIVE_SYMBOLS"
    )
    
    @validator('active_symbols')
    def validate_active_symbols(cls, v: str) -> str:
        """Validate that active_symbols is a comma-separated string."""
        if not v or not v.strip():
            raise ValueError("active_symbols cannot be empty")
        return v.strip()
    
    @validator('log_level')
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @validator('log_format')
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = {'json', 'text'}
        if v.lower() not in valid_formats:
            raise ValueError(f"log_format must be one of: {', '.join(valid_formats)}")
        return v.lower()
    
    def get_active_symbols_list(self) -> List[str]:
        """Get active symbols as a list."""
        return [symbol.strip() for symbol in self.active_symbols.split(',') if symbol.strip()]
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Provider configuration
class ProviderConfig:
    """Configuration for data providers and their fallbacks."""
    
    # Primary providers for each asset type
    PRIMARY_PROVIDERS = {
        'stocks': 'yfinance',
        'crypto': 'coingecko',
        'forex': 'alpha_vantage'
    }
    
    # Fallback providers for each asset type
    FALLBACK_PROVIDERS = {
        'stocks': 'finnhub',
        'crypto': 'coinmarketcap',
        'forex': 'yfinance'
    }
    
    # Circuit breaker keys for Redis
    CIRCUIT_BREAKER_KEYS = {
        'yfinance': 'circuit_breaker:yfinance',
        'finnhub': 'circuit_breaker:finnhub',
        'coingecko': 'circuit_breaker:coingecko',
        'coinmarketcap': 'circuit_breaker:coinmarketcap',
        'alpha_vantage': 'circuit_breaker:alpha_vantage'
    }
    
    # Cache keys
    CACHE_KEYS = {
        'quotes': 'quotes:{symbol}',
        'assets_stocks': 'assets:stocks',
        'assets_crypto': 'assets:crypto',
        'assets_forex': 'assets:forex',
        'active_symbols': 'config:active_symbols'
    }


provider_config = ProviderConfig()