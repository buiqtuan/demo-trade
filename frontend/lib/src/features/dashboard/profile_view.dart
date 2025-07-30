import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/device_service.dart';
import '../auth/auth_repository.dart';
import '../sync/sync_repository.dart';

final userProfileProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final deviceService = ref.watch(deviceServiceProvider);
  final authRepository = ref.watch(authRepositoryProvider);
  final syncRepository = ref.watch(syncRepositoryProvider);

  final anonymousUserId = await deviceService.getUserId();
  final displayUserId = await deviceService.getDisplayUserId();
  final user = authRepository.currentUser;
  final syncStatus = await syncRepository.getSyncStatus();
  final hasLocalData = await syncRepository.hasLocalDataToSync();
  final localDataSummary = await syncRepository.getLocalDataSummary();

  return {
    'anonymousUserId': anonymousUserId,
    'displayUserId': displayUserId,
    'firebaseUser': user,
    'syncStatus': syncStatus,
    'hasLocalData': hasLocalData,
    'localDataSummary': localDataSummary,
  };
});

class ProfileView extends ConsumerStatefulWidget {
  @override
  ConsumerState<ProfileView> createState() => _ProfileViewState();
}

class _ProfileViewState extends ConsumerState<ProfileView> {
  bool _isSyncing = false;

  Future<void> _signInAndSync() async {
    try {
      setState(() {
        _isSyncing = true;
      });

      // Sign in with Google
      final authRepository = ref.read(authRepositoryProvider);
      final result = await authRepository.signInWithGoogle();

      if (result != null && result.user != null) {
        // Check if user has local data to sync
        final syncRepository = ref.read(syncRepositoryProvider);
        final hasLocalData = await syncRepository.hasLocalDataToSync();

        if (hasLocalData) {
          // Show sync confirmation dialog
          final shouldSync = await _showSyncConfirmationDialog();
          if (shouldSync == true) {
            final syncResult = await syncRepository.syncLocalDataToServer();

            if (syncResult.success) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                      'Successfully synced ${syncResult.syncedItemsCount} items to cloud'),
                  backgroundColor: Colors.green,
                ),
              );
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Sync failed: ${syncResult.message}'),
                  backgroundColor: Colors.red,
                ),
              );
            }
          } else {
            // User chose not to sync, just switch to remote mode
            await syncRepository.switchToRemoteMode();
          }
        } else {
          // No local data, just switch to remote mode
          await syncRepository.switchToRemoteMode();
        }

        // Refresh profile data
        ref.invalidate(userProfileProvider);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Sign in failed: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        _isSyncing = false;
      });
    }
  }

  Future<bool?> _showSyncConfirmationDialog() async {
    final localDataSummary =
        await ref.read(syncRepositoryProvider).getLocalDataSummary();

    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Sync Local Data?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('You have local data that can be synced to the cloud:'),
            SizedBox(height: 12),
            if (localDataSummary['portfolios']! > 0)
              Text('• Portfolio: ${localDataSummary['portfolios']} item'),
            if (localDataSummary['holdings']! > 0)
              Text('• Holdings: ${localDataSummary['holdings']} items'),
            if (localDataSummary['transactions']! > 0)
              Text('• Transactions: ${localDataSummary['transactions']} items'),
            if (localDataSummary['watchlist']! > 0)
              Text('• Watchlist: ${localDataSummary['watchlist']} items'),
            SizedBox(height: 12),
            Text(
              'This will upload your data to the cloud and link it to your account.',
              style: TextStyle(color: Colors.grey[600]),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('Skip Sync'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text('Sync Data'),
          ),
        ],
      ),
    );
  }

  Future<void> _signOut() async {
    try {
      final authRepository = ref.read(authRepositoryProvider);
      final syncRepository = ref.read(syncRepositoryProvider);

      await authRepository.signOut();
      await syncRepository.switchToLocalMode();

      ref.invalidate(userProfileProvider);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Signed out successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Sign out failed: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(userProfileProvider);

    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: profileAsync.when(
        data: (profile) => _buildProfileContent(profile),
        loading: () => Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
          ),
        ),
        error: (error, stack) => _buildErrorContent(),
      ),
    );
  }

  Widget _buildProfileContent(Map<String, dynamic> profile) {
    final firebaseUser = profile['firebaseUser'];
    final isSignedIn = firebaseUser != null;
    final syncStatus = profile['syncStatus'] as SyncStatus;

    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          // User Avatar and Info
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 50,
                  backgroundColor: Colors.blue[100],
                  backgroundImage: isSignedIn && firebaseUser.photoURL != null
                      ? NetworkImage(firebaseUser.photoURL!)
                      : null,
                  child: !isSignedIn || firebaseUser.photoURL == null
                      ? Icon(
                          Icons.person,
                          size: 50,
                          color: Colors.blue[600],
                        )
                      : null,
                ),
                SizedBox(height: 16),
                Text(
                  isSignedIn
                      ? (firebaseUser.displayName ?? 'User')
                      : 'Anonymous User',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Colors.grey[800],
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  isSignedIn
                      ? (firebaseUser.email ?? 'No email')
                      : 'ID: ${profile['displayUserId']}',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.grey[600],
                  ),
                ),
                SizedBox(height: 16),
                _buildSyncStatusChip(syncStatus),
              ],
            ),
          ),

          SizedBox(height: 24),

          // Sign In / Sync Section
          if (!isSignedIn) ...[
            _buildSignInSection(profile),
            SizedBox(height: 24),
          ],

          // Local Data Summary
          if (profile['hasLocalData'] == true) ...[
            _buildLocalDataSection(profile['localDataSummary']),
            SizedBox(height: 24),
          ],

          // Account Actions
          _buildAccountActionsSection(isSignedIn),

          SizedBox(height: 24),

          // App Info
          _buildAppInfoSection(),
        ],
      ),
    );
  }

  Widget _buildSyncStatusChip(SyncStatus status) {
    Color color;
    IconData icon;

    switch (status) {
      case SyncStatus.synced:
        color = Colors.green;
        icon = Icons.cloud_done;
        break;
      case SyncStatus.localDataPending:
        color = Colors.orange;
        icon = Icons.cloud_upload;
        break;
      case SyncStatus.notSignedIn:
        color = Colors.grey;
        icon = Icons.cloud_off;
        break;
      case SyncStatus.noLocalData:
        color = Colors.blue;
        icon = Icons.cloud;
        break;
    }

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 16),
          SizedBox(width: 6),
          Text(
            status.displayMessage,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSignInSection(Map<String, dynamic> profile) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.blue[600]!, Colors.blue[800]!],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.blue.withOpacity(0.3),
            blurRadius: 15,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(
            Icons.cloud_sync,
            size: 48,
            color: Colors.white,
          ),
          SizedBox(height: 16),
          Text(
            'Sign In to Sync & Backup Your Data',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 8),
          Text(
            'Keep your portfolio safe and access it from any device',
            style: TextStyle(
              fontSize: 14,
              color: Colors.white70,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: _isSyncing ? null : _signInAndSync,
            icon: _isSyncing
                ? SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
                    ),
                  )
                : Icon(Icons.login),
            label: Text(_isSyncing ? 'Signing In...' : 'Sign In with Google'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: Colors.blue[700],
              padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLocalDataSection(Map<String, int> summary) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.storage, color: Colors.blue[600]),
              SizedBox(width: 8),
              Text(
                'Local Data',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[800],
                ),
              ),
            ],
          ),
          SizedBox(height: 16),
          ...summary.entries.map((entry) {
            if (entry.value > 0) {
              return Padding(
                padding: EdgeInsets.only(bottom: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      entry.key.toUpperCase(),
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 14,
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.blue[50],
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${entry.value}',
                        style: TextStyle(
                          color: Colors.blue[700],
                          fontWeight: FontWeight.w600,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }
            return SizedBox.shrink();
          }).toList(),
        ],
      ),
    );
  }

  Widget _buildAccountActionsSection(bool isSignedIn) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Account Actions',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.grey[800],
            ),
          ),
          SizedBox(height: 16),
          if (isSignedIn) ...[
            ListTile(
              leading: Icon(Icons.logout, color: Colors.red[600]),
              title: Text('Sign Out'),
              subtitle: Text('Switch back to local-only mode'),
              onTap: _signOut,
              contentPadding: EdgeInsets.zero,
            ),
          ],
          ListTile(
            leading: Icon(Icons.info, color: Colors.blue[600]),
            title: Text('About'),
            subtitle: Text('App version and information'),
            onTap: () {
              showAboutDialog(
                context: context,
                applicationName: 'Trading Simulator',
                applicationVersion: '1.0.0',
                applicationIcon: Icon(Icons.show_chart, size: 48),
                children: [
                  Text(
                      'A local-first trading simulator with optional cloud sync.'),
                ],
              );
            },
            contentPadding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }

  Widget _buildAppInfoSection() {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(Icons.show_chart, size: 48, color: Colors.blue[600]),
          SizedBox(height: 12),
          Text(
            'Trading Simulator',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.grey[800],
            ),
          ),
          SizedBox(height: 4),
          Text(
            'Local-first with cloud sync',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Version 1.0.0',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorContent() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
          SizedBox(height: 16),
          Text(
            'Failed to load profile',
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          SizedBox(height: 8),
          ElevatedButton(
            onPressed: () => ref.invalidate(userProfileProvider),
            child: Text('Retry'),
          ),
        ],
      ),
    );
  }
}
