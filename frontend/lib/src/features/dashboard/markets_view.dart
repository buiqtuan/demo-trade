import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../models/market_index.dart';
import '../../services/local_db_service.dart';
import '../../services/websocket_service.dart';
import '../../services/api_service.dart';

// Helper function to create market indices from price data
Future<List<MarketIndex>> _createMarketIndicesFromPrices(
  Map<String, double> prices, 
  LocalDbService localDb
) async {
  final realIndices = <MarketIndex>[];
  
  prices.forEach((symbol, price) {
    if (price > 0) {
      realIndices.add(MarketIndex(
        symbol: symbol,
        name: _getSymbolName(symbol),
        currentValue: price,
        dailyChange: 0.0, // TODO: Calculate from historical data
        dailyChangePercentage: 0.0,
        lastUpdated: DateTime.now(),
      ));
    }
  });
  
  if (realIndices.isNotEmpty) {
    await localDb.saveMarketIndices(realIndices);
  }
  
  return realIndices;
}

// Helper function to get display name for symbol
String _getSymbolName(String symbol) {
  switch (symbol) {
    case 'SPY':
      return 'S&P 500 ETF';
    case 'QQQ':
      return 'NASDAQ ETF';
    case 'DIA':
      return 'Dow Jones ETF';
    case 'IWM':
      return 'Russell 2000 ETF';
    default:
      return symbol;
  }
}

// Simplified market indices provider for local-first strategy
final marketIndicesProvider = FutureProvider<List<MarketIndex>>((ref) async {
  final localDb = ref.watch(localDbServiceProvider);
  
  try {
    // Try to get real-time data from backend (no authentication required)
    print('Attempting to fetch real market data from backend...');
    
    // Popular market symbols for real-time updates
    final marketSymbols = ['SPY', 'QQQ', 'DIA', 'IWM']; 
    final realIndices = <MarketIndex>[];
    
    // Try to get prices directly from backend API (now without authentication)
    for (final symbol in marketSymbols) {
      try {
        final response = await http.get(
          Uri.parse('http://localhost:8000/api/stocks/$symbol/price'),
          headers: {'Content-Type': 'application/json'},
        ).timeout(Duration(seconds: 5));
        
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          final price = data['price']?.toDouble() ?? 0.0;
          
          if (price > 0) {
            realIndices.add(MarketIndex(
              symbol: symbol,
              name: _getSymbolName(symbol),
              currentValue: price,
              dailyChange: 0.0, 
              dailyChangePercentage: 0.0,
              lastUpdated: DateTime.now(),
            ));
            print('Got price for $symbol: \$${price.toStringAsFixed(2)}');
          }
        }
      } catch (e) {
        print('Failed to get price for $symbol: $e');
      }
    }
    
    if (realIndices.isNotEmpty) {
      print('Successfully fetched ${realIndices.length} real prices via API');
      await localDb.saveMarketIndices(realIndices);
      return realIndices;
    }
  } catch (e) {
    print('Error fetching real market data: $e');
  }
  
  // Fallback to cached data
  final cachedIndices = await localDb.getMarketIndices();
  if (cachedIndices.isNotEmpty) {
    print('Using cached market data');
    return cachedIndices;
  }

  print('Using mock market data');
  // Final fallback to mock data
  final mockIndices = [
    MarketIndex(
      symbol: 'SPX',
      name: 'S&P 500',
      currentValue: 4756.50,
      dailyChange: 24.85,
      dailyChangePercentage: 0.53,
      lastUpdated: DateTime.now(),
    ),
    MarketIndex(
      symbol: 'IXIC',
      name: 'NASDAQ',
      currentValue: 14845.73,
      dailyChange: -12.45,
      dailyChangePercentage: -0.08,
      lastUpdated: DateTime.now(),
    ),
    MarketIndex(
      symbol: 'DJI',
      name: 'Dow Jones',
      currentValue: 37435.08,
      dailyChange: 156.89,
      dailyChangePercentage: 0.42,
      lastUpdated: DateTime.now(),
    ),
    MarketIndex(
      symbol: 'RUT',
      name: 'Russell 2000',
      currentValue: 2071.15,
      dailyChange: -8.34,
      dailyChangePercentage: -0.40,
      lastUpdated: DateTime.now(),
    ),
  ];

  // Cache the mock data
  await localDb.saveMarketIndices(mockIndices);
  return mockIndices;
});

// Real-time price updates provider (simplified)
final realTimePricesProvider = StreamProvider<Map<String, double>>((ref) {
  final websocketService = ref.watch(websocketServiceProvider);
  return websocketService.priceStream;
});

final newsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  // Mock financial news data
  // TODO: Replace with real API call
  return [
    {
      'headline': 'Tech Stocks Rally as AI Optimism Grows',
      'summary':
          'Major technology companies see gains amid renewed investor confidence in artificial intelligence development.',
      'timestamp': DateTime.now().subtract(Duration(hours: 2)),
      'source': 'MarketWatch',
    },
    {
      'headline': 'Federal Reserve Signals Potential Rate Changes',
      'summary':
          'Central bank officials hint at policy adjustments following latest economic data releases.',
      'timestamp': DateTime.now().subtract(Duration(hours: 4)),
      'source': 'Reuters',
    },
    {
      'headline': 'Energy Sector Shows Strong Performance',
      'summary':
          'Oil and gas companies outperform broader market as commodity prices stabilize.',
      'timestamp': DateTime.now().subtract(Duration(hours: 6)),
      'source': 'Bloomberg',
    },
    {
      'headline': 'Retail Earnings Beat Expectations',
      'summary':
          'Consumer spending remains robust as major retailers report better-than-expected quarterly results.',
      'timestamp': DateTime.now().subtract(Duration(hours: 8)),
      'source': 'CNBC',
    },
  ];
});

class MarketsView extends ConsumerStatefulWidget {
  @override
  ConsumerState<MarketsView> createState() => _MarketsViewState();
}

class _MarketsViewState extends ConsumerState<MarketsView> {
  Map<String, double> _latestPrices = {};

  @override
  void initState() {
    super.initState();
    _initializeRealTimeData();
  }

  void _initializeRealTimeData() {
    // Subscribe to popular stocks for real-time updates (local-first strategy)
    final websocketService = ref.read(websocketServiceProvider);
    
    // Initialize connection for local-first app
    websocketService.initializeConnection();
    websocketService.subscribeToPopularStocks();
    print('Initialized real-time connection for local-first app');
  }

  @override
  Widget build(BuildContext context) {
    final marketIndicesAsync = ref.watch(marketIndicesProvider);
    final newsAsync = ref.watch(newsProvider);
    final realTimePricesAsync = ref.watch(realTimePricesProvider);
    
    // Update latest prices when real-time data comes in
    realTimePricesAsync.whenData((prices) {
      setState(() {
        _latestPrices = Map.from(prices);
      });
    });

    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(marketIndicesProvider);
          ref.invalidate(newsProvider);
          
          // Reconnect WebSocket
          final websocketService = ref.read(websocketServiceProvider);
          await websocketService.reconnect();
        },
        child: SingleChildScrollView(
          physics: AlwaysScrollableScrollPhysics(),
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Connection status indicator
              _buildConnectionStatus(realTimePricesAsync),
              
              SizedBox(height: 16),
              
              // Market Indices Section
              _buildSectionHeader('Markets', Icons.trending_up),
              SizedBox(height: 12),
              marketIndicesAsync.when(
                data: (indices) => _buildMarketIndicesGrid(indices),
                loading: () => _buildLoadingGrid(),
                error: (error, stack) =>
                    _buildErrorWidget('Failed to load market data'),
              ),

              SizedBox(height: 32),

              // Financial News Section
              _buildSectionHeader('Financial News', Icons.article),
              SizedBox(height: 12),
              newsAsync.when(
                data: (news) => _buildNewsList(news),
                loading: () => _buildLoadingNews(),
                error: (error, stack) =>
                    _buildErrorWidget('Failed to load news'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConnectionStatus(AsyncValue<Map<String, double>> realTimePricesAsync) {
    final websocketService = ref.watch(websocketServiceProvider);
    final isConnected = websocketService.isConnected;
    
    Color statusColor;
    String statusText;
    IconData statusIcon;
    
    if (isConnected && realTimePricesAsync.hasValue && realTimePricesAsync.value!.isNotEmpty) {
      statusColor = Colors.green;
      statusText = 'Live Data Connected';
      statusIcon = Icons.wifi;
    } else if (isConnected) {
      statusColor = Colors.orange;
      statusText = 'Connected - Waiting for Data';
      statusIcon = Icons.wifi;
    } else {
      statusColor = Colors.blue;
      statusText = 'Connecting to Live Data...';
      statusIcon = Icons.wifi_off;
    }
    
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: statusColor.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(statusIcon, color: statusColor, size: 16),
          SizedBox(width: 6),
          Text(
            statusText,
            style: TextStyle(
              color: statusColor,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (_latestPrices.isNotEmpty)
            ...[
              SizedBox(width: 8),
              Text(
                '${_latestPrices.length} symbols',
                style: TextStyle(
                  color: statusColor.withOpacity(0.8),
                  fontSize: 11,
                ),
              ),
            ],
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: Colors.blue[700], size: 24),
        SizedBox(width: 8),
        Text(
          title,
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.bold,
            color: Colors.grey[800],
          ),
        ),
      ],
    );
  }

  Widget _buildMarketIndicesGrid(List<MarketIndex> indices) {
    return GridView.builder(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 1.6,
      ),
      itemCount: indices.length,
      itemBuilder: (context, index) {
        final marketIndex = indices[index];
        return _buildMarketIndexCard(marketIndex);
      },
    );
  }

  Widget _buildMarketIndexCard(MarketIndex index) {
    final isPositive = index.isPositive;
    final color = isPositive ? Colors.green : Colors.red;
    
    // Check if we have real-time price for this symbol
    final realtimePrice = _latestPrices[index.symbol];
    final displayPrice = realtimePrice ?? index.currentValue;
    final isRealTime = realtimePrice != null;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
        // Add a subtle border for real-time data
        border: isRealTime 
          ? Border.all(color: Colors.blue.withOpacity(0.3), width: 1)
          : null,
      ),
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      index.name,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey[700],
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (isRealTime)
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: Colors.green,
                        shape: BoxShape.circle,
                      ),
                    ),
                ],
              ),
              SizedBox(height: 4),
              Text(
                displayPrice.toStringAsFixed(2),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[900],
                ),
              ),
            ],
          ),
          Row(
            children: [
              Icon(
                isPositive ? Icons.arrow_upward : Icons.arrow_downward,
                color: color,
                size: 16,
              ),
              SizedBox(width: 4),
              Text(
                '${isPositive ? '+' : ''}${index.dailyChange.toStringAsFixed(2)}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
              ),
              SizedBox(width: 4),
              Text(
                '(${isPositive ? '+' : ''}${index.dailyChangePercentage.toStringAsFixed(2)}%)',
                style: TextStyle(
                  fontSize: 12,
                  color: color,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNewsList(List<Map<String, dynamic>> news) {
    return ListView.separated(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      itemCount: news.length,
      separatorBuilder: (context, index) => SizedBox(height: 12),
      itemBuilder: (context, index) {
        final article = news[index];
        return _buildNewsCard(article);
      },
    );
  }

  Widget _buildNewsCard(Map<String, dynamic> article) {
    final timestamp = article['timestamp'] as DateTime;
    final timeAgo = _getTimeAgo(timestamp);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            article['headline'],
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.grey[900],
              height: 1.3,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          SizedBox(height: 8),
          Text(
            article['summary'],
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
              height: 1.4,
            ),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
          SizedBox(height: 12),
          Row(
            children: [
              Text(
                article['source'],
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.blue[600],
                ),
              ),
              Spacer(),
              Text(
                timeAgo,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[500],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingGrid() {
    return GridView.builder(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 1.6,
      ),
      itemCount: 4,
      itemBuilder: (context, index) => _buildLoadingCard(),
    );
  }

  Widget _buildLoadingNews() {
    return Column(
      children: List.generate(
        3,
        (index) => Container(
          margin: EdgeInsets.only(bottom: 12),
          child: _buildLoadingCard(height: 120),
        ),
      ),
    );
  }

  Widget _buildLoadingCard({double? height}) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
        ),
      ),
    );
  }

  Widget _buildErrorWidget(String message) {
    return Container(
      padding: EdgeInsets.all(32),
      child: Column(
        children: [
          Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
          SizedBox(height: 16),
          Text(
            message,
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  String _getTimeAgo(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }
}
