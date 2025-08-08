# Market Data Aggregator Service

A production-ready, high-performance microservice for aggregating market data from multiple providers with built-in resilience, caching, and circuit breaker patterns.

## 🏗️ Architecture Overview

This service is designed as a standalone microservice that:

- **Aggregates** market data from multiple providers (Yahoo Finance, Finnhub, CoinGecko, CoinMarketCap, Alpha Vantage)
- **Caches** data in Redis for ultra-fast API responses
- **Implements** circuit breaker pattern for resilience against provider failures
- **Provides** RESTful APIs for consuming standardized market data
- **Runs** background tasks for continuous data updates

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Aggregator    │    │   Cache Layer   │
│                 │    │                 │    │                 │
│ • Yahoo Finance │────│ • Circuit       │────│ • Redis         │
│ • Finnhub       │    │   Breakers      │    │ • Fast Queries  │
│ • CoinGecko     │    │ • Fallback      │    │ • TTL Management│
│ • Alpha Vantage │    │   Logic         │    │ • Data Normalization  │
│ • CoinMarketCap │    │                 │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ↓
                       ┌─────────────────┐
                       │   FastAPI       │
                       │   REST API      │
                       │                 │
                       │ • /v1/assets    │
                       │ • /v1/quotes    │
                       │ • /health       │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- API keys for data providers (see Environment Variables section)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd market_data_aggregator
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Configure API keys in `.env`:**
   ```bash
   # Edit .env file with your API keys
   FINNHUB_API_KEY=your_actual_key_here
   COINMARKETCAP_API_KEY=your_actual_key_here
   ALPHA_VANTAGE_API_KEY=your_actual_key_here
   ```

4. **Start the services:**
   ```bash
   docker-compose up -d
   ```

5. **Verify the service is running:**
   ```bash
   curl http://localhost:8000/health
   ```

## 📚 API Documentation

### Endpoints

#### Health Check
```http
GET /health
```
Returns service health status.

#### Get Assets by Type
```http
GET /v1/assets/{asset_type}
```

**Parameters:**
- `asset_type`: `stocks`, `crypto`, or `forex`

**Example:**
```bash
curl http://localhost:8000/v1/assets/stocks
```

#### Get Real-time Quotes
```http
GET /v1/quotes?symbols=AAPL,BTC-USD,EUR/USD
```

**Parameters:**
- `symbols`: Comma-separated list of symbols

**Example:**
```bash
curl "http://localhost:8000/v1/quotes?symbols=AAPL,GOOGL,BTC-USD"
```

**Response:**
```json
{
  "quotes": [
    {
      "symbol": "AAPL",
      "price": 182.50,
      "change": 1.25,
      "percent_change": 0.69,
      "source": "yfinance",
      "timestamp": "2024-01-15T14:30:00Z"
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_HOST` | Redis hostname | `redis` | Yes |
| `REDIS_PORT` | Redis port | `6379` | Yes |
| `FINNHUB_API_KEY` | Finnhub API key | - | Yes |
| `COINMARKETCAP_API_KEY` | CoinMarketCap API key | - | Yes |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | - | Yes |
| `CIRCUIT_BREAKER_TIMEOUT` | Circuit breaker timeout (seconds) | `300` | No |
| `PRICE_FETCH_INTERVAL` | Price update interval (seconds) | `5` | No |
| `ASSET_LIST_UPDATE_INTERVAL` | Asset list update interval (seconds) | `86400` | No |
| `ACTIVE_SYMBOLS` | Comma-separated symbols to track | See .env.example | No |

### Background Tasks

1. **Asset List Updater (Slow Loop)**
   - Frequency: Every 24 hours
   - Purpose: Updates the complete list of available symbols
   - Providers: All configured providers

2. **Price Fetcher (Fast Loop)**
   - Frequency: Every 5 seconds
   - Purpose: Fetches latest quotes for active symbols
   - Fallback: Uses circuit breaker pattern for resilience

## 🛡️ Resilience Features

### Circuit Breaker Pattern

The service implements a circuit breaker for each data provider:

- **Closed State**: Normal operation, requests go to provider
- **Open State**: Provider is failing, requests go to fallback
- **Timeout**: 5 minutes (configurable)

### Fallback Strategy

| Primary Provider | Fallback Provider | Asset Type |
|-----------------|-------------------|------------|
| Yahoo Finance | Finnhub | Stocks |
| CoinGecko | CoinMarketCap | Crypto |
| Alpha Vantage | Yahoo Finance | Forex |

### Caching Strategy

- **Quotes Cache**: 5 minutes TTL
- **Assets Cache**: 24 hours TTL
- **Redis LRU**: Automatic eviction when memory limit reached

## 🧪 Development

### Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis locally:**
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/
```

## 📊 Monitoring

### Health Endpoints

- **Application Health**: `GET /health`
- **Redis Health**: Checked via application health endpoint
- **Provider Health**: Circuit breaker status in Redis

### Logging

The service uses structured JSON logging with the following levels:
- `INFO`: Normal operations, background task execution
- `WARNING`: Circuit breaker trips, fallback usage
- `ERROR`: Provider failures, cache errors
- `DEBUG`: Detailed operation logs (development only)

### Metrics

Key metrics to monitor:
- Request latency for API endpoints
- Cache hit/miss rates
- Circuit breaker state changes
- Background task execution times
- Provider response times

## 🔒 Security

- **Non-root user**: Container runs as non-privileged user
- **Environment isolation**: Sensitive data in environment variables
- **API rate limiting**: Built-in rate limiting per provider
- **Input validation**: Pydantic models for all inputs

## 📈 Performance

- **Sub-second response times**: All API calls served from cache
- **Horizontal scaling**: Stateless design allows multiple instances
- **Memory efficient**: Redis LRU eviction policy
- **Connection pooling**: Shared HTTP clients for external APIs

## 🐛 Troubleshooting

### Common Issues

1. **Service won't start:**
   - Check Redis connectivity
   - Verify API keys in `.env`
   - Check Docker logs: `docker-compose logs app`

2. **No data in cache:**
   - Verify background tasks are running
   - Check provider API key validity
   - Monitor circuit breaker status

3. **Slow API responses:**
   - Check Redis memory usage
   - Monitor cache hit rates
   - Verify network connectivity to Redis

### Debug Commands

```bash
# View application logs
docker-compose logs -f app

# Check Redis data
docker-compose exec redis redis-cli keys "*"

# Test provider connectivity
curl -H "Content-Type: application/json" localhost:8000/health
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section above
- Review the application logs for error details