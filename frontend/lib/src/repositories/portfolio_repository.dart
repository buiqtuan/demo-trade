import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/portfolio.dart';
import '../models/transaction.dart';
import '../services/local_db_service.dart';
import '../services/api_service.dart';
import '../services/device_service.dart';
import 'package:uuid/uuid.dart';

final portfolioRepositoryProvider = Provider<PortfolioRepository>((ref) {
  final localDb = ref.watch(localDbServiceProvider);
  final apiService = ref.watch(apiServiceProvider);
  final deviceService = ref.watch(deviceServiceProvider);
  return PortfolioRepository(localDb, apiService, deviceService);
});

enum DataMode { local, remote }

class PortfolioRepository {
  final LocalDbService _localDb;
  final ApiService _apiService;
  final DeviceService _deviceService;

  DataMode _currentMode = DataMode.local;

  PortfolioRepository(this._localDb, this._apiService, this._deviceService);

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

  /// Get user's portfolio
  Future<Portfolio?> getPortfolio() async {
    if (_currentMode == DataMode.local) {
      return _getPortfolioLocal();
    } else {
      return _getPortfolioRemote();
    }
  }

  /// Save portfolio
  Future<void> savePortfolio(Portfolio portfolio) async {
    if (_currentMode == DataMode.local) {
      await _savePortfolioLocal(portfolio);
    } else {
      await _savePortfolioRemote(portfolio);
    }
  }

  /// Create initial portfolio for new user
  Future<Portfolio> createInitialPortfolio(
      {double initialBalance = 100000.0}) async {
    final userId = await _deviceService.getUserId();

    final portfolio = Portfolio(
      userId: userId,
      cashBalance: initialBalance,
      initialBalance: initialBalance,
      holdings: [],
    );

    await savePortfolio(portfolio);
    return portfolio;
  }

  /// Execute a trade (buy/sell)
  Future<Portfolio> executeTrade({
    required String symbol,
    required String companyName,
    required double quantity,
    required double price,
    required TransactionType type,
  }) async {
    final currentPortfolio = await getPortfolio();
    if (currentPortfolio == null) {
      throw Exception('Portfolio not found');
    }

    final totalCost = quantity * price;
    final userId = await _deviceService.getUserId();

    // Create transaction
    final transaction = Transaction(
      id: const Uuid().v4(),
      userId: userId,
      symbol: symbol,
      type: type,
      quantity: quantity,
      price: price,
      timestamp: DateTime.now(),
      totalValue: totalCost,
    );

    Portfolio updatedPortfolio;

    if (type == TransactionType.buy) {
      // Check if user has enough cash
      if (currentPortfolio.cashBalance < totalCost) {
        throw Exception('Insufficient funds');
      }

      // Update cash balance
      final newCashBalance = currentPortfolio.cashBalance - totalCost;

      // Update or add holding
      final existingHoldingIndex =
          currentPortfolio.holdings.indexWhere((h) => h.symbol == symbol);

      List<Holding> updatedHoldings;
      if (existingHoldingIndex != -1) {
        // Update existing holding
        final existingHolding = currentPortfolio.holdings[existingHoldingIndex];
        final newQuantity = existingHolding.quantity + quantity;
        final newAverageCost =
            ((existingHolding.averageCostBasis * existingHolding.quantity) +
                    (price * quantity)) /
                newQuantity;

        updatedHoldings = List.from(currentPortfolio.holdings);
        updatedHoldings[existingHoldingIndex] = existingHolding.copyWith(
          quantity: newQuantity,
          averageCostBasis: newAverageCost,
          currentPrice: price,
        );
      } else {
        // Add new holding
        updatedHoldings = [
          ...currentPortfolio.holdings,
          Holding(
            symbol: symbol,
            name: companyName,
            quantity: quantity,
            averageCostBasis: price,
            currentPrice: price,
          ),
        ];
      }

      updatedPortfolio = currentPortfolio.copyWith(
        cashBalance: newCashBalance,
        holdings: updatedHoldings,
      );
    } else {
      // Sell transaction
      final existingHoldingIndex =
          currentPortfolio.holdings.indexWhere((h) => h.symbol == symbol);

      if (existingHoldingIndex == -1) {
        throw Exception('Stock not found in portfolio');
      }

      final existingHolding = currentPortfolio.holdings[existingHoldingIndex];
      if (existingHolding.quantity < quantity) {
        throw Exception('Insufficient shares to sell');
      }

      // Update cash balance
      final newCashBalance = currentPortfolio.cashBalance + totalCost;

      // Update holding
      List<Holding> updatedHoldings;
      final newQuantity = existingHolding.quantity - quantity;

      if (newQuantity == 0) {
        // Remove holding completely
        updatedHoldings =
            currentPortfolio.holdings.where((h) => h.symbol != symbol).toList();
      } else {
        // Update quantity
        updatedHoldings = List.from(currentPortfolio.holdings);
        updatedHoldings[existingHoldingIndex] = existingHolding.copyWith(
          quantity: newQuantity,
          currentPrice: price,
        );
      }

      updatedPortfolio = currentPortfolio.copyWith(
        cashBalance: newCashBalance,
        holdings: updatedHoldings,
      );
    }

    // Save transaction and updated portfolio
    await _saveTransaction(transaction);
    await savePortfolio(updatedPortfolio);

    return updatedPortfolio;
  }

  /// Get transaction history
  Future<List<Transaction>> getTransactionHistory() async {
    final userId = await _deviceService.getUserId();
    return await _localDb.getTransactions(userId);
  }

  // Private local methods
  Future<Portfolio?> _getPortfolioLocal() async {
    final userId = await _deviceService.getUserId();
    return await _localDb.getPortfolio(userId);
  }

  Future<void> _savePortfolioLocal(Portfolio portfolio) async {
    await _localDb.savePortfolio(portfolio);
  }

  Future<void> _saveTransaction(Transaction transaction) async {
    if (_currentMode == DataMode.local) {
      await _localDb.saveTransaction(transaction);
    } else {
      // TODO: Implement remote transaction saving via API
      await _localDb.saveTransaction(transaction);
    }
  }

  // Private remote methods (TODO: Implement based on existing API service)
  Future<Portfolio?> _getPortfolioRemote() async {
    try {
      final Portfolio remotePortfolio = await _apiService.getPortfolio();
      return remotePortfolio;
    } catch (e) {
      // Fallback to local if remote fails
      return await _getPortfolioLocal();
    }
  }

  Future<void> _savePortfolioRemote(Portfolio portfolio) async {
    try {
      // TODO: Implement API call to save portfolio
      // For now, also save locally as backup
      await _savePortfolioLocal(portfolio);
    } catch (e) {
      // Fallback to local if remote fails
      await _savePortfolioLocal(portfolio);
    }
  }
}
