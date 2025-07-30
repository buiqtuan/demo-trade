# Trading Simulator - Local-First Architecture

A comprehensive educational trading simulator built with Flutter and FastAPI, featuring a **local-first architecture** with optional cloud sync. Start trading immediately without creating an account, then optionally sync your data to the cloud for backup and multi-device access.

## 🚀 Features

### 🏠 Local-First Experience
- **Instant Start**: Begin trading immediately without signing up
- **Offline Capability**: Full functionality without internet connection
- **Privacy-First**: Your data stays on your device by default
- **Anonymous Users**: Persistent anonymous user IDs for session continuity

### 📱 Yahoo Finance-Inspired UI
- **Markets Tab**: Real-time market indices and financial news
- **Watchlist Tab**: Track your favorite stocks with search functionality
- **Portfolio Tab**: Comprehensive portfolio management and trading history
- **Profile Tab**: User settings and optional cloud sync controls

### ☁️ Optional Cloud Sync
- **Sign In When Ready**: Optional Google Sign-In for cloud backup
- **Seamless Migration**: One-click sync of local data to the cloud
- **Multi-Device Access**: Access your portfolio from any device after sync
- **Data Portability**: Easy export and import of trading data

### 💼 Trading Features
- **Virtual Trading**: Buy and sell stocks with $100,000 virtual money
- **Real-time Prices**: Live stock prices and market updates
- **Portfolio Analytics**: Track performance, P/L, and trading statistics
- **Transaction History**: Complete record of all trades
- **Watchlist Management**: Monitor stocks before trading

### 🔧 Technical Features
- **Local Database**: Hive-based local storage for fast access
- **Dual-Mode Repositories**: Seamlessly switch between local and remote data
- **Real-time Updates**: WebSocket connections for live market data
- **Responsive Design**: Beautiful UI optimized for mobile and web

## 🏗️ Architecture

### Local-First Design Principles

This application follows a **local-first architecture** where user data is stored locally by default, with optional cloud synchronization. This approach provides:

- **Immediate Availability**: No network dependency for core functionality
- **User Privacy**: Data stays on device unless explicitly synced
- **Offline Resilience**: Full functionality without internet
- **Performance**: Instant responses from local database

### Frontend (Flutter)

#### Local Data Layer
- **Hive Database**: Local NoSQL storage for all user data
- **Device Service**: Anonymous user ID management with SharedPreferences
- **Local DB Service**: Centralized Hive operations and TypeAdapters
- **Data Models**: Portfolio, Holdings, Transactions, Watchlist with Hive annotations

#### Dual-Mode Repositories
- **Portfolio Repository**: Manages trading data (local/remote modes)
- **Watchlist Repository**: Handles stock watchlists (local/remote modes)
- **Sync Repository**: Coordinates data migration between local and cloud
- **Mode Switching**: Seamless transition between local and remote data sources

#### UI Architecture
- **Markets View**: Real-time market indices and financial news
- **Watchlist View**: Stock search, add/remove functionality
- **Portfolio View**: Trading interface, holdings, and transaction history
- **Profile View**: User settings, sync controls, and account management

#### State Management & Services
- **Riverpod**: Reactive state management with providers
- **Device Service**: Anonymous user identification and device settings
- **API Service**: HTTP client for remote API communication
- **WebSocket Service**: Real-time market data streaming

### Backend (FastAPI)

#### Core API
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Firebase Admin SDK for token verification
- **Market Data**: Finnhub API integration for real-time prices
- **WebSockets**: Real-time price broadcasting to connected clients

#### Sync Infrastructure
- **Sync Router**: `/sync/migrate` endpoint for data migration
- **Idempotent Operations**: Safe retry mechanisms for sync failures
- **Data Validation**: Pydantic schemas for local data payload validation
- **Conflict Resolution**: Server-side logic for handling data conflicts

#### Data Migration Flow
1. User signs in with Google after using app locally
2. Frontend packages all local data into migration payload
3. Backend validates and migrates data to user's cloud account
4. Repositories switch to remote mode for future operations
5. Local data can be optionally cleared or kept as backup

## 🛠️ Tech Stack

### Frontend Dependencies

#### Core Flutter & State Management
```yaml
dependencies:
  flutter_riverpod: ^2.4.9      # Reactive state management
  riverpod_annotation: ^2.3.3   # Code generation for providers
```

#### Local-First Architecture
```yaml
  # Local Database
  hive: ^2.2.3                  # NoSQL local database
  hive_flutter: ^1.1.0          # Flutter integration for Hive
  path_provider: ^2.1.1         # File system path access
  
  # Device Management
  shared_preferences: ^2.2.2    # Persistent key-value storage
  uuid: ^4.2.1                  # Anonymous user ID generation
```

#### Optional Cloud Sync
```yaml
  # Firebase (for optional sync)
  firebase_core: ^2.32.0        # Firebase SDK core
  firebase_auth: ^4.15.3        # Authentication service
  google_sign_in: ^6.1.6        # Google Sign-In integration
```

#### Network & Real-time Data
```yaml
  # API Communication
  http: ^1.1.2                  # HTTP client for REST APIs
  web_socket_channel: ^2.4.0    # WebSocket for real-time updates
```

#### UI & Visualization
```yaml
  # User Interface
  cupertino_icons: ^1.0.2       # iOS-style icons
  flutter_svg: ^2.0.9           # SVG support
  fl_chart: ^0.66.0             # Financial charts and graphs
  intl: ^0.19.0                 # Date/number formatting
```

#### Development Tools
```yaml
dev_dependencies:
  # Code Generation
  hive_generator: ^2.0.1        # Generates TypeAdapters for Hive
  build_runner: ^2.4.7          # Code generation runner
  riverpod_generator: ^2.3.9    # Provider code generation
```

### Backend Dependencies
```txt
fastapi==0.104.1              # Modern Python web framework
sqlalchemy==2.0.23            # Database ORM
postgresql-adapter             # PostgreSQL driver
firebase-admin==6.2.0         # Firebase authentication
finnhub-python==2.4.18        # Market data API
websockets==11.0.3            # Real-time communication
pydantic==2.5.0               # Data validation
uvicorn==0.24.0               # ASGI server
python-dotenv==1.0.0          # Environment variables
```

## 🚀 Getting Started

### Prerequisites
- Flutter SDK (3.1.0 or higher)
- Python 3.8+
- PostgreSQL database (for cloud sync features)
- Firebase project setup (for optional cloud sync)
- Finnhub API key (for real-time market data)

### Local-First Setup (Start Here!)

The app works completely offline out of the box. For the basic local experience:

1. **Clone and navigate to frontend directory**:
```bash
git clone <repository-url>
cd frontend
```

2. **Install dependencies**:
```bash
flutter pub get
```

3. **Generate required code**:
```bash
flutter packages pub run build_runner build
```

4. **Run the app locally**:
```bash
flutter run
```

That's it! The app will:
- Create an anonymous user ID automatically
- Initialize a local Hive database
- Provide $100,000 virtual cash to start trading
- Work completely offline with mock market data

### Cloud Sync Setup (Optional)

To enable cloud sync and real-time market data:

#### Backend Setup

1. **Navigate to backend directory**:
```bash
cd backend
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
Create a `.env` file with:
```env
DATABASE_URL=postgresql://username:password@localhost/tradingdb
FIREBASE_PROJECT_ID=your-firebase-project-id
FINNHUB_API_KEY=your-finnhub-api-key
```

4. **Run the server**:
```bash
python main.py
```

The server will be available at `http://localhost:8000` with:
- API documentation at `http://localhost:8000/docs`
- Sync endpoint at `http://localhost:8000/sync/migrate`

#### Firebase Setup

1. **Create a Firebase project** at [Firebase Console](https://console.firebase.google.com)

2. **Enable Authentication** with Google Sign-In provider

3. **Add your platform configurations**:
   - Add `google-services.json` for Android in `android/app/`
   - Add `GoogleService-Info.plist` for iOS in `ios/Runner/`

4. **Update Firebase configuration**:
```bash
cd frontend
dart pub global activate flutterfire_cli
flutterfire configure
```

5. **Update API endpoint** in the app:
Edit `frontend/lib/src/features/sync/sync_repository.dart`:
```dart
static const String _baseUrl = 'http://your-backend-url';
```

### User Journey

#### First-Time User Experience
1. **Launch App**: Instant access without sign-up
2. **Anonymous ID**: Auto-generated persistent user ID
3. **Local Portfolio**: $100,000 virtual cash ready to trade
4. **Offline Trading**: Full functionality without internet
5. **Data Persistence**: All data saved locally via Hive

#### Optional Cloud Sync Journey
1. **Ready to Sync**: Tap "Sign In to Sync & Backup" in Profile tab
2. **Google Sign-In**: Authenticate with Firebase
3. **Data Migration**: One-click sync of local data to cloud
4. **Multi-Device**: Access portfolio from any device
5. **Real-Time Data**: Live market prices and updates

## 📡 API Endpoints

### Local-First Architecture Endpoints

#### Sync Management (Authentication Required)
All sync endpoints require Firebase authentication token:
```
Authorization: Bearer <firebase-id-token>
```

- `POST /sync/migrate` - Migrate local data to cloud account
- `GET /sync/status` - Get current user's cloud data status

#### Trading APIs (Authentication Required)
- `GET /api/portfolios/{user_id}` - Get user's portfolio
- `POST /api/trades/execute` - Execute a trade
- `GET /api/stocks/{symbol}/price` - Get current stock price
- `GET /api/stocks/{symbol}/data` - Get historical price data

#### Real-time Data (Authentication Required)
- `WebSocket /{user_id}/ws` - Real-time price updates and subscriptions

#### Health & Status
- `GET /health` - Server health status
- `GET /` - API information and available endpoints

### Sync Migration Payload

The `/sync/migrate` endpoint accepts local data in this format:

```json
{
  "anonymous_user_id": "abc123-def456-ghi789",
  "firebase_user_id": "firebase-uid-here",
  "sync_timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "portfolio": {
      "user_id": "abc123-def456-ghi789",
      "cash_balance": 95000.00,
      "initial_balance": 100000.00
    },
    "holdings": [
      {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "quantity": 10.0,
        "average_cost_basis": 175.50,
        "current_price": 180.25
      }
    ],
    "transactions": [
      {
        "id": "txn-uuid-123",
        "user_id": "abc123-def456-ghi789",
        "symbol": "AAPL",
        "type": "buy",
        "quantity": 10.0,
        "price": 175.50,
        "timestamp": "2024-01-15T09:15:00Z",
        "total_value": 1755.00
      }
    ],
    "watchlist": [
      {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "added_at": "2024-01-15T08:00:00Z",
        "current_price": 142.50,
        "daily_change": -1.25,
        "daily_change_percentage": -0.87
      }
    ]
  }
}
```

## 🔧 Development

### Local Development Workflow

#### Frontend Development
```bash
# Install dependencies
cd frontend
flutter pub get

# Generate code (Hive adapters, Riverpod providers)
flutter packages pub run build_runner build

# Watch for changes during development
flutter packages pub run build_runner watch

# Run app with hot reload
flutter run

# Run tests
flutter test
```

#### Backend Development
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run server with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest

# Check API documentation
# Visit http://localhost:8000/docs
```

### Code Generation

#### Hive TypeAdapters
The app uses code generation for Hive TypeAdapters. After modifying model classes:

```bash
flutter packages pub run build_runner build --delete-conflicting-outputs
```

#### Riverpod Providers
Provider code generation for type-safe state management:

```bash
flutter packages pub run build_runner build
```

### Local Database Management

#### Hive Boxes
The app creates these local database boxes:
- `portfolio` - User portfolio data
- `holdings` - Stock holdings
- `transactions` - Trading history
- `watchlist` - Watched stocks
- `market_indices` - Cached market data

#### Clearing Local Data
For development/testing, clear local data:
```dart
// In device service or local DB service
await LocalDbService.clearAllData();
await DeviceService.clearDeviceData();
```

### Architecture Decisions

#### Why Local-First?
1. **Instant Gratification**: Users can start trading immediately
2. **Privacy-First**: No data collection without explicit consent
3. **Offline Resilience**: Works without internet connection
4. **Performance**: Local database queries are instantaneous
5. **User Control**: Users decide when/if to sync to cloud

#### Data Flow
```
Device Storage (Hive) ←→ Local Repositories ←→ UI
                              ↓ (optional)
                        Sync Repository
                              ↓
                        Cloud API ←→ PostgreSQL
```

## 🔒 Data Privacy & Security

### Local-First Privacy Benefits
- **No Automatic Data Collection**: Data stays on device by default
- **Anonymous Usage**: No personal information required to use the app
- **Opt-in Cloud Sync**: Users explicitly choose when to sync data
- **Data Portability**: Users can export their data at any time
- **Right to Deletion**: Local data can be cleared entirely

### Security Measures
- **Firebase Authentication**: Secure OAuth flow for cloud sync
- **API Authentication**: JWT tokens for backend communication
- **Local Encryption**: Hive database provides secure local storage
- **No Sensitive Data**: Only trading simulation data, no real financial info

## 🐛 Troubleshooting

### Common Issues

#### Local Database Issues
```bash
# Clear Hive data if corrupted
rm -rf build/
flutter clean
flutter pub get
flutter packages pub run build_runner build
```

#### Sync Issues
- Check internet connection
- Verify Firebase configuration
- Ensure backend server is running
- Check API endpoint URLs

#### Performance Issues
- Local database operations should be instant
- If slow, check for large transaction histories
- Consider implementing data pagination

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

We welcome contributions! This local-first architecture provides many opportunities for enhancement:

### Priority Areas
1. **Enhanced Offline Features**: More sophisticated local data management
2. **Conflict Resolution**: Better handling of sync conflicts
3. **Data Export/Import**: CSV/JSON export capabilities
4. **Performance Optimization**: Large dataset handling
5. **UI/UX Improvements**: Enhanced Yahoo Finance-style interface

### Development Process
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Test both local and sync modes thoroughly
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Architecture Guidelines
- Maintain local-first principles
- Ensure all features work offline
- Add cloud sync as enhancement, not requirement
- Follow existing dual-mode repository patterns
- Write tests for both local and remote data flows

---

**Start Trading Instantly! 📈💰**

Built with ❤️ using Flutter, FastAPI, and Local-First Architecture