from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import asyncio
import json
import logging
from typing import Dict, List
import os
from dotenv import load_dotenv

from database import get_db, engine
from models import Base
from dependencies import get_current_user
from routers import trades, portfolios, sync, news
from services.market_data_client import market_data_client
from middleware.error_handler import global_exception_handler, validation_exception_handler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Trading Simulator API",
    description="A comprehensive trading simulator backend with real-time market data",
    version="1.0.0"
)

# CORS middleware for Flutter web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Create database tables
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

# Include routers
app.include_router(trades.router, prefix="/api", tags=["trades"])
app.include_router(portfolios.router, prefix="/api", tags=["portfolios"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(news.router, prefix="/api", tags=["news"])

# Market Data Aggregator client is imported and initialized in services/market_data_client.py

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscribed_symbols: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.subscribed_symbols[user_id] = []
        logger.info(f"User {user_id} connected to WebSocket")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.subscribed_symbols:
            del self.subscribed_symbols[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast_prices(self, prices: Dict[str, float]):
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            try:
                # Only send prices for symbols the user is subscribed to
                user_symbols = self.subscribed_symbols.get(user_id, [])
                if user_symbols:
                    filtered_prices = {
                        symbol: price for symbol, price in prices.items()
                        if symbol in user_symbols
                    }
                    if filtered_prices:
                        message = {
                            "type": "price_update",
                            "prices": filtered_prices
                        }
                        await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)

manager = ConnectionManager()

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Trading Simulator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "websocket": "/{user_id}/ws",
            "trades": "/api/execute",
            "portfolios": "/api/portfolios/{user_id}",
            "health": "/health"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}

# WebSocket endpoint for real-time data
@app.websocket("/{user_id}/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    
    # Send connection acknowledgment
    await manager.send_personal_message(
        json.dumps({"type": "connection_ack", "message": "Connected successfully"}),
        user_id
    )
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe":
                symbols = message.get("symbols", [])
                manager.subscribed_symbols[user_id] = symbols
                await manager.send_personal_message(
                    json.dumps({
                        "type": "subscription_ack",
                        "message": f"Subscribed to {len(symbols)} symbols"
                    }),
                    user_id
                )
                logger.info(f"User {user_id} subscribed to {symbols}")
                
            elif message.get("type") == "unsubscribe":
                symbols = message.get("symbols", [])
                current_symbols = manager.subscribed_symbols.get(user_id, [])
                manager.subscribed_symbols[user_id] = [
                    s for s in current_symbols if s not in symbols
                ]
                await manager.send_personal_message(
                    json.dumps({
                        "type": "unsubscription_ack",
                        "message": f"Unsubscribed from {len(symbols)} symbols"
                    }),
                    user_id
                )
                
            elif message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong"}),
                    user_id
                )
                
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)

# Background task to fetch and broadcast real-time prices
_background_task = None
_shutdown_event = asyncio.Event()

async def fetch_and_broadcast_prices():
    """Background task to fetch prices from Market Data Aggregator and broadcast to connected clients"""
    
    # Popular stocks to fetch prices for
    default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    logger.info("Starting price broadcasting background task")
    
    while not _shutdown_event.is_set():
        try:
            # Health check before fetching data
            if not await market_data_client.health_check():
                logger.warning("Market Data Aggregator health check failed, using mock data")
                consecutive_failures += 1
                
                # If too many consecutive failures, wait longer
                if consecutive_failures >= max_consecutive_failures:
                    delay = min(30, 2 ** min(consecutive_failures - max_consecutive_failures, 5))
                    logger.error(f"Too many consecutive failures ({consecutive_failures}), waiting {delay}s")
                    try:
                        await asyncio.wait_for(_shutdown_event.wait(), timeout=delay)
                        break  # Shutdown requested
                    except asyncio.TimeoutError:
                        pass
                
                # Use mock data when service is down
                if manager.active_connections:
                    all_symbols = set()
                    for symbols in manager.subscribed_symbols.values():
                        all_symbols.update(symbols)
                    
                    if not all_symbols:
                        all_symbols = set(default_symbols)
                    
                    # Generate mock prices
                    import random
                    prices = {symbol: round(random.uniform(50, 500), 2) for symbol in all_symbols}
                    
                    if prices:
                        await manager.broadcast_prices(prices)
                        logger.info(f"Broadcasted mock prices for {len(prices)} symbols")
                
                # Wait before next attempt
                delay = min(10, 2 ** min(consecutive_failures, 3))
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=delay)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue
            
            # Service is healthy, proceed with normal operation
            if manager.active_connections:
                # Get all subscribed symbols
                all_symbols = set()
                for symbols in manager.subscribed_symbols.values():
                    all_symbols.update(symbols)
                
                # Add default symbols if no one is subscribed to anything
                if not all_symbols:
                    all_symbols = set(default_symbols)
                
                try:
                    # Fetch prices from Market Data Aggregator
                    quotes_dict = await market_data_client.get_quotes(list(all_symbols))
                    
                    # Convert to simple price dict for broadcasting
                    prices = {}
                    for symbol, quote in quotes_dict.items():
                        prices[symbol] = float(quote.price)
                    
                    # Add fallback mock data for missing symbols
                    for symbol in all_symbols:
                        if symbol not in prices:
                            logger.warning(f"No price data for {symbol}, using mock price")
                            import random
                            prices[symbol] = round(random.uniform(50, 500), 2)
                    
                    # Broadcast prices to all connected clients
                    if prices:
                        await manager.broadcast_prices(prices)
                        logger.info(f"Broadcasted prices for {len(prices)} symbols")
                    
                    # Reset failure counter on success
                    consecutive_failures = 0
                    
                except Exception as e:
                    logger.error(f"Error fetching quotes from Market Data Aggregator: {e}")
                    consecutive_failures += 1
                    
                    # Use mock data as fallback
                    import random
                    prices = {symbol: round(random.uniform(50, 500), 2) for symbol in all_symbols}
                    
                    if prices:
                        await manager.broadcast_prices(prices)
                        logger.info(f"Broadcasted fallback mock prices for {len(prices)} symbols")
            
            # Wait 2 seconds before next update (or until shutdown)
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=2.0)
                break  # Shutdown requested
            except asyncio.TimeoutError:
                pass
            
        except asyncio.CancelledError:
            logger.info("Price broadcasting task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in price broadcasting task: {e}")
            consecutive_failures += 1
            
            # Exponential backoff on errors
            delay = min(30, 2 ** min(consecutive_failures, 5))
            logger.warning(f"Waiting {delay}s before retry due to error")
            
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=delay)
                break  # Shutdown requested
            except asyncio.TimeoutError:
                pass
    
    logger.info("Price broadcasting background task stopped")

# Start background task when app starts
@app.on_event("startup")
async def start_background_tasks():
    global _background_task
    _background_task = asyncio.create_task(fetch_and_broadcast_prices())
    logger.info("Background tasks started")

# Additional API endpoints for stock data
@app.get("/api/stocks/{symbol}/price")
async def get_current_price(symbol: str, current_user=Depends(get_current_user)):
    """Get current price for a stock symbol"""
    try:
        quote = await market_data_client.get_quote(symbol)
        if quote and quote.price > 0:
            return {"symbol": symbol, "price": float(quote.price), "source": quote.source}
        else:
            raise HTTPException(status_code=404, detail=f"Price not found for symbol {symbol}")
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        # Return mock data if Market Data Aggregator fails
        import random
        return {"symbol": symbol, "price": round(random.uniform(50, 500), 2), "source": "mock"}

@app.get("/api/stocks/{symbol}/data")
async def get_stock_data(symbol: str, current_user=Depends(get_current_user)):
    """Get historical price data for charting (mock data for now)"""
    try:
        # TODO: Integrate with Market Data Aggregator for historical data
        # For now, return mock data
        import random
        from datetime import datetime, timedelta
        
        mock_data = []
        base_price = random.uniform(100, 300)
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            price_change = random.uniform(-5, 5)
            base_price += price_change
            
            open_price = base_price
            high_price = base_price + random.uniform(0, 10)
            low_price = base_price - random.uniform(0, 10)
            close_price = base_price + random.uniform(-5, 5)
            
            mock_data.append({
                'timestamp': int(date.timestamp()),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': random.randint(1000000, 50000000)
            })
        
        logger.info(f"Generated mock historical data for {symbol}")
        return mock_data
            
    except Exception as e:
        logger.error(f"Error generating stock data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock data")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _background_task
    
    # Signal background tasks to stop
    _shutdown_event.set()
    logger.info("Shutdown signal sent to background tasks")
    
    # Wait for background task to finish gracefully
    if _background_task and not _background_task.done():
        try:
            await asyncio.wait_for(_background_task, timeout=10.0)
            logger.info("Background task stopped gracefully")
        except asyncio.TimeoutError:
            logger.warning("Background task did not stop gracefully, cancelling")
            _background_task.cancel()
            try:
                await _background_task
            except asyncio.CancelledError:
                pass
    
    # Close market data client
    await market_data_client.close()
    logger.info("Shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 