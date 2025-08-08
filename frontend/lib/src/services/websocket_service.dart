import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_config.dart';

// WebSocket service provider
final websocketServiceProvider = Provider<WebSocketService>((ref) {
  return WebSocketService();
});

class WebSocketService {
  WebSocketChannel? _channel;
  StreamController<Map<String, double>>? _priceController;
  Stream<Map<String, double>>? _priceStream;
  bool _isConnected = false;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  int _reconnectAttempts = 0;
  
  static const String _wsUrl = AppConfig.wsUrl;
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _reconnectDelay = Duration(seconds: 5);
  static const int _maxReconnectAttempts = 3;

  WebSocketService() {
    _priceController = StreamController<Map<String, double>>.broadcast();
    _priceStream = _priceController!.stream;
  }

  /// Get the price stream for real-time updates
  Stream<Map<String, double>> get priceStream => _priceStream!;

  /// Check if WebSocket is connected
  bool get isConnected => _isConnected;

  /// Initialize WebSocket connection
  Future<void> initializeConnection() async {
    if (_isConnected) return;
    
    try {
      print('Attempting to connect to WebSocket at $_wsUrl');
      _channel = WebSocketChannel.connect(
        Uri.parse(_wsUrl),
        protocols: null,
      );
      
      // Listen for connection establishment with timeout
      await _channel!.ready.timeout(
        Duration(seconds: 5),
        onTimeout: () {
          throw TimeoutException('WebSocket connection timeout');
        },
      );
      
      _isConnected = true;
      print('WebSocket connected successfully');
      
      // Start listening to messages
      _listenToMessages();
      
      // Start heartbeat
      _startHeartbeat();
      
    } catch (e) {
      print('Failed to connect to WebSocket: $e');
      _isConnected = false;
      
      // Don't attempt reconnection if backend is not available
      if (e.toString().contains('connection failed') || 
          e.toString().contains('timeout') ||
          e.toString().contains('refused')) {
        print('Backend WebSocket server not available. Running in offline mode.');
        return;
      }
      
      _scheduleReconnect();
    }
  }

  /// Subscribe to popular stocks for real-time updates
  void subscribeToPopularStocks() {
    if (!_isConnected || _channel == null) {
      print('WebSocket not connected, running in offline mode with mock data');
      
      // Emit mock data for demo purposes when WebSocket is not available
      _emitMockPriceData();
      return;
    }

    final popularSymbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'SPY', 'QQQ', 'DIA', 'IWM'];
    
    try {
      final subscribeMessage = {
        'action': 'subscribe',
        'symbols': popularSymbols,
      };
      
      _channel!.sink.add(json.encode(subscribeMessage));
      print('Subscribed to ${popularSymbols.length} popular stocks');
    } catch (e) {
      print('Failed to subscribe to stocks: $e');
    }
  }

  /// Emit mock price data for offline mode
  void _emitMockPriceData() {
    // Generate mock prices for popular symbols
    final mockPrices = <String, double>{
      'AAPL': 150.25 + (DateTime.now().millisecond % 100) / 100,
      'GOOGL': 2800.50 + (DateTime.now().millisecond % 200) / 100,
      'MSFT': 300.75 + (DateTime.now().millisecond % 150) / 100,
      'AMZN': 3200.00 + (DateTime.now().millisecond % 300) / 100,
      'TSLA': 800.25 + (DateTime.now().millisecond % 250) / 100,
      'NVDA': 450.80 + (DateTime.now().millisecond % 180) / 100,
      'SPY': 450.15 + (DateTime.now().millisecond % 120) / 100,
      'QQQ': 380.90 + (DateTime.now().millisecond % 140) / 100,
    };
    
    // Emit the mock data after a short delay
    Timer(Duration(milliseconds: 500), () {
      _priceController?.add(mockPrices);
      print('Emitted mock price data for ${mockPrices.length} symbols');
    });
  }

  /// Listen to WebSocket messages
  void _listenToMessages() {
    _channel!.stream.listen(
      (message) {
        try {
          final data = json.decode(message);
          _handleMessage(data);
        } catch (e) {
          print('Error parsing WebSocket message: $e');
        }
      },
      onError: (error) {
        print('WebSocket error: $error');
        _handleDisconnection();
      },
      onDone: () {
        print('WebSocket connection closed');
        _handleDisconnection();
      },
    );
  }

  /// Handle incoming WebSocket messages
  void _handleMessage(Map<String, dynamic> data) {
    final type = data['type'];
    
    switch (type) {
      case 'price_update':
        _handlePriceUpdate(data);
        break;
      case 'batch_prices':
        _handleBatchPrices(data);
        break;
      case 'heartbeat':
        print('Received heartbeat from server');
        break;
      default:
        print('Unknown message type: $type');
    }
  }

  /// Handle price update messages
  void _handlePriceUpdate(Map<String, dynamic> data) {
    try {
      final symbol = data['symbol'] as String?;
      final price = data['price']?.toDouble();
      
      if (symbol != null && price != null) {
        final currentPrices = <String, double>{symbol: price};
        _priceController?.add(currentPrices);
        print('Price update: $symbol = \$${price.toStringAsFixed(2)}');
      }
    } catch (e) {
      print('Error handling price update: $e');
    }
  }

  /// Handle batch price updates
  void _handleBatchPrices(Map<String, dynamic> data) {
    try {
      final prices = data['prices'] as Map<String, dynamic>?;
      
      if (prices != null) {
        final priceMap = <String, double>{};
        prices.forEach((symbol, price) {
          if (price is num) {
            priceMap[symbol] = price.toDouble();
          }
        });
        
        if (priceMap.isNotEmpty) {
          _priceController?.add(priceMap);
          print('Batch price update: ${priceMap.length} symbols');
        }
      }
    } catch (e) {
      print('Error handling batch prices: $e');
    }
  }

  /// Handle WebSocket disconnection
  void _handleDisconnection() {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    _scheduleReconnect();
  }

  /// Start heartbeat to keep connection alive
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (_isConnected && _channel != null) {
        try {
          final heartbeatMessage = {
            'action': 'heartbeat',
            'timestamp': DateTime.now().millisecondsSinceEpoch,
          };
          _channel!.sink.add(json.encode(heartbeatMessage));
        } catch (e) {
          print('Failed to send heartbeat: $e');
          _handleDisconnection();
        }
      }
    });
  }

  /// Schedule reconnection attempt
  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    
    // Only attempt reconnection a few times before giving up
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      print('Max reconnection attempts reached. WebSocket will remain disconnected.');
      return;
    }
    
    _reconnectAttempts++;
    print('Scheduling reconnection attempt ${_reconnectAttempts}/${_maxReconnectAttempts}...');
    
    _reconnectTimer = Timer(_reconnectDelay, () {
      print('Attempting to reconnect WebSocket...');
      initializeConnection();
    });
  }

  /// Manually reconnect WebSocket
  Future<void> reconnect() async {
    print('Manual WebSocket reconnection requested');
    await disconnect();
    
    // Reset reconnection attempts counter for manual reconnect
    _reconnectAttempts = 0;
    
    await initializeConnection();
    if (_isConnected) {
      subscribeToPopularStocks();
    }
  }

  /// Disconnect WebSocket
  Future<void> disconnect() async {
    _isConnected = false;
    _heartbeatTimer?.cancel();
    _reconnectTimer?.cancel();
    
    try {
      await _channel?.sink.close();
    } catch (e) {
      print('Error closing WebSocket: $e');
    }
    
    _channel = null;
    print('WebSocket disconnected');
  }

  /// Subscribe to specific symbol
  void subscribeToSymbol(String symbol) {
    if (!_isConnected || _channel == null) {
      print('WebSocket not connected, cannot subscribe to $symbol');
      return;
    }

    try {
      final subscribeMessage = {
        'action': 'subscribe',
        'symbols': [symbol],
      };
      
      _channel!.sink.add(json.encode(subscribeMessage));
      print('Subscribed to $symbol');
    } catch (e) {
      print('Failed to subscribe to $symbol: $e');
    }
  }

  /// Unsubscribe from specific symbol
  void unsubscribeFromSymbol(String symbol) {
    if (!_isConnected || _channel == null) {
      print('WebSocket not connected, cannot unsubscribe from $symbol');
      return;
    }

    try {
      final unsubscribeMessage = {
        'action': 'unsubscribe',
        'symbols': [symbol],
      };
      
      _channel!.sink.add(json.encode(unsubscribeMessage));
      print('Unsubscribed from $symbol');
    } catch (e) {
      print('Failed to unsubscribe from $symbol: $e');
    }
  }

  /// Dispose resources
  void dispose() {
    disconnect();
    _priceController?.close();
  }
}