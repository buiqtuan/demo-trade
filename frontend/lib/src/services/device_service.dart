import 'dart:async';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final deviceServiceProvider = Provider<DeviceService>((ref) {
  return DeviceService();
});

/// Service responsible for managing anonymous user identification
/// and device-specific settings using SharedPreferences
class DeviceService {
  static const String _userIdKey = 'anonymous_user_id';
  static const String _firstLaunchKey = 'is_first_launch';

  final Uuid _uuid = const Uuid();
  String? _cachedUserId;

  /// Get or create an anonymous user ID
  /// This ID persists across app launches and serves as the local user identifier
  Future<String> getUserId() async {
    if (_cachedUserId != null) {
      return _cachedUserId!;
    }

    final prefs = await SharedPreferences.getInstance();
    String? userId = prefs.getString(_userIdKey);

    if (userId == null) {
      // First time user - generate new UUID
      userId = _uuid.v4();
      await prefs.setString(_userIdKey, userId);
      await prefs.setBool(_firstLaunchKey, true);
    }

    _cachedUserId = userId;
    return userId;
  }

  /// Check if this is the first app launch
  Future<bool> isFirstLaunch() async {
    final prefs = await SharedPreferences.getInstance();
    final isFirst = prefs.getBool(_firstLaunchKey) ?? true;

    if (isFirst) {
      // Mark as no longer first launch
      await prefs.setBool(_firstLaunchKey, false);
    }

    return isFirst;
  }

  /// Clear all device data (useful for testing or reset functionality)
  Future<void> clearDeviceData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    _cachedUserId = null;
  }

  /// Get a shorter, display-friendly version of the user ID
  Future<String> getDisplayUserId() async {
    final userId = await getUserId();
    // Return first 8 characters of UUID for display
    return userId.substring(0, 8);
  }
}
