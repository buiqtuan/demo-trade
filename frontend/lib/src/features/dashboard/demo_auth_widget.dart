import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../auth/auth_repository.dart';

class DemoAuthWidget extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    final authRepository = ref.watch(authRepositoryProvider);

    return authState.when(
      data: (user) {
        if (user != null) {
          return Container(
            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.green.withOpacity(0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.person, color: Colors.green, size: 16),
                SizedBox(width: 6),
                Text(
                  user.email ?? 'Demo User',
                  style: TextStyle(
                    color: Colors.green[700],
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(width: 8),
                GestureDetector(
                  onTap: () => authRepository.signOut(),
                  child: Icon(Icons.logout, color: Colors.green, size: 16),
                ),
              ],
            ),
          );
        } else {
          return ElevatedButton.icon(
            onPressed: () => _showDemoSignIn(context, ref),
            icon: Icon(Icons.login, size: 16),
            label: Text(
              'Demo Login',
              style: TextStyle(fontSize: 12),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blue[600],
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              minimumSize: Size(0, 32),
            ),
          );
        }
      },
      loading: () => SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      error: (error, stack) => Icon(
        Icons.error,
        color: Colors.red,
        size: 20,
      ),
    );
  }

  void _showDemoSignIn(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Demo Authentication'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Sign in to enable real-time market data and trading features.',
              style: TextStyle(fontSize: 14),
            ),
            SizedBox(height: 16),
            Text(
              'Demo Credentials:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            Text('Email: demo@example.com'),
            Text('Password: demo123'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              await _performDemoSignIn(ref);
            },
            child: Text('Demo Sign In'),
          ),
        ],
      ),
    );
  }

  Future<void> _performDemoSignIn(WidgetRef ref) async {
    try {
      final authRepository = ref.read(authRepositoryProvider);
      await authRepository.signInWithEmail(
        email: 'demo@example.com',
        password: 'demo123',
      );
      print('Demo sign-in successful');
    } catch (e) {
      print('Demo sign-in failed: $e');
      // Create the account if it doesn't exist
      try {
        final authRepository = ref.read(authRepositoryProvider);
        await authRepository.createUserWithEmail(
          email: 'demo@example.com',
          password: 'demo123',
        );
        print('Demo account created and signed in');
      } catch (createError) {
        print('Failed to create demo account: $createError');
      }
    }
  }
}
