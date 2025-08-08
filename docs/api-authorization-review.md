# Backend API Authorization Review & Updates

## Summary

This document outlines the authorization changes made to ensure proper separation between public market data APIs and private user-specific APIs.

## Authorization Structure

### 🌐 **PUBLIC APIs** (No Authentication Required)

These endpoints provide general market information and should be accessible to all users:

#### Market Data & News
- `GET /api/news/general` - General market news
- `GET /api/news/{symbol}` - Company-specific news
- `GET /api/stocks/{symbol}/price` - Current stock price
- `GET /api/stocks/{symbol}/data` - Historical stock data
- `GET /api/stocks/{symbol}/quote` - Detailed quote information
- `GET /api/stocks/{symbol}/info` - Company information
- `GET /api/stocks/search` - Search stocks by symbol/name
- `GET /api/stocks/trending` - Trending/popular stocks
- `GET /api/market/status` - Market status and trading hours

#### Public Leaderboard
- `GET /api/leaderboard` - Public leaderboard (no user rank)

#### Authentication
- `POST /api/auth/verify-token` - Verify Firebase token
- `GET /` - Root endpoint
- `GET /health` - Health check

### 🔒 **PRIVATE APIs** (Authentication Required)

These endpoints access or modify user-specific data:

#### User Management
- `POST /api/auth/register` - Register new user
- `GET /api/auth/profile` - Get user profile
- `PUT /api/auth/profile` - Update user profile
- `DELETE /api/auth/account` - Delete user account

#### Portfolio & Trading
- `GET /api/portfolios/{user_id}` - User's portfolio
- `GET /api/portfolios/{user_id}/value` - Portfolio value
- `POST /api/execute` - Execute trades
- `GET /api/history` - Trading history
- `GET /api/transaction/{transaction_id}` - Transaction details
- `GET /api/validate` - Validate trade

#### User Stats & Rankings
- `GET /api/users/{user_id}/stats` - User statistics
- `GET /api/users/{user_id}/rank` - User rank
- `GET /api/leaderboard/my-rank` - Leaderboard with user's rank
- `GET /api/users/{user_id}` - User profile

#### Data Synchronization
- `POST /sync/migrate` - Migrate local data
- `GET /sync/status` - Sync status

#### WebSocket
- `WS /{user_id}/ws` - Real-time data (user-specific subscriptions)

## Changes Made

### 1. News Router (`/routers/news.py`)
**BEFORE**: Required authentication for both endpoints
**AFTER**: Made both endpoints public
- Removed `current_user: FirebaseUser = Depends(get_current_user)` parameters
- Updated docstrings to indicate public access

### 2. Portfolios Router (`/routers/portfolios.py`)
**BEFORE**: Single leaderboard endpoint requiring auth
**AFTER**: Split into public and authenticated versions
- `GET /api/leaderboard` - Public (no user rank)
- `GET /api/leaderboard/my-rank` - Authenticated (includes user's rank)

### 3. Market Router (`/routers/market.py`)
**NEW**: Created comprehensive public market data API
- Stock search functionality
- Detailed quotes and company information
- Trending stocks
- Market status

### 4. Auth Router (`/routers/auth.py`)
**BEFORE**: `GET /verify-token` 
**AFTER**: `POST /verify-token` (public endpoint)
- Changed from GET to POST for better security
- Made publicly accessible for frontend token validation

### 5. Main App (`/main.py`)
**BEFORE**: Limited public endpoints
**AFTER**: Added market data router
- Included market router with `/api` prefix
- Organized routers by access level

## Security Benefits

### ✅ **Improved User Experience**
- Users can browse market data without account creation
- News and stock prices accessible to anonymous users
- Public leaderboard encourages engagement

### ✅ **Better Security Model**
- Clear separation of public vs private data
- User-specific data remains protected
- No accidental exposure of personal information

### ✅ **Scalability**
- Public endpoints can be cached more aggressively
- Reduced authentication overhead for market data
- Better suited for mobile apps with offline capabilities

## API Usage Examples

### Public Market Data (No Auth)
```bash
# Get stock price
curl "http://localhost:8000/api/stocks/AAPL/price"

# Search stocks
curl "http://localhost:8000/api/stocks/search?query=apple&limit=5"

# Get market news
curl "http://localhost:8000/api/news/general"

# View leaderboard
curl "http://localhost:8000/api/leaderboard"
```

### Private User Data (Auth Required)
```bash
# Get user portfolio
curl "http://localhost:8000/api/portfolios/user123" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"

# Execute trade
curl -X POST "http://localhost:8000/api/execute" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "quantity": 10, "action": "BUY"}'

# Get personal leaderboard rank
curl "http://localhost:8000/api/leaderboard/my-rank" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

## Migration Notes

### Frontend Updates Required
1. **Remove auth headers** from market data API calls
2. **Update leaderboard calls** to use public endpoint for general viewing
3. **Add auth headers** only for user-specific operations
4. **Use new market endpoints** for enhanced functionality

### Backward Compatibility
- All existing authenticated endpoints remain functional
- No breaking changes to request/response formats
- Additional public endpoints provide new functionality

## Testing Checklist

- [ ] Public endpoints work without auth headers
- [ ] Private endpoints require valid auth tokens  
- [ ] User can only access their own data
- [ ] Public leaderboard hides user rank
- [ ] Authenticated leaderboard shows user rank
- [ ] News endpoints work for anonymous users
- [ ] Market data endpoints provide real-time info
- [ ] WebSocket subscriptions still require user auth

## Performance Benefits

### Caching Strategy
- **Public endpoints**: Can use aggressive caching (1-5 minutes)
- **Private endpoints**: Minimal caching or user-specific cache
- **Market data**: Cached by symbol with TTL
- **News**: Cached by time periods

### Load Distribution
- Market data requests no longer hit authentication service
- Reduced database queries for public information
- Better separation of concerns between services
