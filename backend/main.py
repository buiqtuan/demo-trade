from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from typing import Dict, List
import os
from dotenv import load_dotenv

from database import get_db, engine
from models import Base
from dependencies import get_current_user
from routers import trades, portfolios, sync
import finnhub

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

# Create database tables
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

# Include routers
app.include_router(trades.router, prefix="/api", tags=["trades"])
app.include_router(portfolios.router, prefix="/api", tags=["portfolios"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])

# Finnhub client
finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

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
async def fetch_and_broadcast_prices():
    """Background task to fetch prices from Finnhub and broadcast to connected clients"""
    
    # Popular stocks to fetch prices for
    default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
    
    while True:
        try:
            if manager.active_connections:
                # Get all subscribed symbols
                all_symbols = set()
                for symbols in manager.subscribed_symbols.values():
                    all_symbols.update(symbols)
                
                # Add default symbols if no one is subscribed to anything
                if not all_symbols:
                    all_symbols = set(default_symbols)
                
                # Fetch prices from Finnhub
                prices = {}
                for symbol in all_symbols:
                    try:
                        quote = finnhub_client.quote(symbol)
                        if quote and 'c' in quote:  # 'c' is current price
                            prices[symbol] = float(quote['c'])
                    except Exception as e:
                        logger.error(f"Error fetching price for {symbol}: {e}")
                        # Use mock data if Finnhub fails
                        import random
                        prices[symbol] = round(random.uniform(50, 500), 2)
                
                # Broadcast prices to all connected clients
                if prices:
                    await manager.broadcast_prices(prices)
                    logger.info(f"Broadcasted prices for {len(prices)} symbols")
            
            # Wait 2 seconds before next update
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error in price broadcasting task: {e}")
            await asyncio.sleep(5)  # Wait longer on error

# Start background task when app starts
@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(fetch_and_broadcast_prices())

# Additional API endpoints for stock data
@app.get("/api/stocks/{symbol}/price")
async def get_current_price(symbol: str, current_user=Depends(get_current_user)):
    """Get current price for a stock symbol"""
    try:
        quote = finnhub_client.quote(symbol)
        if quote and 'c' in quote:
            return {"symbol": symbol, "price": float(quote['c'])}
        else:
            raise HTTPException(status_code=404, detail=f"Price not found for symbol {symbol}")
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        # Return mock data if Finnhub fails
        import random
        return {"symbol": symbol, "price": round(random.uniform(50, 500), 2)}

@app.get("/api/stocks/{symbol}/data")
async def get_stock_data(symbol: str, current_user=Depends(get_current_user)):
    """Get historical price data for charting"""
    try:
        # Get last 30 days of data
        import time
        from datetime import datetime, timedelta
        
        end_time = int(time.time())
        start_time = int((datetime.now() - timedelta(days=30)).timestamp())
        
        candles = finnhub_client.stock_candles(symbol, 'D', start_time, end_time)
        
        if candles and 't' in candles:
            data = []
            for i in range(len(candles['t'])):
                data.append({
                    'timestamp': candles['t'][i],
                    'open': candles['o'][i],
                    'high': candles['h'][i],
                    'low': candles['l'][i],
                    'close': candles['c'][i],
                    'volume': candles['v'][i]
                })
            return data
        else:
            # Return mock data if Finnhub fails
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
            
            return mock_data
            
    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock data")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 