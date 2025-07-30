// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'market_index.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class MarketIndexAdapter extends TypeAdapter<MarketIndex> {
  @override
  final int typeId = 5;

  @override
  MarketIndex read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return MarketIndex(
      symbol: fields[0] as String,
      name: fields[1] as String,
      currentValue: fields[2] as double,
      dailyChange: fields[3] as double,
      dailyChangePercentage: fields[4] as double,
      lastUpdated: fields[5] as DateTime,
    );
  }

  @override
  void write(BinaryWriter writer, MarketIndex obj) {
    writer
      ..writeByte(6)
      ..writeByte(0)
      ..write(obj.symbol)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.currentValue)
      ..writeByte(3)
      ..write(obj.dailyChange)
      ..writeByte(4)
      ..write(obj.dailyChangePercentage)
      ..writeByte(5)
      ..write(obj.lastUpdated);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MarketIndexAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
