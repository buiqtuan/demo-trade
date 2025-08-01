import 'package:hive/hive.dart';

part 'transaction.g.dart';

@HiveType(typeId: 2)
class Transaction {
  @HiveField(0)
  final String id;

  @HiveField(1)
  final String userId;

  @HiveField(2)
  final String symbol;

  @HiveField(3)
  final TransactionType type;

  @HiveField(4)
  final double quantity;

  @HiveField(5)
  final double price;

  @HiveField(6)
  final DateTime timestamp;

  @HiveField(7)
  final double totalValue;

  Transaction({
    required this.id,
    required this.userId,
    required this.symbol,
    required this.type,
    required this.quantity,
    required this.price,
    required this.timestamp,
    required this.totalValue,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['id'],
      userId: json['user_id'],
      symbol: json['symbol'],
      type: TransactionType.values.firstWhere(
        (t) => t.name.toUpperCase() == json['type'].toString().toUpperCase(),
        orElse: () => TransactionType.BUY,
      ),
      quantity: json['quantity'].toDouble(),
      price: json['price'].toDouble(),
      timestamp: DateTime.parse(json['timestamp']),
      totalValue: json['total_value'].toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'symbol': symbol,
      'type': type.name,
      'quantity': quantity,
      'price': price,
      'timestamp': timestamp.toIso8601String(),
      'total_value': totalValue,
    };
  }
}

@HiveType(typeId: 3)
enum TransactionType {
  @HiveField(0)
  BUY,

  @HiveField(1)
  SELL,
}
