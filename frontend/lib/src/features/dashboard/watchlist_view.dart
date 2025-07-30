import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/watchlist.dart';
import '../../repositories/watchlist_repository.dart';

final watchlistProvider = FutureProvider<List<WatchlistItem>>((ref) async {
  final repository = ref.watch(watchlistRepositoryProvider);
  return await repository.getWatchlist();
});

class WatchlistView extends ConsumerStatefulWidget {
  @override
  ConsumerState<WatchlistView> createState() => _WatchlistViewState();
}

class _WatchlistViewState extends ConsumerState<WatchlistView> {
  final TextEditingController _searchController = TextEditingController();
  List<Map<String, dynamic>> _searchResults = [];
  bool _isSearching = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _performSearch(String query) async {
    if (query.trim().isEmpty) {
      setState(() {
        _searchResults = [];
        _isSearching = false;
      });
      return;
    }

    setState(() {
      _isSearching = true;
    });

    try {
      final repository = ref.read(watchlistRepositoryProvider);
      final results = await repository.searchStocks(query);
      setState(() {
        _searchResults = results;
        _isSearching = false;
      });
    } catch (e) {
      setState(() {
        _searchResults = [];
        _isSearching = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Search failed: ${e.toString()}')),
      );
    }
  }

  Future<void> _addToWatchlist(Map<String, dynamic> stock) async {
    try {
      final repository = ref.read(watchlistRepositoryProvider);
      await repository.addToWatchlist(
        symbol: stock['symbol'],
        name: stock['name'],
        currentPrice: stock['price']?.toDouble() ?? 0.0,
        dailyChange: stock['change']?.toDouble() ?? 0.0,
        dailyChangePercentage: stock['changePercent']?.toDouble() ?? 0.0,
      );

      // Clear search and refresh watchlist
      _searchController.clear();
      setState(() {
        _searchResults = [];
      });
      ref.invalidate(watchlistProvider);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${stock['symbol']} added to watchlist'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to add to watchlist: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _removeFromWatchlist(String symbol) async {
    try {
      final repository = ref.read(watchlistRepositoryProvider);
      await repository.removeFromWatchlist(symbol);
      ref.invalidate(watchlistProvider);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$symbol removed from watchlist'),
          backgroundColor: Colors.orange,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to remove from watchlist: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final watchlistAsync = ref.watch(watchlistProvider);

    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: Column(
        children: [
          // Search Bar
          Container(
            padding: EdgeInsets.all(16),
            color: Colors.white,
            child: TextField(
              controller: _searchController,
              onChanged: _performSearch,
              decoration: InputDecoration(
                hintText: 'Search stocks to add...',
                prefixIcon: Icon(Icons.search, color: Colors.grey[600]),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {
                            _searchResults = [];
                          });
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.grey[300]!),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.grey[300]!),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.blue[600]!),
                ),
                filled: true,
                fillColor: Colors.grey[50],
              ),
            ),
          ),

          Expanded(
            child: _searchResults.isNotEmpty || _isSearching
                ? _buildSearchResults()
                : _buildWatchlist(watchlistAsync),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchResults() {
    if (_isSearching) {
      return Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
        ),
      );
    }

    if (_searchResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 64, color: Colors.grey[400]),
            SizedBox(height: 16),
            Text(
              'No stocks found',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      );
    }

    return ListView.separated(
      padding: EdgeInsets.all(16),
      itemCount: _searchResults.length,
      separatorBuilder: (context, index) => SizedBox(height: 8),
      itemBuilder: (context, index) {
        final stock = _searchResults[index];
        return _buildSearchResultCard(stock);
      },
    );
  }

  Widget _buildSearchResultCard(Map<String, dynamic> stock) {
    final isPositive = (stock['change'] ?? 0.0) >= 0;
    final color = isPositive ? Colors.green : Colors.red;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: ListTile(
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: Colors.blue[50],
          child: Text(
            stock['symbol'][0],
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.blue[700],
            ),
          ),
        ),
        title: Text(
          stock['symbol'],
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        subtitle: Text(
          stock['name'],
          style: TextStyle(
            color: Colors.grey[600],
            fontSize: 14,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '\$${stock['price'].toStringAsFixed(2)}',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                Text(
                  '${isPositive ? '+' : ''}${stock['changePercent'].toStringAsFixed(2)}%',
                  style: TextStyle(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            SizedBox(width: 8),
            IconButton(
              onPressed: () => _addToWatchlist(stock),
              icon: Icon(Icons.add_circle, color: Colors.blue[600]),
              tooltip: 'Add to watchlist',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWatchlist(AsyncValue<List<WatchlistItem>> watchlistAsync) {
    return watchlistAsync.when(
      data: (watchlist) {
        if (watchlist.isEmpty) {
          return _buildEmptyWatchlist();
        }
        return RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(watchlistProvider);
          },
          child: ListView.separated(
            padding: EdgeInsets.all(16),
            itemCount: watchlist.length,
            separatorBuilder: (context, index) => SizedBox(height: 8),
            itemBuilder: (context, index) {
              final item = watchlist[index];
              return _buildWatchlistCard(item);
            },
          ),
        );
      },
      loading: () => Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation(Colors.blue[600]),
        ),
      ),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
            SizedBox(height: 16),
            Text(
              'Failed to load watchlist',
              style: TextStyle(fontSize: 18, color: Colors.grey[600]),
            ),
            SizedBox(height: 8),
            ElevatedButton(
              onPressed: () => ref.invalidate(watchlistProvider),
              child: Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWatchlistCard(WatchlistItem item) {
    final isPositive = item.dailyChange >= 0;
    final color = isPositive ? Colors.green : Colors.red;

    return Dismissible(
      key: Key(item.symbol),
      background: Container(
        decoration: BoxDecoration(
          color: Colors.red,
          borderRadius: BorderRadius.circular(12),
        ),
        alignment: Alignment.centerRight,
        padding: EdgeInsets.only(right: 20),
        child: Icon(Icons.delete, color: Colors.white),
      ),
      direction: DismissDirection.endToStart,
      onDismissed: (_) => _removeFromWatchlist(item.symbol),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 8,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: ListTile(
          contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          leading: CircleAvatar(
            backgroundColor: Colors.blue[50],
            child: Text(
              item.symbol[0],
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.blue[700],
              ),
            ),
          ),
          title: Text(
            item.symbol,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          subtitle: Text(
            item.name,
            style: TextStyle(
              color: Colors.grey[600],
              fontSize: 14,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '\$${item.currentPrice.toStringAsFixed(2)}',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isPositive ? Icons.arrow_upward : Icons.arrow_downward,
                    color: color,
                    size: 14,
                  ),
                  Text(
                    '${isPositive ? '+' : ''}${item.dailyChangePercentage.toStringAsFixed(2)}%',
                    style: TextStyle(
                      color: color,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyWatchlist() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.visibility_off, size: 64, color: Colors.grey[400]),
          SizedBox(height: 16),
          Text(
            'Your watchlist is empty',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Colors.grey[700],
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Search for stocks to add to your watchlist',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
