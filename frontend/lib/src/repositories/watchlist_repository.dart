import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/watchlist.dart';
import '../services/local_db_service.dart';
import '../services/api_service.dart';
import '../services/device_service.dart';
import 'portfolio_repository.dart' show DataMode;

final watchlistRepositoryProvider = Provider<WatchlistRepository>((ref) {
  final localDb = ref.watch(localDbServiceProvider);
  final apiService = ref.watch(apiServiceProvider);
  final deviceService = ref.watch(deviceServiceProvider);
  return WatchlistRepository(localDb, apiService, deviceService);
});

class WatchlistRepository {
  final LocalDbService _localDb;
  // ignore: unused_field
  final ApiService _apiService;
  final DeviceService _deviceService;

  DataMode _currentMode = DataMode.local;

  WatchlistRepository(this._localDb, this._apiService, this._deviceService);

  /// Switch to remote mode (called after successful login/sync)
  void switchToRemoteMode() {
    _currentMode = DataMode.remote;
  }

  /// Switch back to local mode
  void switchToLocalMode() {
    _currentMode = DataMode.local;
  }

  /// Get current data mode
  DataMode get currentMode => _currentMode;

  /// Get user's watchlist
  Future<List<WatchlistItem>> getWatchlist() async {
    if (_currentMode == DataMode.local) {
      return _getWatchlistLocal();
    } else {
      return _getWatchlistRemote();
    }
  }

  /// Add stock to watchlist
  Future<void> addToWatchlist({
    required String symbol,
    required String name,
    double currentPrice = 0.0,
    double dailyChange = 0.0,
    double dailyChangePercentage = 0.0,
  }) async {
    final userId = await _deviceService.getUserId();

    // Check if already in watchlist
    if (await isInWatchlist(symbol)) {
      throw Exception('Stock is already in watchlist');
    }

    final item = WatchlistItem(
      symbol: symbol,
      name: name,
      addedAt: DateTime.now(),
      currentPrice: currentPrice,
      dailyChange: dailyChange,
      dailyChangePercentage: dailyChangePercentage,
    );

    if (_currentMode == DataMode.local) {
      await _localDb.addToWatchlist(userId, item);
    } else {
      await _addToWatchlistRemote(item);
    }
  }

  /// Remove stock from watchlist
  Future<void> removeFromWatchlist(String symbol) async {
    final userId = await _deviceService.getUserId();

    if (_currentMode == DataMode.local) {
      await _localDb.removeFromWatchlist(userId, symbol);
    } else {
      await _removeFromWatchlistRemote(symbol);
    }
  }

  /// Check if stock is in watchlist
  Future<bool> isInWatchlist(String symbol) async {
    final userId = await _deviceService.getUserId();

    if (_currentMode == DataMode.local) {
      return await _localDb.isInWatchlist(userId, symbol);
    } else {
      return await _isInWatchlistRemote(symbol);
    }
  }

  /// Update watchlist item with current prices
  Future<void> updatePrices(Map<String, Map<String, double>> priceData) async {
    final watchlist = await getWatchlist();
    final userId = await _deviceService.getUserId();

    for (final item in watchlist) {
      final stockData = priceData[item.symbol];
      if (stockData != null) {
        final updatedItem = item.copyWith(
          currentPrice: stockData['price'] ?? item.currentPrice,
          dailyChange: stockData['change'] ?? item.dailyChange,
          dailyChangePercentage:
              stockData['changePercent'] ?? item.dailyChangePercentage,
        );

        if (_currentMode == DataMode.local) {
          await _localDb.addToWatchlist(userId, updatedItem);
        } else {
          // TODO: Update remote watchlist prices
          await _localDb.addToWatchlist(userId, updatedItem);
        }
      }
    }
  }

  /// Search for stocks to add to watchlist
  Future<List<Map<String, dynamic>>> searchStocks(String query) async {
    // TODO: Implement stock search via API
    // For now, return mock data
    if (query.isEmpty) return [];

    final mockResults = [
      {
        'symbol': 'AAPL',
        'name': 'Apple Inc.',
        'price': 175.43,
        'change': 2.15,
        'changePercent': 1.24,
      },
      {
        'symbol': 'GOOGL',
        'name': 'Alphabet Inc.',
        'price': 142.56,
        'change': -1.23,
        'changePercent': -0.85,
      },
      {
        'symbol': 'MSFT',
        'name': 'Microsoft Corporation',
        'price': 378.85,
        'change': 5.42,
        'changePercent': 1.45,
      },
      {
        'symbol': 'TSLA',
        'name': 'Tesla, Inc.',
        'price': 248.42,
        'change': -3.21,
        'changePercent': -1.27,
      },
      {
        'symbol': 'AMZN',
        'name': 'Amazon.com, Inc.',
        'price': 155.89,
        'change': 1.87,
        'changePercent': 1.21,
      },
    ];

    return mockResults
        .where((stock) =>
            (stock['symbol'] as String)
                .toLowerCase()
                .contains(query.toLowerCase()) ||
            (stock['name'] as String)
                .toLowerCase()
                .contains(query.toLowerCase()))
        .take(10)
        .toList();
  }

  // Private local methods
  Future<List<WatchlistItem>> _getWatchlistLocal() async {
    final userId = await _deviceService.getUserId();
    return await _localDb.getWatchlist(userId);
  }

  // Private remote methods (TODO: Implement based on API)
  Future<List<WatchlistItem>> _getWatchlistRemote() async {
    try {
      // TODO: Implement API call to get watchlist
      // For now, fallback to local
      return await _getWatchlistLocal();
    } catch (e) {
      return await _getWatchlistLocal();
    }
  }

  Future<void> _addToWatchlistRemote(WatchlistItem item) async {
    try {
      // TODO: Implement API call to add to watchlist
      // For now, also save locally as backup
      final userId = await _deviceService.getUserId();
      await _localDb.addToWatchlist(userId, item);
    } catch (e) {
      final userId = await _deviceService.getUserId();
      await _localDb.addToWatchlist(userId, item);
    }
  }

  Future<void> _removeFromWatchlistRemote(String symbol) async {
    try {
      // TODO: Implement API call to remove from watchlist
      // For now, also remove locally
      final userId = await _deviceService.getUserId();
      await _localDb.removeFromWatchlist(userId, symbol);
    } catch (e) {
      final userId = await _deviceService.getUserId();
      await _localDb.removeFromWatchlist(userId, symbol);
    }
  }

  Future<bool> _isInWatchlistRemote(String symbol) async {
    try {
      // TODO: Implement API call to check watchlist
      // For now, fallback to local
      final userId = await _deviceService.getUserId();
      return await _localDb.isInWatchlist(userId, symbol);
    } catch (e) {
      final userId = await _deviceService.getUserId();
      return await _localDb.isInWatchlist(userId, symbol);
    }
  }
}

// Import DataMode from portfolio_repository for consistency
// (DataMode is already defined in portfolio_repository.dart)
