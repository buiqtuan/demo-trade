import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/local_db_service.dart';
import 'markets_view.dart';
import 'watchlist_view.dart';
import 'portfolio_view_new.dart';
import 'profile_view.dart';

class HomeScreen extends ConsumerStatefulWidget {
  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 0;
  late PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _initializeLocalDatabase();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _initializeLocalDatabase() async {
    try {
      final localDb = ref.read(localDbServiceProvider);
      await localDb.openBoxes();
    } catch (e) {
      // Handle initialization error
      print('Failed to initialize local database: $e');
    }
  }

  final List<Widget> _pages = [
    MarketsView(),
    WatchlistView(),
    PortfolioViewNew(),
    ProfileView(),
  ];

  final List<BottomNavigationBarItem> _bottomNavItems = [
    BottomNavigationBarItem(
      icon: Icon(Icons.trending_up),
      activeIcon: Icon(Icons.trending_up),
      label: 'Home',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.visibility_outlined),
      activeIcon: Icon(Icons.visibility),
      label: 'Watchlist',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.account_balance_wallet_outlined),
      activeIcon: Icon(Icons.account_balance_wallet),
      label: 'Portfolio',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.person_outline),
      activeIcon: Icon(Icons.person),
      label: 'Profile',
    ),
  ];

  void _onTabTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
    _pageController.jumpToPage(index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_getPageTitle()),
        backgroundColor: Colors.white,
        foregroundColor: Colors.grey[800],
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
          color: Colors.grey[800],
        ),
      ),
      body: PageView(
        controller: _pageController,
        onPageChanged: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        children: _pages,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: Offset(0, -2),
            ),
          ],
        ),
        child: BottomNavigationBar(
          type: BottomNavigationBarType.fixed,
          currentIndex: _selectedIndex,
          selectedItemColor: Colors.blue[700],
          unselectedItemColor: Colors.grey[500],
          selectedFontSize: 12,
          unselectedFontSize: 12,
          backgroundColor: Colors.white,
          elevation: 0,
          onTap: _onTabTapped,
          items: _bottomNavItems,
          selectedLabelStyle: TextStyle(
            fontWeight: FontWeight.w600,
          ),
          unselectedLabelStyle: TextStyle(
            fontWeight: FontWeight.normal,
          ),
        ),
      ),
    );
  }

  String _getPageTitle() {
    switch (_selectedIndex) {
      case 0:
        return 'Markets';
      case 1:
        return 'Watchlist';
      case 2:
        return 'Portfolio';
      case 3:
        return 'Profile';
      default:
        return 'Trading Simulator';
    }
  }
}
