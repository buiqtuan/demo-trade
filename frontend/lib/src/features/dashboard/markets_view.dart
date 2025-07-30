import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/market_index.dart';
import '../../services/local_db_service.dart';

final marketIndicesProvider = FutureProvider<List<MarketIndex>>((ref) async {
  final localDb = ref.watch(localDbServiceProvider);

  // Get cached indices or return mock data
  final cachedIndices = await localDb.getMarketIndices();
  if (cachedIndices.isNotEmpty) {
    return cachedIndices;
  }

  // Mock data for major market indices
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

class MarketsView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final marketIndicesAsync = ref.watch(marketIndicesProvider);
    final newsAsync = ref.watch(newsProvider);

    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(marketIndicesProvider);
          ref.invalidate(newsProvider);
        },
        child: SingleChildScrollView(
          physics: AlwaysScrollableScrollPhysics(),
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
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
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                index.name,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey[700],
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              SizedBox(height: 4),
              Text(
                index.currentValue.toStringAsFixed(2),
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
