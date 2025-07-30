import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

// Mock leaderboard data
final leaderboardProvider = Provider<List<LeaderboardEntry>>((ref) {
  return [
    LeaderboardEntry(
      rank: 1,
      username: 'TradingMaster',
      userAvatar: '🏆',
      totalReturn: 45.23,
      portfolioValue: 145230.50,
      winRate: 78.5,
      tradesCount: 156,
    ),
    LeaderboardEntry(
      rank: 2,
      username: 'QuantTrader',
      userAvatar: '📊',
      totalReturn: 38.91,
      portfolioValue: 138910.75,
      winRate: 72.3,
      tradesCount: 203,
    ),
    LeaderboardEntry(
      rank: 3,
      username: 'DividendHero',
      userAvatar: '💰',
      totalReturn: 31.45,
      portfolioValue: 131450.25,
      winRate: 69.8,
      tradesCount: 89,
    ),
    LeaderboardEntry(
      rank: 4,
      username: 'TechBull',
      userAvatar: '🚀',
      totalReturn: 28.67,
      portfolioValue: 128670.00,
      winRate: 66.2,
      tradesCount: 145,
    ),
    LeaderboardEntry(
      rank: 5,
      username: 'ValueInvestor',
      userAvatar: '💎',
      totalReturn: 24.89,
      portfolioValue: 124890.50,
      winRate: 71.4,
      tradesCount: 78,
    ),
    LeaderboardEntry(
      rank: 6,
      username: 'GrowthSeeker',
      userAvatar: '📈',
      totalReturn: 22.15,
      portfolioValue: 122150.25,
      winRate: 64.8,
      tradesCount: 167,
    ),
    LeaderboardEntry(
      rank: 7,
      username: 'MarketNinja',
      userAvatar: '🥷',
      totalReturn: 19.78,
      portfolioValue: 119780.75,
      winRate: 68.9,
      tradesCount: 134,
    ),
    LeaderboardEntry(
      rank: 8,
      username: 'SwingTrader',
      userAvatar: '🎯',
      totalReturn: 17.23,
      portfolioValue: 117230.00,
      winRate: 62.1,
      tradesCount: 198,
    ),
  ];
});

// Current user's rank provider (mock)
final currentUserRankProvider = Provider<int>((ref) => 12);

class LeaderboardView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final leaderboard = ref.watch(leaderboardProvider);
    final currentUserRank = ref.watch(currentUserRankProvider);

    return RefreshIndicator(
      onRefresh: () async {
        // TODO: Implement refresh functionality
        await Future.delayed(Duration(seconds: 1));
      },
      child: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context),
            SizedBox(height: 16),
            _buildCurrentUserCard(context, currentUserRank),
            SizedBox(height: 16),
            _buildTopThree(context, leaderboard.take(3).toList()),
            SizedBox(height: 16),
            _buildFullLeaderboard(context, leaderboard),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.leaderboard, color: Colors.amber[700], size: 28),
                SizedBox(width: 12),
                Text(
                  'Leaderboard',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            SizedBox(height: 12),
            Text(
              'Top performing traders in the community',
              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            ),
            SizedBox(height: 16),
            Row(
              children: [
                _buildStatItem('Total Traders', '1,247'),
                SizedBox(width: 24),
                _buildStatItem('Avg. Return', '+18.4%'),
                SizedBox(width: 24),
                _buildStatItem('Top Return', '+45.2%'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
        SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: Colors.blue[900],
          ),
        ),
      ],
    );
  }

  Widget _buildCurrentUserCard(BuildContext context, int rank) {
    return Card(
      color: Colors.blue[50],
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: Colors.blue[900],
              child: Text('👤', style: TextStyle(fontSize: 20)),
            ),
            SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Your Position',
                    style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                  ),
                  Text(
                    'Rank #$rank',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue[900],
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '+12.8%',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.green,
                  ),
                ),
                Text(
                  '\$112,800',
                  style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopThree(BuildContext context, List<LeaderboardEntry> topThree) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Top 3 Performers',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            Row(
              children: [
                // 2nd place
                if (topThree.length > 1)
                  Expanded(
                    child: _buildPodiumCard(topThree[1], Colors.grey[400]!),
                  ),
                SizedBox(width: 8),
                // 1st place
                if (topThree.isNotEmpty)
                  Expanded(
                    child: _buildPodiumCard(topThree[0], Colors.amber[600]!),
                  ),
                SizedBox(width: 8),
                // 3rd place
                if (topThree.length > 2)
                  Expanded(
                    child: _buildPodiumCard(topThree[2], Colors.orange[400]!),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPodiumCard(LeaderboardEntry entry, Color medalColor) {
    final currencyFormat = NumberFormat.currency(symbol: '\$');

    return Container(
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: medalColor, width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: medalColor,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                entry.rank.toString(),
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          SizedBox(height: 8),
          Text(entry.userAvatar, style: TextStyle(fontSize: 24)),
          SizedBox(height: 4),
          Text(
            entry.username,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          SizedBox(height: 4),
          Text(
            '+${entry.totalReturn.toStringAsFixed(1)}%',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Colors.green,
            ),
          ),
          Text(
            currencyFormat.format(entry.portfolioValue),
            style: TextStyle(fontSize: 10, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  Widget _buildFullLeaderboard(
    BuildContext context,
    List<LeaderboardEntry> entries,
  ) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Full Rankings',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 12),
            ...entries.map((entry) => _buildLeaderboardItem(entry)),
          ],
        ),
      ),
    );
  }

  Widget _buildLeaderboardItem(LeaderboardEntry entry) {
    final currencyFormat = NumberFormat.currency(symbol: '\$');
    final isTopThree = entry.rank <= 3;

    return Container(
      margin: EdgeInsets.only(bottom: 8),
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isTopThree ? Colors.amber[50] : Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
        border:
            isTopThree ? Border.all(color: Colors.amber[200]!, width: 1) : null,
      ),
      child: Row(
        children: [
          // Rank
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: isTopThree ? Colors.amber[600] : Colors.grey[400],
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                entry.rank.toString(),
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ),
          ),
          SizedBox(width: 12),

          // Avatar and username
          CircleAvatar(
            backgroundColor: Colors.blue[100],
            child: Text(entry.userAvatar, style: TextStyle(fontSize: 18)),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.username,
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                Text(
                  '${entry.tradesCount} trades • ${entry.winRate.toStringAsFixed(1)}% win rate',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),

          // Performance stats
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '+${entry.totalReturn.toStringAsFixed(2)}%',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.green,
                ),
              ),
              Text(
                currencyFormat.format(entry.portfolioValue),
                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// Leaderboard entry data model
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
