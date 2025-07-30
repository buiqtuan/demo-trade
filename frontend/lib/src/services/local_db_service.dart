import 'package:hive_flutter/hive_flutter.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/portfolio.dart';
import '../models/transaction.dart';
import '../models/watchlist.dart';
import '../models/market_index.dart';

final localDbServiceProvider = Provider<LocalDbService>((ref) {
  return LocalDbService();
});

/// Service responsible for all local database operations using Hive
class LocalDbService {
  // Box names
  static const String _portfolioBoxName = 'portfolio';
  static const String _holdingsBoxName = 'holdings';
  static const String _transactionsBoxName = 'transactions';
  static const String _watchlistBoxName = 'watchlist';
  static const String _marketIndicesBoxName = 'market_indices';

  // Lazy boxes for better performance
  Box<Portfolio>? _portfolioBox;
  Box<Holding>? _holdingsBox;
  Box<Transaction>? _transactionsBox;
  Box<WatchlistItem>? _watchlistBox;
  Box<MarketIndex>? _marketIndicesBox;

  /// Initialize Hive and register adapters
  /// This should be called before any other Hive operations
  static Future<void> initialize() async {
    await Hive.initFlutter();

    // Register type adapters
    if (!Hive.isAdapterRegistered(0)) {
      Hive.registerAdapter(PortfolioAdapter());
    }
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(HoldingAdapter());
    }
    if (!Hive.isAdapterRegistered(2)) {
      Hive.registerAdapter(TransactionAdapter());
    }
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(TransactionTypeAdapter());
    }
    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(WatchlistItemAdapter());
    }
    if (!Hive.isAdapterRegistered(5)) {
      Hive.registerAdapter(MarketIndexAdapter());
    }
  }

  /// Open all required boxes
  Future<void> openBoxes() async {
    _portfolioBox = await Hive.openBox<Portfolio>(_portfolioBoxName);
    _holdingsBox = await Hive.openBox<Holding>(_holdingsBoxName);
    _transactionsBox = await Hive.openBox<Transaction>(_transactionsBoxName);
    _watchlistBox = await Hive.openBox<WatchlistItem>(_watchlistBoxName);
    _marketIndicesBox = await Hive.openBox<MarketIndex>(_marketIndicesBoxName);
  }

  /// Close all boxes
  Future<void> closeBoxes() async {
    await _portfolioBox?.close();
    await _holdingsBox?.close();
    await _transactionsBox?.close();
    await _watchlistBox?.close();
    await _marketIndicesBox?.close();
  }

  /// Clear all local data
  Future<void> clearAllData() async {
    await _portfolioBox?.clear();
    await _holdingsBox?.clear();
    await _transactionsBox?.clear();
    await _watchlistBox?.clear();
    await _marketIndicesBox?.clear();
  }

  // Portfolio operations
  Future<Portfolio?> getPortfolio(String userId) async {
    return _portfolioBox?.get(userId);
  }

  Future<void> savePortfolio(Portfolio portfolio) async {
    await _portfolioBox?.put(portfolio.userId, portfolio);
  }

  Future<void> deletePortfolio(String userId) async {
    await _portfolioBox?.delete(userId);
  }

  // Holdings operations
  Future<List<Holding>> getHoldings(String userId) async {
    if (_holdingsBox == null) return [];
    return _holdingsBox!.values
        .where((holding) => holding.symbol.startsWith(userId))
        .toList();
  }

  Future<void> saveHolding(String userId, Holding holding) async {
    final key = '${userId}_${holding.symbol}';
    await _holdingsBox?.put(key, holding);
  }

  Future<void> deleteHolding(String userId, String symbol) async {
    final key = '${userId}_$symbol';
    await _holdingsBox?.delete(key);
  }

  // Transaction operations
  Future<List<Transaction>> getTransactions(String userId) async {
    if (_transactionsBox == null) return [];
    return _transactionsBox!.values
        .where((transaction) => transaction.userId == userId)
        .toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
  }

  Future<void> saveTransaction(Transaction transaction) async {
    await _transactionsBox?.put(transaction.id, transaction);
  }

  Future<void> deleteTransaction(String transactionId) async {
    await _transactionsBox?.delete(transactionId);
  }

  // Watchlist operations
  Future<List<WatchlistItem>> getWatchlist(String userId) async {
    if (_watchlistBox == null) return [];
    return _watchlistBox!.values
        .where((item) => item.symbol.startsWith(userId))
        .toList()
      ..sort((a, b) => a.addedAt.compareTo(b.addedAt));
  }

  Future<void> addToWatchlist(String userId, WatchlistItem item) async {
    final key = '${userId}_${item.symbol}';
    await _watchlistBox?.put(key, item);
  }

  Future<void> removeFromWatchlist(String userId, String symbol) async {
    final key = '${userId}_$symbol';
    await _watchlistBox?.delete(key);
  }

  Future<bool> isInWatchlist(String userId, String symbol) async {
    final key = '${userId}_$symbol';
    return _watchlistBox?.containsKey(key) ?? false;
  }

  // Market indices operations
  Future<List<MarketIndex>> getMarketIndices() async {
    if (_marketIndicesBox == null) return [];
    return _marketIndicesBox!.values.toList();
  }

  Future<void> saveMarketIndices(List<MarketIndex> indices) async {
    if (_marketIndicesBox == null) return;

    for (final index in indices) {
      await _marketIndicesBox!.put(index.symbol, index);
    }
  }

  Future<void> saveMarketIndex(MarketIndex index) async {
    await _marketIndicesBox?.put(index.symbol, index);
  }

  /// Get all data for sync purposes
  Future<Map<String, dynamic>> getAllUserData(String userId) async {
    final portfolio = await getPortfolio(userId);
    final holdings = await getHoldings(userId);
    final transactions = await getTransactions(userId);
    final watchlist = await getWatchlist(userId);

    return {
      'portfolio': portfolio?.toJson(),
      'holdings': holdings.map((h) => h.toJson()).toList(),
      'transactions': transactions.map((t) => t.toJson()).toList(),
      'watchlist': watchlist.map((w) => w.toJson()).toList(),
    };
  }

  /// Check if user has any local data
  Future<bool> hasUserData(String userId) async {
    final portfolio = await getPortfolio(userId);
    final holdings = await getHoldings(userId);
    final transactions = await getTransactions(userId);
    final watchlist = await getWatchlist(userId);

    return portfolio != null ||
        holdings.isNotEmpty ||
        transactions.isNotEmpty ||
        watchlist.isNotEmpty;
  }
}
