// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'watchlist.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class WatchlistItemAdapter extends TypeAdapter<WatchlistItem> {
  @override
  final int typeId = 4;

  @override
  WatchlistItem read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return WatchlistItem(
      symbol: fields[0] as String,
      name: fields[1] as String,
      addedAt: fields[2] as DateTime,
      currentPrice: fields[3] as double,
      dailyChange: fields[4] as double,
      dailyChangePercentage: fields[5] as double,
    );
  }

  @override
  void write(BinaryWriter writer, WatchlistItem obj) {
    writer
      ..writeByte(6)
      ..writeByte(0)
      ..write(obj.symbol)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.addedAt)
      ..writeByte(3)
      ..write(obj.currentPrice)
      ..writeByte(4)
      ..write(obj.dailyChange)
      ..writeByte(5)
      ..write(obj.dailyChangePercentage);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is WatchlistItemAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
