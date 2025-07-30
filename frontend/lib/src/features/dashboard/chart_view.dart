import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';

// Popular stocks for selection
const List<String> popularStocks = [
  'AAPL',
  'GOOGL',
  'MSFT',
  'AMZN',
  'TSLA',
  'NVDA',
  'META',
  'NFLX',
];

// Current selected stock provider
final selectedStockProvider = StateProvider<String>((ref) => 'AAPL');

// Stock data provider
final stockDataProvider = FutureProvider.family<List<CandlestickData>, String>((
  ref,
  symbol,
) async {
  final apiService = ref.watch(apiServiceProvider);
  return await apiService.getStockData(symbol);
});

// Current price provider
final currentPriceProvider = StreamProvider.family<double, String>((
  ref,
  symbol,
) {
  final websocketService = ref.watch(websocketServiceProvider);
  return websocketService.priceStream.map((prices) => prices[symbol] ?? 0.0);
});

class ChartView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedStock = ref.watch(selectedStockProvider);
    final stockDataAsync = ref.watch(stockDataProvider(selectedStock));
    final currentPriceAsync = ref.watch(currentPriceProvider(selectedStock));

    return Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          // Stock selector
          _buildStockSelector(context, ref, selectedStock),
          SizedBox(height: 16),

          // Current price display
          currentPriceAsync.when(
            data: (price) => _buildPriceDisplay(selectedStock, price),
            loading: () => SizedBox.shrink(),
            error: (error, stack) => SizedBox.shrink(),
          ),

          SizedBox(height: 16),

          // Chart
          Expanded(
            child: stockDataAsync.when(
              data: (data) => _buildChart(data),
              loading: () => Center(child: CircularProgressIndicator()),
              error: (error, stack) => _buildErrorWidget(error),
            ),
          ),

          SizedBox(height: 16),

          // Trade buttons
          _buildTradeButtons(context, selectedStock),
        ],
      ),
    );
  }

  Widget _buildStockSelector(
    BuildContext context,
    WidgetRef ref,
    String selectedStock,
  ) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Select Stock',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: popularStocks.map((stock) {
                final isSelected = stock == selectedStock;
                return FilterChip(
                  label: Text(stock),
                  selected: isSelected,
                  onSelected: (selected) {
                    if (selected) {
                      ref.read(selectedStockProvider.notifier).state = stock;
                    }
                  },
                  selectedColor: Colors.blue[100],
                  checkmarkColor: Colors.blue[900],
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPriceDisplay(String symbol, double price) {
    final formatter = NumberFormat.currency(symbol: '\$');

    return Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  symbol,
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                Text(
                  'Current Price',
                  style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                ),
              ],
            ),
            Text(
              formatter.format(price),
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.blue[900],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(List<CandlestickData> data) {
    if (data.isEmpty) {
      return Card(
        child: Center(
          child: Padding(
            padding: EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.show_chart, size: 64, color: Colors.grey[400]),
                SizedBox(height: 16),
                Text(
                  'No chart data available',
                  style: TextStyle(fontSize: 16, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Price Chart (Last 30 Days)',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            Expanded(child: LineChart(_buildLineChartData(data))),
          ],
        ),
      ),
    );
  }

  LineChartData _buildLineChartData(List<CandlestickData> data) {
    final spots = data.asMap().entries.map((entry) {
      return FlSpot(entry.key.toDouble(), entry.value.close);
    }).toList();

    final minY = data.map((d) => d.low).reduce((a, b) => a < b ? a : b);
    final maxY = data.map((d) => d.high).reduce((a, b) => a > b ? a : b);
    final padding = (maxY - minY) * 0.1;

    return LineChartData(
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: (maxY - minY) / 5,
        getDrawingHorizontalLine: (value) {
          return FlLine(color: Colors.grey[300], strokeWidth: 1);
        },
      ),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 60,
            getTitlesWidget: (value, meta) {
              return Text(
                '\$${value.toStringAsFixed(0)}',
                style: TextStyle(color: Colors.grey[600], fontSize: 12),
              );
            },
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 30,
            interval: data.length / 5,
            getTitlesWidget: (value, meta) {
              if (value.toInt() >= 0 && value.toInt() < data.length) {
                final date = data[value.toInt()].date;
                return Text(
                  DateFormat('MM/dd').format(date),
                  style: TextStyle(color: Colors.grey[600], fontSize: 12),
                );
              }
              return SizedBox.shrink();
            },
          ),
        ),
        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      borderData: FlBorderData(
        show: true,
        border: Border(
          left: BorderSide(color: Colors.grey[300]!),
          bottom: BorderSide(color: Colors.grey[300]!),
        ),
      ),
      lineBarsData: [
        LineChartBarData(
          spots: spots,
          isCurved: true,
          color: Colors.blue[700],
          barWidth: 3,
          isStrokeCapRound: true,
          dotData: FlDotData(show: false),
          belowBarData: BarAreaData(
            show: true,
            color: Colors.blue[100]!.withValues(alpha: 0.3),
          ),
        ),
      ],
      minY: minY - padding,
      maxY: maxY + padding,
    );
  }

  Widget _buildTradeButtons(BuildContext context, String selectedStock) {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              // TODO: Navigate to buy screen
              _showTradeDialog(context, selectedStock, 'BUY');
            },
            icon: Icon(Icons.trending_up),
            label: Text('BUY'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ),
        SizedBox(width: 16),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              // TODO: Navigate to sell screen
              _showTradeDialog(context, selectedStock, 'SELL');
            },
            icon: Icon(Icons.trending_down),
            label: Text('SELL'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ),
      ],
    );
  }

  void _showTradeDialog(BuildContext context, String symbol, String action) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('$action $symbol'),
        content: Text('Trade functionality will be implemented here.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorWidget(Object error) {
    return Card(
      child: Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: Colors.red),
              SizedBox(height: 16),
              Text(
                'Failed to load chart data',
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
      ),
    );
  }
}

// Candlestick data model
class CandlestickData {
  final DateTime date;
  final double open;
  final double high;
  final double low;
  final double close;
  final int volume;

  CandlestickData({
    required this.date,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
  });

  factory CandlestickData.fromJson(Map<String, dynamic> json) {
    return CandlestickData(
      date: DateTime.fromMillisecondsSinceEpoch(json['timestamp'] * 1000),
      open: json['open'].toDouble(),
      high: json['high'].toDouble(),
      low: json['low'].toDouble(),
      close: json['close'].toDouble(),
      volume: json['volume'],
    );
  }
}
