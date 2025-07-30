import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/portfolio.dart';
import '../../models/transaction.dart';
import '../../repositories/portfolio_repository.dart';

final portfolioProvider = FutureProvider<Portfolio?>((ref) async {
  final repository = ref.watch(portfolioRepositoryProvider);
  return await repository.getPortfolio();
});

final transactionHistoryProvider =
    FutureProvider<List<Transaction>>((ref) async {
  final repository = ref.watch(portfolioRepositoryProvider);
  return await repository.getTransactionHistory();
});

class PortfolioViewNew extends ConsumerStatefulWidget {
  @override
  ConsumerState<PortfolioViewNew> createState() => _PortfolioViewNewState();
}

class _PortfolioViewNewState extends ConsumerState<PortfolioViewNew>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _initializePortfolio() async {
    try {
      final repository = ref.read(portfolioRepositoryProvider);
      await repository.createInitialPortfolio();
      ref.invalidate(portfolioProvider);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to initialize portfolio: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final portfolioAsync = ref.watch(portfolioProvider);

    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: portfolioAsync.when(
        data: (portfolio) {
          if (portfolio == null) {
            return _buildInitializePortfolio();
          }
          return _buildPortfolioContent(portfolio);
        },
        loading: () => Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
          ),
        ),
        error: (error, stack) => _buildErrorContent(),
      ),
    );
  }

  Widget _buildInitializePortfolio() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.account_balance_wallet_outlined,
            size: 80,
            color: Colors.grey[400],
          ),
          SizedBox(height: 24),
          Text(
            'Start Your Trading Journey',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.grey[800],
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Initialize your portfolio with \$100,000\nvirtual cash to start trading.',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
              height: 1.4,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 32),
          ElevatedButton(
            onPressed: _initializePortfolio,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blue[600],
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(horizontal: 32, vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: Text(
              'Initialize Portfolio',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPortfolioContent(Portfolio portfolio) {
    return Column(
      children: [
        // Portfolio Header
        Container(
          width: double.infinity,
          padding: EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Colors.blue[700]!, Colors.blue[900]!],
            ),
          ),
          child: Column(
            children: [
              Text(
                'Portfolio Value',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
              SizedBox(height: 8),
              Text(
                '\$${portfolio.totalValue.toStringAsFixed(2)}',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 8),
              _buildProfitLossIndicator(portfolio),
            ],
          ),
        ),

        // Portfolio Metrics
        Container(
          color: Colors.white,
          padding: EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                  child: _buildMetricCard(
                'Cash Balance',
                '\$${portfolio.cashBalance.toStringAsFixed(2)}',
                Icons.account_balance_wallet,
                Colors.green[600]!,
              )),
              SizedBox(width: 12),
              Expanded(
                  child: _buildMetricCard(
                'Holdings',
                '${portfolio.holdings.length}',
                Icons.pie_chart,
                Colors.orange[600]!,
              )),
              SizedBox(width: 12),
              Expanded(
                  child: _buildMetricCard(
                'Initial',
                '\$${portfolio.initialBalance.toStringAsFixed(2)}',
                Icons.trending_up,
                Colors.blue[600]!,
              )),
            ],
          ),
        ),

        // Tab Bar
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: Colors.blue[700],
            unselectedLabelColor: Colors.grey[600],
            indicatorColor: Colors.blue[700],
            tabs: [
              Tab(text: 'Holdings'),
              Tab(text: 'History'),
            ],
          ),
        ),

        // Tab Content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildHoldingsTab(portfolio.holdings),
              _buildHistoryTab(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildProfitLossIndicator(Portfolio portfolio) {
    final profitLoss = portfolio.totalProfitLoss;
    final profitLossPercentage = portfolio.totalProfitLossPercentage;
    final isPositive = profitLoss >= 0;
    final color = isPositive ? Colors.green[300]! : Colors.red[300]!;

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isPositive ? Icons.trending_up : Icons.trending_down,
            color: color,
            size: 16,
          ),
          SizedBox(width: 4),
          Text(
            '${isPositive ? '+' : ''}\$${profitLoss.abs().toStringAsFixed(2)}',
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          SizedBox(width: 4),
          Text(
            '(${isPositive ? '+' : ''}${profitLossPercentage.toStringAsFixed(2)}%)',
            style: TextStyle(
              color: color,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricCard(
      String title, String value, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.grey[800],
            ),
          ),
          SizedBox(height: 4),
          Text(
            title,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildHoldingsTab(List<Holding> holdings) {
    if (holdings.isEmpty) {
      return _buildEmptyHoldings();
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(portfolioProvider);
      },
      child: ListView.separated(
        padding: EdgeInsets.all(16),
        itemCount: holdings.length,
        separatorBuilder: (context, index) => SizedBox(height: 12),
        itemBuilder: (context, index) {
          final holding = holdings[index];
          return _buildHoldingCard(holding);
        },
      ),
    );
  }

  Widget _buildHoldingCard(Holding holding) {
    final profitLoss = holding.profitLoss;
    final profitLossPercentage = holding.profitLossPercentage;
    final isPositive = profitLoss >= 0;
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
      child: ListTile(
        contentPadding: EdgeInsets.all(16),
        leading: CircleAvatar(
          backgroundColor: Colors.blue[50],
          child: Text(
            holding.symbol[0],
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.blue[700],
            ),
          ),
        ),
        title: Text(
          holding.symbol,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              holding.name,
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 14,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            SizedBox(height: 4),
            Text(
              '${holding.quantity.toStringAsFixed(2)} shares @ \$${holding.averageCostBasis.toStringAsFixed(2)}',
              style: TextStyle(
                color: Colors.grey[500],
                fontSize: 12,
              ),
            ),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              '\$${holding.totalValue.toStringAsFixed(2)}',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isPositive ? Icons.arrow_upward : Icons.arrow_downward,
                  color: color,
                  size: 14,
                ),
                Text(
                  '${isPositive ? '+' : ''}\$${profitLoss.abs().toStringAsFixed(2)}',
                  style: TextStyle(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            Text(
              '(${isPositive ? '+' : ''}${profitLossPercentage.toStringAsFixed(2)}%)',
              style: TextStyle(
                color: color,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyHoldings() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.pie_chart_outline, size: 64, color: Colors.grey[400]),
          SizedBox(height: 16),
          Text(
            'No Holdings Yet',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Colors.grey[700],
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Start trading to see your holdings here',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryTab() {
    final transactionsAsync = ref.watch(transactionHistoryProvider);

    return transactionsAsync.when(
      data: (transactions) {
        if (transactions.isEmpty) {
          return _buildEmptyHistory();
        }
        return RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(transactionHistoryProvider);
          },
          child: ListView.separated(
            padding: EdgeInsets.all(16),
            itemCount: transactions.length,
            separatorBuilder: (context, index) => SizedBox(height: 8),
            itemBuilder: (context, index) {
              final transaction = transactions[index];
              return _buildTransactionCard(transaction);
            },
          ),
        );
      },
      loading: () => Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
        ),
      ),
      error: (error, stack) => _buildErrorContent(),
    );
  }

  Widget _buildTransactionCard(Transaction transaction) {
    final isBuy = transaction.type == TransactionType.buy;
    final color = isBuy ? Colors.green : Colors.red;

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
      child: ListTile(
        contentPadding: EdgeInsets.all(16),
        leading: Container(
          padding: EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            isBuy ? Icons.add : Icons.remove,
            color: color,
            size: 20,
          ),
        ),
        title: Text(
          '${isBuy ? 'Bought' : 'Sold'} ${transaction.symbol}',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(height: 4),
            Text(
              '${transaction.quantity.toStringAsFixed(2)} shares @ \$${transaction.price.toStringAsFixed(2)}',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 14,
              ),
            ),
            SizedBox(height: 2),
            Text(
              _formatDate(transaction.timestamp),
              style: TextStyle(
                color: Colors.grey[500],
                fontSize: 12,
              ),
            ),
          ],
        ),
        trailing: Text(
          '${isBuy ? '-' : '+'}\$${transaction.totalValue.toStringAsFixed(2)}',
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyHistory() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.history, size: 64, color: Colors.grey[400]),
          SizedBox(height: 16),
          Text(
            'No Transactions Yet',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Colors.grey[700],
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Your trading history will appear here',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorContent() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
          SizedBox(height: 16),
          Text(
            'Failed to load portfolio',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          SizedBox(height: 8),
          ElevatedButton(
            onPressed: () {
              ref.invalidate(portfolioProvider);
              ref.invalidate(transactionHistoryProvider);
            },
            child: Text('Retry'),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays > 0) {
      return '${difference.inDays} day${difference.inDays == 1 ? '' : 's'} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} hour${difference.inHours == 1 ? '' : 's'} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} minute${difference.inMinutes == 1 ? '' : 's'} ago';
    } else {
      return 'Just now';
    }
  }
}
