import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../models/portfolio.dart';

// Providers for portfolio data (Legacy - use PortfolioRepository instead)
final portfolioProvider = FutureProvider<Portfolio>((ref) async {
  final apiService = ref.watch(apiServiceProvider);
  final portfolio = await apiService.getPortfolio();
  return portfolio;
});

final realTimePricesProvider = StreamProvider<Map<String, double>>((ref) {
  final websocketService = ref.watch(websocketServiceProvider);
  return websocketService.priceStream;
});

class PortfolioView extends ConsumerWidget {
  final NumberFormat currencyFormat = NumberFormat.currency(symbol: '\$');
  final NumberFormat percentFormat = NumberFormat.percentPattern();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final portfolioAsync = ref.watch(portfolioProvider);
    final realTimePricesAsync = ref.watch(realTimePricesProvider);

    return RefreshIndicator(
      onRefresh: () => ref.refresh(portfolioProvider.future),
      child: portfolioAsync.when(
        data: (portfolio) => _buildPortfolioContent(
          context,
          portfolio,
          realTimePricesAsync.asData?.value ?? {},
        ),
        loading: () => Center(child: CircularProgressIndicator()),
        error: (error, stack) => _buildErrorWidget(error),
      ),
    );
  }

  Widget _buildPortfolioContent(
    BuildContext context,
    Portfolio portfolio,
    Map<String, double> realTimePrices,
  ) {
    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Portfolio Summary Card
          _buildSummaryCard(portfolio, realTimePrices),
          SizedBox(height: 16),

          // Holdings Section
          _buildHoldingsSection(portfolio.holdings, realTimePrices),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(
    Portfolio portfolio,
    Map<String, double> realTimePrices,
  ) {
    double totalValue = portfolio.cashBalance;
    double totalGainLoss = 0;

    // Calculate current portfolio value including real-time prices
    for (final holding in portfolio.holdings) {
      final currentPrice =
          realTimePrices[holding.symbol] ?? holding.averageCostBasis;
      final currentValue = holding.quantity * currentPrice;
      final costBasis = holding.quantity * holding.averageCostBasis;

      totalValue += currentValue;
      totalGainLoss += (currentValue - costBasis);
    }

    final totalGainLossPercent = portfolio.initialBalance > 0
        ? totalGainLoss / portfolio.initialBalance
        : 0.0;

    return Card(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Portfolio Value',
              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            ),
            SizedBox(height: 8),
            Text(
              currencyFormat.format(totalValue),
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: Colors.blue[900],
              ),
            ),
            SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildSummaryItem(
                    'Cash Balance',
                    currencyFormat.format(portfolio.cashBalance),
                    Colors.green,
                  ),
                ),
                Expanded(
                  child: _buildSummaryItem(
                    'Total Gain/Loss',
                    '${currencyFormat.format(totalGainLoss)} (${percentFormat.format(totalGainLossPercent)})',
                    totalGainLoss >= 0 ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
        SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildHoldingsSection(
    List<Holding> holdings,
    Map<String, double> realTimePrices,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Holdings',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            TextButton.icon(
              onPressed: () {
                // TODO: Navigate to trade screen
              },
              icon: Icon(Icons.add),
              label: Text('Trade'),
            ),
          ],
        ),
        SizedBox(height: 12),
        if (holdings.isEmpty)
          Card(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.trending_up, size: 48, color: Colors.grey[400]),
                    SizedBox(height: 16),
                    Text(
                      'No holdings yet',
                      style: TextStyle(fontSize: 16, color: Colors.grey[600]),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Start trading to see your positions here',
                      style: TextStyle(fontSize: 14, color: Colors.grey[500]),
                    ),
                  ],
                ),
              ),
            ),
          )
        else
          ...holdings.map(
            (holding) => _buildHoldingCard(holding, realTimePrices),
          ),
      ],
    );
  }

  Widget _buildHoldingCard(
    Holding holding,
    Map<String, double> realTimePrices,
  ) {
    final currentPrice =
        realTimePrices[holding.symbol] ?? holding.averageCostBasis;
    final currentValue = holding.quantity * currentPrice;
    final costBasis = holding.quantity * holding.averageCostBasis;
    final gainLoss = currentValue - costBasis;
    final gainLossPercent = costBasis > 0 ? gainLoss / costBasis : 0.0;

    return Card(
      margin: EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            // Symbol and name
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    holding.symbol,
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    holding.name,
                    style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                  ),
                ],
              ),
            ),

            // Quantity and average cost
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    '${holding.quantity.toStringAsFixed(2)} shares',
                    style: TextStyle(fontSize: 12),
                  ),
                  Text(
                    'Avg: ${currencyFormat.format(holding.averageCostBasis)}',
                    style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                  ),
                ],
              ),
            ),

            // Current value and P&L
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    currencyFormat.format(currentValue),
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    '${currencyFormat.format(gainLoss)} (${percentFormat.format(gainLossPercent)})',
                    style: TextStyle(
                      fontSize: 11,
                      color: gainLoss >= 0 ? Colors.green : Colors.red,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorWidget(Object error) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red),
            SizedBox(height: 16),
            Text(
              'Failed to load portfolio',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Text(
              error.toString(),
              style: TextStyle(color: Colors.grey[600]),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
