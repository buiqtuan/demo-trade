import 'package:hive/hive.dart';

part 'watchlist.g.dart';

@HiveType(typeId: 4)
class WatchlistItem {
  @HiveField(0)
  final String symbol;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final DateTime addedAt;

  @HiveField(3)
  final double currentPrice;

  @HiveField(4)
  final double dailyChange;

  @HiveField(5)
  final double dailyChangePercentage;

  WatchlistItem({
    required this.symbol,
    required this.name,
    required this.addedAt,
    this.currentPrice = 0.0,
    this.dailyChange = 0.0,
    this.dailyChangePercentage = 0.0,
  });

  factory WatchlistItem.fromJson(Map<String, dynamic> json) {
    return WatchlistItem(
      symbol: json['symbol'],
      name: json['name'],
      addedAt: DateTime.parse(json['added_at']),
      currentPrice: json['current_price']?.toDouble() ?? 0.0,
      dailyChange: json['daily_change']?.toDouble() ?? 0.0,
      dailyChangePercentage: json['daily_change_percentage']?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'name': name,
      'added_at': addedAt.toIso8601String(),
      'current_price': currentPrice,
      'daily_change': dailyChange,
      'daily_change_percentage': dailyChangePercentage,
    };
  }

  WatchlistItem copyWith({
    String? symbol,
    String? name,
    DateTime? addedAt,
    double? currentPrice,
    double? dailyChange,
    double? dailyChangePercentage,
  }) {
    return WatchlistItem(
      symbol: symbol ?? this.symbol,
      name: name ?? this.name,
      addedAt: addedAt ?? this.addedAt,
      currentPrice: currentPrice ?? this.currentPrice,
      dailyChange: dailyChange ?? this.dailyChange,
      dailyChangePercentage:
          dailyChangePercentage ?? this.dailyChangePercentage,
    );
  }
}
