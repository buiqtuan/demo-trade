import 'package:hive/hive.dart';

part 'portfolio.g.dart';

@HiveType(typeId: 0)
class Portfolio {
  @HiveField(0)
  final String userId;

  @HiveField(1)
  final double cashBalance;

  @HiveField(2)
  final double initialBalance;

  @HiveField(3)
  final List<Holding> holdings;

  Portfolio({
    required this.userId,
    required this.cashBalance,
    required this.initialBalance,
    required this.holdings,
  });

  factory Portfolio.fromJson(Map<String, dynamic> json) {
    return Portfolio(
      userId: json['user_id'],
      cashBalance: json['cash_balance'].toDouble(),
      initialBalance: json['initial_balance'].toDouble(),
      holdings:
          (json['holdings'] as List).map((h) => Holding.fromJson(h)).toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'cash_balance': cashBalance,
      'initial_balance': initialBalance,
      'holdings': holdings.map((h) => h.toJson()).toList(),
    };
  }

  /// Calculate total portfolio value
  double get totalValue {
    final holdingsValue = holdings.fold<double>(
        0, (sum, holding) => sum + (holding.quantity * holding.currentPrice));
    return cashBalance + holdingsValue;
  }

  /// Calculate total profit/loss
  double get totalProfitLoss {
    return totalValue - initialBalance;
  }

  /// Calculate total profit/loss percentage
  double get totalProfitLossPercentage {
    if (initialBalance == 0) return 0;
    return (totalProfitLoss / initialBalance) * 100;
  }

  Portfolio copyWith({
    String? userId,
    double? cashBalance,
    double? initialBalance,
    List<Holding>? holdings,
  }) {
    return Portfolio(
      userId: userId ?? this.userId,
      cashBalance: cashBalance ?? this.cashBalance,
      initialBalance: initialBalance ?? this.initialBalance,
      holdings: holdings ?? this.holdings,
    );
  }
}

@HiveType(typeId: 1)
class Holding {
  @HiveField(0)
  final String symbol;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final double quantity;

  @HiveField(3)
  final double averageCostBasis;

  @HiveField(4)
  final double currentPrice;

  Holding({
    required this.symbol,
    required this.name,
    required this.quantity,
    required this.averageCostBasis,
    this.currentPrice = 0.0,
  });

  factory Holding.fromJson(Map<String, dynamic> json) {
    return Holding(
      symbol: json['symbol'],
      name: json['name'],
      quantity: json['quantity'].toDouble(),
      averageCostBasis: json['average_cost_basis'].toDouble(),
      currentPrice: json['current_price']?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'name': name,
      'quantity': quantity,
      'average_cost_basis': averageCostBasis,
      'current_price': currentPrice,
    };
  }

  /// Calculate total value of this holding
  double get totalValue => quantity * currentPrice;

  /// Calculate profit/loss for this holding
  double get profitLoss => (currentPrice - averageCostBasis) * quantity;

  /// Calculate profit/loss percentage for this holding
  double get profitLossPercentage {
    if (averageCostBasis == 0) return 0;
    return ((currentPrice - averageCostBasis) / averageCostBasis) * 100;
  }

  Holding copyWith({
    String? symbol,
    String? name,
    double? quantity,
    double? averageCostBasis,
    double? currentPrice,
  }) {
    return Holding(
      symbol: symbol ?? this.symbol,
      name: name ?? this.name,
      quantity: quantity ?? this.quantity,
      averageCostBasis: averageCostBasis ?? this.averageCostBasis,
      currentPrice: currentPrice ?? this.currentPrice,
    );
  }
}
