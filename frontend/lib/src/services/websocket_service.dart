import 'dart:convert';
import 'dart:async';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/auth/auth_repository.dart';
import '../config/app_config.dart';

// WebSocket service provider
final websocketServiceProvider = Provider<WebSocketService>((ref) {
  final authRepository = ref.watch(authRepositoryProvider);
  return WebSocketService(authRepository);
});

class WebSocketService {
  final AuthRepository _authRepository;
  WebSocketChannel? _channel;

  static const String _baseWsUrl = AppConfig.wsBaseUrl;

  // Stream controller for real-time price data
  final _priceController = StreamController<Map<String, double>>.broadcast();

  // Current prices cache
  final Map<String, double> _currentPrices = {};

  // Connection status
  bool _isConnected = false;
  Timer? _reconnectTimer;

  WebSocketService(this._authRepository) {
    _initializeConnection();
  }

  /// Stream of real-time price updates
  Stream<Map<String, double>> get priceStream => _priceController.stream;

  /// Get current connection status
  bool get isConnected => _isConnected;

  /// Get current cached prices
  Map<String, double> get currentPrices => Map.unmodifiable(_currentPrices);

  /// Initialize WebSocket connection
  Future<void> _initializeConnection() async {
    final user = _authRepository.currentUser;
    if (user == null) {
      print('Cannot connect to WebSocket: User not authenticated');
      return;
    }

    try {
      await _connect(user.uid);
    } catch (e) {
      print('Failed to initialize WebSocket connection: $e');
      _scheduleReconnect();
    }
  }

  /// Connect to WebSocket
  Future<void> _connect(String userId) async {
    try {
      // Get authentication token
      final idToken = await _authRepository.getIdToken();
      if (idToken == null) {
        throw Exception('Failed to get authentication token');
      }

      // Connect to WebSocket with user ID and auth token
      final uri = Uri.parse('$_baseWsUrl/$userId/ws?token=$idToken');
      _channel = IOWebSocketChannel.connect(uri);

      // Listen for messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
      );

      _isConnected = true;
      print('WebSocket connected successfully');

      // Cancel any existing reconnect timer
      _reconnectTimer?.cancel();
    } catch (e) {
      print('WebSocket connection failed: $e');
      _isConnected = false;
      _scheduleReconnect();
      rethrow;
    }
  }

  /// Handle incoming WebSocket messages
  void _handleMessage(dynamic message) {
    try {
      final data = json.decode(message.toString());

      if (data['type'] == 'price_update') {
        final prices = Map<String, double>.from(
          (data['prices'] as Map).map(
            (key, value) => MapEntry(key.toString(), value.toDouble()),
          ),
        );

        // Update cached prices
        _currentPrices.addAll(prices);

        // Emit price update
        _priceController.add(Map.from(_currentPrices));

        print('Received price update: ${prices.length} symbols');
      } else if (data['type'] == 'error') {
        print('WebSocket error: ${data['message']}');
      } else if (data['type'] == 'connection_ack') {
        print('WebSocket connection acknowledged');
      }
    } catch (e) {
      print('Error parsing WebSocket message: $e');
    }
  }

  /// Handle WebSocket errors
  void _handleError(error) {
    print('WebSocket error: $error');
    _isConnected = false;
    _scheduleReconnect();
  }

  /// Handle WebSocket disconnection
  void _handleDisconnect() {
    print('WebSocket disconnected');
    _isConnected = false;
    _scheduleReconnect();
  }

  /// Schedule reconnection attempt
  void _scheduleReconnect() {
    _reconnectTimer?.cancel();

    _reconnectTimer = Timer(Duration(seconds: 5), () {
      print('Attempting to reconnect WebSocket...');
      _initializeConnection();
    });
  }

  /// Manually reconnect
  Future<void> reconnect() async {
    await disconnect();
    await _initializeConnection();
  }

  /// Send message to WebSocket
  void _sendMessage(Map<String, dynamic> message) {
    if (_isConnected && _channel != null) {
      try {
        _channel!.sink.add(json.encode(message));
      } catch (e) {
        print('Error sending WebSocket message: $e');
      }
    } else {
      print('Cannot send message: WebSocket not connected');
    }
  }

  /// Subscribe to specific symbols
  void subscribeToSymbols(List<String> symbols) {
    _sendMessage({'type': 'subscribe', 'symbols': symbols});
    print('Subscribed to symbols: $symbols');
  }

  /// Unsubscribe from specific symbols
  void unsubscribeFromSymbols(List<String> symbols) {
    _sendMessage({'type': 'unsubscribe', 'symbols': symbols});
    print('Unsubscribed from symbols: $symbols');
  }

  /// Get latest price for a specific symbol
  double? getPrice(String symbol) {
    return _currentPrices[symbol];
  }

  /// Send ping to keep connection alive
  void ping() {
    _sendMessage({'type': 'ping'});
  }

  /// Disconnect WebSocket
  Future<void> disconnect() async {
    _reconnectTimer?.cancel();

    if (_channel != null) {
      await _channel!.sink.close();
      _channel = null;
    }

    _isConnected = false;
    print('WebSocket disconnected');
  }

  /// Dispose resources
  void dispose() {
    disconnect();
    _priceController.close();
  }
}

// Extension to provide default symbols for subscription
extension WebSocketServiceExtension on WebSocketService {
  /// Subscribe to default popular stocks
  void subscribeToPopularStocks() {
    const popularStocks = [
      'AAPL',
      'GOOGL',
      'MSFT',
      'AMZN',
      'TSLA',
      'NVDA',
      'META',
      'NFLX',
      'JPM',
      'JNJ',
    ];
    subscribeToSymbols(popularStocks);
  }
}

// Price update data model
class PriceUpdate {
  final String symbol;
  final double price;
  final DateTime timestamp;
  final double? change;
  final double? changePercent;

  PriceUpdate({
    required this.symbol,
    required this.price,
    required this.timestamp,
    this.change,
    this.changePercent,
  });

  factory PriceUpdate.fromJson(Map<String, dynamic> json) {
    return PriceUpdate(
      symbol: json['symbol'],
      price: json['price'].toDouble(),
      timestamp: DateTime.fromMillisecondsSinceEpoch(json['timestamp']),
      change: json['change']?.toDouble(),
      changePercent: json['change_percent']?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'price': price,
      'timestamp': timestamp.millisecondsSinceEpoch,
      'change': change,
      'change_percent': changePercent,
    };
  }
}
