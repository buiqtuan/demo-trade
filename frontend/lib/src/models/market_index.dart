import 'package:hive/hive.dart';

part 'market_index.g.dart';

@HiveType(typeId: 5)
class MarketIndex {
  @HiveField(0)
  final String symbol;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final double currentValue;

  @HiveField(3)
  final double dailyChange;

  @HiveField(4)
  final double dailyChangePercentage;

  @HiveField(5)
  final DateTime lastUpdated;

  MarketIndex({
    required this.symbol,
    required this.name,
    required this.currentValue,
    required this.dailyChange,
    required this.dailyChangePercentage,
    required this.lastUpdated,
  });

  factory MarketIndex.fromJson(Map<String, dynamic> json) {
    return MarketIndex(
      symbol: json['symbol'],
      name: json['name'],
      currentValue: json['current_value'].toDouble(),
      dailyChange: json['daily_change'].toDouble(),
      dailyChangePercentage: json['daily_change_percentage'].toDouble(),
      lastUpdated: DateTime.parse(json['last_updated']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'name': name,
      'current_value': currentValue,
      'daily_change': dailyChange,
      'daily_change_percentage': dailyChangePercentage,
      'last_updated': lastUpdated.toIso8601String(),
    };
  }

  /// Whether the index is up (positive change)
  bool get isPositive => dailyChange >= 0;

  MarketIndex copyWith({
    String? symbol,
    String? name,
    double? currentValue,
    double? dailyChange,
    double? dailyChangePercentage,
    DateTime? lastUpdated,
  }) {
    return MarketIndex(
      symbol: symbol ?? this.symbol,
      name: name ?? this.name,
      currentValue: currentValue ?? this.currentValue,
      dailyChange: dailyChange ?? this.dailyChange,
      dailyChangePercentage:
          dailyChangePercentage ?? this.dailyChangePercentage,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }
}
