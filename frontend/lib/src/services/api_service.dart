import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/auth/auth_repository.dart';
import '../models/portfolio.dart';
import '../features/dashboard/chart_view.dart';

// API service provider
final apiServiceProvider = Provider<ApiService>((ref) {
  final authRepository = ref.watch(authRepositoryProvider);
  return ApiService(authRepository);
});

class ApiService {
  final AuthRepository _authRepository;

  // TODO: Update this URL to your deployed backend or use local for development
  static const String _baseUrl = 'http://localhost:8000';

  ApiService(this._authRepository);

  /// Get authenticated headers with Firebase ID token
  Future<Map<String, String>> _getAuthHeaders() async {
    final idToken = await _authRepository.getIdToken();
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $idToken',
    };
  }

  /// Get current user's portfolio
  Future<Portfolio> getPortfolio() async {
    try {
      final headers = await _getAuthHeaders();
      final user = _authRepository.currentUser;

      if (user == null) {
        throw Exception('User not authenticated');
      }

      final response = await http.get(
        Uri.parse('$_baseUrl/portfolios/${user.uid}'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return Portfolio.fromJson(data);
      } else {
        throw Exception('Failed to load portfolio: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching portfolio: $e');
      rethrow;
    }
  }

  /// Get stock chart data
  Future<List<CandlestickData>> getStockData(String symbol) async {
    try {
      final headers = await _getAuthHeaders();

      final response = await http.get(
        Uri.parse('$_baseUrl/stocks/$symbol/data'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => CandlestickData.fromJson(item)).toList();
      } else {
        throw Exception('Failed to load stock data: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching stock data: $e');
      rethrow;
    }
  }

  /// Execute a trade (buy/sell)
  Future<TradeResult> executeTrade({
    required String symbol,
    required String action, // 'BUY' or 'SELL'
    required double quantity,
  }) async {
    try {
      final headers = await _getAuthHeaders();

      final requestBody = {
        'ticker': symbol,
        'quantity': quantity,
        'action': action,
      };

      final response = await http.post(
        Uri.parse('$_baseUrl/execute'),
        headers: headers,
        body: json.encode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return TradeResult.fromJson(data);
      } else {
        final errorData = json.decode(response.body);
        throw Exception(errorData['detail'] ?? 'Trade execution failed');
      }
    } catch (e) {
      print('Error executing trade: $e');
      rethrow;
    }
  }

  /// Get current stock price
  Future<double> getCurrentPrice(String symbol) async {
    try {
      final headers = await _getAuthHeaders();

      final response = await http.get(
        Uri.parse('$_baseUrl/stocks/$symbol/price'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['price'].toDouble();
      } else {
        throw Exception('Failed to get current price: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching current price: $e');
      rethrow;
    }
  }

  /// Get leaderboard data
  Future<List<LeaderboardEntry>> getLeaderboard() async {
    try {
      final headers = await _getAuthHeaders();

      final response = await http.get(
        Uri.parse('$_baseUrl/leaderboard'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => LeaderboardEntry.fromJson(item)).toList();
      } else {
        throw Exception('Failed to load leaderboard: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching leaderboard: $e');
      rethrow;
    }
  }

  /// Get user's current rank
  Future<int> getUserRank() async {
    try {
      final headers = await _getAuthHeaders();
      final user = _authRepository.currentUser;

      if (user == null) {
        throw Exception('User not authenticated');
      }

      final response = await http.get(
        Uri.parse('$_baseUrl/users/${user.uid}/rank'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['rank'];
      } else {
        throw Exception('Failed to get user rank: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching user rank: $e');
      rethrow;
    }
  }

  /// Search for stocks
  Future<List<StockSearchResult>> searchStocks(String query) async {
    try {
      final headers = await _getAuthHeaders();

      final response = await http.get(
        Uri.parse('$_baseUrl/stocks/search?q=${Uri.encodeComponent(query)}'),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => StockSearchResult.fromJson(item)).toList();
      } else {
        throw Exception('Failed to search stocks: ${response.statusCode}');
      }
    } catch (e) {
      print('Error searching stocks: $e');
      rethrow;
    }
  }

  /// Create new user account in backend
  Future<void> createUserAccount({
    required String userId,
    required String email,
    required String username,
  }) async {
    try {
      final headers = await _getAuthHeaders();

      final requestBody = {
        'user_id': userId,
        'email': email,
        'username': username,
      };

      final response = await http.post(
        Uri.parse('$_baseUrl/users'),
        headers: headers,
        body: json.encode(requestBody),
      );

      if (response.statusCode != 201) {
        final errorData = json.decode(response.body);
        throw Exception(errorData['detail'] ?? 'Failed to create user account');
      }
    } catch (e) {
      print('Error creating user account: $e');
      rethrow;
    }
  }
}

// Data models for API responses

class TradeResult {
  final String message;
  final double executionPrice;
  final double newCashBalance;
  final double totalPortfolioValue;

  TradeResult({
    required this.message,
    required this.executionPrice,
    required this.newCashBalance,
    required this.totalPortfolioValue,
  });

  factory TradeResult.fromJson(Map<String, dynamic> json) {
    return TradeResult(
      message: json['message'],
      executionPrice: json['execution_price'].toDouble(),
      newCashBalance: json['new_cash_balance'].toDouble(),
      totalPortfolioValue: json['total_portfolio_value'].toDouble(),
    );
  }
}

class LeaderboardEntry {
  final int rank;
  final String username;
  final String userAvatar;
  final double totalReturn;
  final double portfolioValue;
  final double winRate;
  final int tradesCount;

  LeaderboardEntry({
    required this.rank,
    required this.username,
    required this.userAvatar,
    required this.totalReturn,
    required this.portfolioValue,
    required this.winRate,
    required this.tradesCount,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) {
    return LeaderboardEntry(
      rank: json['rank'],
      username: json['username'],
      userAvatar: json['user_avatar'],
      totalReturn: json['total_return'].toDouble(),
      portfolioValue: json['portfolio_value'].toDouble(),
      winRate: json['win_rate'].toDouble(),
      tradesCount: json['trades_count'],
    );
  }
}

class StockSearchResult {
  final String symbol;
  final String name;
  final String exchange;
  final double? currentPrice;

  StockSearchResult({
    required this.symbol,
    required this.name,
    required this.exchange,
    this.currentPrice,
  });

  factory StockSearchResult.fromJson(Map<String, dynamic> json) {
    return StockSearchResult(
      symbol: json['symbol'],
      name: json['name'],
      exchange: json['exchange'],
      currentPrice: json['current_price']?.toDouble(),
    );
  }
}
