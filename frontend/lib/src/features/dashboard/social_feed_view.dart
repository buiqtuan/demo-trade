import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

// Mock data for social feed
final socialFeedProvider = Provider<List<SocialPost>>((ref) {
  return [
    SocialPost(
      id: '1',
      username: 'TradingPro',
      userAvatar: '💼',
      content:
          'Just bought more AAPL shares! The fundamentals look strong for Q4.',
      timestamp: DateTime.now().subtract(Duration(minutes: 30)),
      likes: 23,
      comments: 5,
      symbol: 'AAPL',
    ),
    SocialPost(
      id: '2',
      username: 'MarketWatcher',
      userAvatar: '📈',
      content:
          'Tesla earnings call was impressive. EV market is really heating up!',
      timestamp: DateTime.now().subtract(Duration(hours: 2)),
      likes: 45,
      comments: 12,
      symbol: 'TSLA',
    ),
    SocialPost(
      id: '3',
      username: 'TechInvestor',
      userAvatar: '💻',
      content:
          'Microsoft Azure revenue growth is incredible. Cloud computing is the future.',
      timestamp: DateTime.now().subtract(Duration(hours: 4)),
      likes: 31,
      comments: 8,
      symbol: 'MSFT',
    ),
    SocialPost(
      id: '4',
      username: 'ValueSeeker',
      userAvatar: '💎',
      content:
          'Looking for undervalued stocks in the retail sector. Any suggestions?',
      timestamp: DateTime.now().subtract(Duration(hours: 6)),
      likes: 15,
      comments: 20,
      symbol: null,
    ),
    SocialPost(
      id: '5',
      username: 'DividendKing',
      userAvatar: '👑',
      content:
          'Just received my quarterly dividend from JNJ. Love consistent dividend payers!',
      timestamp: DateTime.now().subtract(Duration(hours: 8)),
      likes: 28,
      comments: 7,
      symbol: 'JNJ',
    ),
  ];
});

class SocialFeedView extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final posts = ref.watch(socialFeedProvider);

    return RefreshIndicator(
      onRefresh: () async {
        // TODO: Implement refresh functionality
        await Future.delayed(Duration(seconds: 1));
      },
      child: ListView.builder(
        padding: EdgeInsets.all(16),
        itemCount: posts.length + 1, // +1 for the header
        itemBuilder: (context, index) {
          if (index == 0) {
            return _buildHeader(context);
          }

          final post = posts[index - 1];
          return _buildPostCard(context, post);
        },
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Column(
      children: [
        Card(
          child: Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.people, color: Colors.blue[900]),
                    SizedBox(width: 8),
                    Text(
                      'Community Feed',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  'Share your trading insights and learn from the community',
                  style: TextStyle(color: Colors.grey[600]),
                ),
                SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _showCreatePostDialog(context),
                    icon: Icon(Icons.add),
                    label: Text('Share a Thought'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue[900],
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        SizedBox(height: 16),
      ],
    );
  }

  Widget _buildPostCard(BuildContext context, SocialPost post) {
    final timeAgo = _getTimeAgo(post.timestamp);

    return Card(
      margin: EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // User info and timestamp
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: Colors.blue[100],
                  child: Text(post.userAvatar, style: TextStyle(fontSize: 20)),
                ),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        post.username,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        timeAgo,
                        style: TextStyle(color: Colors.grey[600], fontSize: 12),
                      ),
                    ],
                  ),
                ),
                if (post.symbol != null)
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.blue[100],
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      post.symbol!,
                      style: TextStyle(
                        color: Colors.blue[900],
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
              ],
            ),

            SizedBox(height: 12),

            // Post content
            Text(post.content, style: TextStyle(fontSize: 15, height: 1.4)),

            SizedBox(height: 16),

            // Actions (like, comment, share)
            Row(
              children: [
                _buildActionButton(
                  icon: Icons.thumb_up_outlined,
                  count: post.likes,
                  onTap: () {
                    // TODO: Implement like functionality
                  },
                ),
                SizedBox(width: 16),
                _buildActionButton(
                  icon: Icons.comment_outlined,
                  count: post.comments,
                  onTap: () {
                    // TODO: Implement comment functionality
                  },
                ),
                SizedBox(width: 16),
                _buildActionButton(
                  icon: Icons.share_outlined,
                  count: null,
                  onTap: () {
                    // TODO: Implement share functionality
                  },
                ),
                Spacer(),
                if (post.symbol != null)
                  TextButton(
                    onPressed: () {
                      // TODO: Navigate to chart view for this symbol
                    },
                    child: Text(
                      'View Chart',
                      style: TextStyle(
                        color: Colors.blue[900],
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required int? count,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 20, color: Colors.grey[600]),
            if (count != null) ...[
              SizedBox(width: 4),
              Text(
                count.toString(),
                style: TextStyle(color: Colors.grey[600], fontSize: 14),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _getTimeAgo(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat('MMM d').format(timestamp);
    }
  }

  void _showCreatePostDialog(BuildContext context) {
    final contentController = TextEditingController();
    final symbolController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Share Your Thoughts'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: contentController,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'What\'s on your mind about the markets?',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 12),
            TextField(
              controller: symbolController,
              decoration: InputDecoration(
                hintText: 'Stock symbol (optional)',
                border: OutlineInputBorder(),
                prefixText: '\$ ',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              // TODO: Implement post creation
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Post shared! (Feature coming soon)'),
                  backgroundColor: Colors.green,
                ),
              );
            },
            child: Text('Share'),
          ),
        ],
      ),
    );
  }
}

// Social post data model
class SocialPost {
  final String id;
  final String username;
  final String userAvatar;
  final String content;
  final DateTime timestamp;
  final int likes;
  final int comments;
  final String? symbol;

  SocialPost({
    required this.id,
    required this.username,
    required this.userAvatar,
    required this.content,
    required this.timestamp,
    required this.likes,
    required this.comments,
    this.symbol,
  });

  factory SocialPost.fromJson(Map<String, dynamic> json) {
    return SocialPost(
      id: json['id'],
      username: json['username'],
      userAvatar: json['user_avatar'],
      content: json['content'],
      timestamp: DateTime.parse(json['timestamp']),
      likes: json['likes'],
      comments: json['comments'],
      symbol: json['symbol'],
    );
  }
}
