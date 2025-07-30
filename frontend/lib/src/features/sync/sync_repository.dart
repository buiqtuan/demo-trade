import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/local_db_service.dart';
import '../../services/device_service.dart';
import '../../repositories/portfolio_repository.dart';
import '../../repositories/watchlist_repository.dart';
import '../auth/auth_repository.dart';

final syncRepositoryProvider = Provider<SyncRepository>((ref) {
  final localDb = ref.watch(localDbServiceProvider);
  final deviceService = ref.watch(deviceServiceProvider);
  final authRepository = ref.watch(authRepositoryProvider);
  final portfolioRepository = ref.watch(portfolioRepositoryProvider);
  final watchlistRepository = ref.watch(watchlistRepositoryProvider);

  return SyncRepository(
    localDb,
    deviceService,
    authRepository,
    portfolioRepository,
    watchlistRepository,
  );
});

class SyncRepository {
  final LocalDbService _localDb;
  final DeviceService _deviceService;
  final AuthRepository _authRepository;
  final PortfolioRepository _portfolioRepository;
  final WatchlistRepository _watchlistRepository;

  // TODO: Update this URL to match your backend
  static const String _baseUrl = 'http://localhost:8000';

  SyncRepository(
    this._localDb,
    this._deviceService,
    this._authRepository,
    this._portfolioRepository,
    this._watchlistRepository,
  );

  /// Check if user has local data that can be synced
  Future<bool> hasLocalDataToSync() async {
    final userId = await _deviceService.getUserId();
    return await _localDb.hasUserData(userId);
  }

  /// Get a summary of local data for display to user
  Future<Map<String, int>> getLocalDataSummary() async {
    final userId = await _deviceService.getUserId();

    final portfolio = await _localDb.getPortfolio(userId);
    final holdings = await _localDb.getHoldings(userId);
    final transactions = await _localDb.getTransactions(userId);
    final watchlist = await _localDb.getWatchlist(userId);

    return {
      'portfolios': portfolio != null ? 1 : 0,
      'holdings': holdings.length,
      'transactions': transactions.length,
      'watchlist': watchlist.length,
    };
  }

  /// Sync local data to server after successful authentication
  Future<SyncResult> syncLocalDataToServer() async {
    try {
      // Ensure user is authenticated
      final user = _authRepository.currentUser;
      if (user == null) {
        throw Exception('User must be authenticated before syncing');
      }

      // Get authentication headers
      final idToken = await _authRepository.getIdToken();
      if (idToken == null) {
        throw Exception('Failed to get authentication token');
      }

      // Collect all local data
      final userId = await _deviceService.getUserId();
      final localData = await _localDb.getAllUserData(userId);

      // Prepare sync payload
      final syncPayload = {
        'anonymous_user_id': userId,
        'firebase_user_id': user.uid,
        'sync_timestamp': DateTime.now().toIso8601String(),
        'data': localData,
      };

      // Send to backend
      final response = await http.post(
        Uri.parse('$_baseUrl/sync/migrate'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
        body: json.encode(syncPayload),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Sync successful - switch repositories to remote mode
        _portfolioRepository.switchToRemoteMode();
        _watchlistRepository.switchToRemoteMode();

        // Optionally clear local data after successful sync
        // await _localDb.clearAllData();

        return SyncResult(
          success: true,
          message: 'Data synced successfully',
          syncedItemsCount: _calculateSyncedItems(localData),
        );
      } else {
        final errorBody = json.decode(response.body);
        throw Exception(
            'Sync failed: ${errorBody['detail'] ?? 'Unknown error'}');
      }
    } catch (e) {
      return SyncResult(
        success: false,
        message: 'Sync failed: ${e.toString()}',
        syncedItemsCount: 0,
      );
    }
  }

  /// Manually switch to remote mode (for users who sign in without local data)
  Future<void> switchToRemoteMode() async {
    _portfolioRepository.switchToRemoteMode();
    _watchlistRepository.switchToRemoteMode();
  }

  /// Switch back to local mode (for sign out)
  Future<void> switchToLocalMode() async {
    _portfolioRepository.switchToLocalMode();
    _watchlistRepository.switchToLocalMode();
  }

  /// Download data from server to local storage (for restoring on new device)
  Future<SyncResult> downloadDataFromServer() async {
    try {
      // Ensure user is authenticated
      final user = _authRepository.currentUser;
      if (user == null) {
        throw Exception('User must be authenticated to download data');
      }

      // Get authentication headers
      final idToken = await _authRepository.getIdToken();
      if (idToken == null) {
        throw Exception('Failed to get authentication token');
      }

      // TODO: Implement download endpoint on backend
      // For now, this is a placeholder
      final response = await http.get(
        Uri.parse('$_baseUrl/sync/download'),
        headers: {
          'Authorization': 'Bearer $idToken',
        },
      );

      if (response.statusCode == 200) {
        // TODO: Parse and save server data to local storage
        // This would involve parsing the server response and saving to Hive

        return SyncResult(
          success: true,
          message: 'Data downloaded successfully',
          syncedItemsCount: 0, // TODO: Calculate based on downloaded data
        );
      } else {
        throw Exception('Download failed: ${response.statusCode}');
      }
    } catch (e) {
      return SyncResult(
        success: false,
        message: 'Download failed: ${e.toString()}',
        syncedItemsCount: 0,
      );
    }
  }

  /// Calculate total number of items being synced
  int _calculateSyncedItems(Map<String, dynamic> localData) {
    int count = 0;

    if (localData['portfolio'] != null) count += 1;
    if (localData['holdings'] is List)
      count += (localData['holdings'] as List).length;
    if (localData['transactions'] is List)
      count += (localData['transactions'] as List).length;
    if (localData['watchlist'] is List)
      count += (localData['watchlist'] as List).length;

    return count;
  }

  /// Get current sync status
  Future<SyncStatus> getSyncStatus() async {
    final hasLocalData = await hasLocalDataToSync();
    final isAuthenticated = _authRepository.currentUser != null;
    final isInRemoteMode = _portfolioRepository.currentMode == DataMode.remote;

    if (!isAuthenticated) {
      return SyncStatus.notSignedIn;
    } else if (isInRemoteMode) {
      return SyncStatus.synced;
    } else if (hasLocalData) {
      return SyncStatus.localDataPending;
    } else {
      return SyncStatus.noLocalData;
    }
  }
}

class SyncResult {
  final bool success;
  final String message;
  final int syncedItemsCount;

  SyncResult({
    required this.success,
    required this.message,
    required this.syncedItemsCount,
  });
}

enum SyncStatus {
  notSignedIn,
  localDataPending,
  synced,
  noLocalData,
}

// Extension to get user-friendly status messages
extension SyncStatusExtension on SyncStatus {
  String get displayMessage {
    switch (this) {
      case SyncStatus.notSignedIn:
        return 'Sign in to sync your data';
      case SyncStatus.localDataPending:
        return 'Local data ready to sync';
      case SyncStatus.synced:
        return 'Data synced with cloud';
      case SyncStatus.noLocalData:
        return 'No local data to sync';
    }
  }
}
