from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from models import User, Portfolio, Asset, Holding, Transaction, UserStats, Watchlist, MarketData
from schemas import UserCreate, PortfolioCreate, AssetCreate, HoldingCreate, TransactionCreate, WatchlistCreate

# User CRUD operations
def get_user(db: Session, user_id: str) -> Optional[User]:
    """Get user by Firebase UID"""
    return db.query(User).filter(User.user_id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate) -> User:
    """Create new user"""
    db_user = User(
        user_id=user.user_id,
        email=user.email,
        username=user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create initial portfolio for the user
    create_portfolio(db, PortfolioCreate(
        user_id=user.user_id,
        cash_balance=Decimal("100000.00"),
        initial_balance=Decimal("100000.00")
    ))
    
    # Create initial user stats
    create_user_stats(db, user.user_id)
    
    return db_user

def update_user(db: Session, user_id: str, **kwargs) -> Optional[User]:
    """Update user information"""
    db_user = get_user(db, user_id)
    if db_user:
        for key, value in kwargs.items():
            setattr(db_user, key, value)
        db_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_user)
    return db_user

# Portfolio CRUD operations
def get_portfolio_by_user_id(db: Session, user_id: str) -> Optional[Portfolio]:
    """Get portfolio by user ID"""
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).first()

def get_user_portfolio(db: Session, user_id: str) -> Optional[Portfolio]:
    """Get user's portfolio with holdings"""
    return db.query(Portfolio).options(
        joinedload(Portfolio.holdings).joinedload(Holding.asset)
    ).filter(Portfolio.user_id == user_id).first()

def create_portfolio(db: Session, portfolio: PortfolioCreate) -> Portfolio:
    """Create new portfolio"""
    db_portfolio = Portfolio(**portfolio.dict())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def update_portfolio_cash(db: Session, portfolio_id: int, new_balance: Decimal) -> Portfolio:
    """Update portfolio cash balance"""
    db_portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if db_portfolio:
        db_portfolio.cash_balance = new_balance
        db.commit()
        db.refresh(db_portfolio)
    return db_portfolio

def update_portfolio(db: Session, portfolio_id: int, **kwargs) -> Optional[Portfolio]:
    """Update portfolio information"""
    db_portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if db_portfolio:
        for key, value in kwargs.items():
            setattr(db_portfolio, key, value)
        db_portfolio.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_portfolio)
    return db_portfolio

# Asset CRUD operations
def get_asset_by_symbol(db: Session, symbol: str) -> Optional[Asset]:
    """Get asset by symbol"""
    return db.query(Asset).filter(Asset.symbol == symbol.upper()).first()

def get_asset(db: Session, asset_id: int) -> Optional[Asset]:
    """Get asset by ID"""
    return db.query(Asset).filter(Asset.asset_id == asset_id).first()

def create_asset(db: Session, asset: AssetCreate) -> Asset:
    """Create new asset"""
    db_asset = Asset(**asset.dict())
    db_asset.symbol = db_asset.symbol.upper()
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

def get_or_create_asset(db: Session, symbol: str, name: str = None) -> Asset:
    """Get existing asset or create new one"""
    asset = get_asset_by_symbol(db, symbol)
    if not asset:
        asset = create_asset(db, AssetCreate(
            symbol=symbol.upper(),
            name=name or symbol.upper(),
            asset_type="STOCK"
        ))
    return asset

def search_assets(db: Session, query: str, limit: int = 10) -> List[Asset]:
    """Search assets by symbol or name"""
    return db.query(Asset).filter(
        (Asset.symbol.ilike(f"%{query.upper()}%")) |
        (Asset.name.ilike(f"%{query}%"))
    ).filter(Asset.is_active == True).limit(limit).all()

# Holding CRUD operations
def get_holdings_by_portfolio_id(db: Session, portfolio_id: int) -> List[Holding]:
    """Get all holdings by portfolio ID"""
    return db.query(Holding).options(
        joinedload(Holding.asset)
    ).filter(Holding.portfolio_id == portfolio_id).all()

def get_holding_by_portfolio_and_asset(db: Session, portfolio_id: int, asset_id: int) -> Optional[Holding]:
    """Get holding by portfolio and asset"""
    return db.query(Holding).filter(
        and_(Holding.portfolio_id == portfolio_id, Holding.asset_id == asset_id)
    ).first()

def get_user_holdings(db: Session, portfolio_id: int) -> List[Holding]:
    """Get all holdings for a portfolio"""
    return db.query(Holding).options(
        joinedload(Holding.asset)
    ).filter(Holding.portfolio_id == portfolio_id).all()

def get_holding(db: Session, portfolio_id: int, asset_id: int) -> Optional[Holding]:
    """Get specific holding"""
    return db.query(Holding).filter(
        and_(Holding.portfolio_id == portfolio_id, Holding.asset_id == asset_id)
    ).first()

def create_holding(db: Session, holding: HoldingCreate) -> Holding:
    """Create new holding"""
    db_holding = Holding(**holding.dict())
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    return db_holding

def update_holding(db: Session, holding_id: int, quantity: Decimal, 
                  average_cost_basis: Decimal, total_cost: Decimal) -> Optional[Holding]:
    """Update holding details"""
    db_holding = db.query(Holding).filter(Holding.holding_id == holding_id).first()
    if db_holding:
        db_holding.quantity = quantity
        db_holding.average_cost_basis = average_cost_basis
        db_holding.total_cost = total_cost
        db.commit()
        db.refresh(db_holding)
    return db_holding

def delete_holding(db: Session, holding_id: int) -> bool:
    """Delete holding if quantity is 0"""
    db_holding = db.query(Holding).filter(Holding.holding_id == holding_id).first()
    if db_holding and db_holding.quantity == 0:
        db.delete(db_holding)
        db.commit()
        return True
    return False

# Transaction CRUD operations
def get_transactions_by_portfolio_id(db: Session, portfolio_id: int) -> List[Transaction]:
    """Get all transactions by portfolio ID"""
    return db.query(Transaction).options(
        joinedload(Transaction.asset)
    ).filter(Transaction.portfolio_id == portfolio_id).all()

def get_transaction_by_external_id(db: Session, external_id: str) -> Optional[Transaction]:
    """Get transaction by external ID (from execution_notes)"""
    return db.query(Transaction).filter(
        Transaction.execution_notes.contains(f"Original ID: {external_id}")
    ).first()

def create_transaction(db: Session, transaction: TransactionCreate) -> Transaction:
    """Create new transaction"""
    db_transaction = Transaction(**transaction.dict())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_user_transactions(db: Session, portfolio_id: int, limit: int = 50) -> List[Transaction]:
    """Get user's recent transactions"""
    return db.query(Transaction).options(
        joinedload(Transaction.asset)
    ).filter(Transaction.portfolio_id == portfolio_id)\
     .order_by(desc(Transaction.timestamp)).limit(limit).all()

def get_transaction(db: Session, transaction_id: int) -> Optional[Transaction]:
    """Get transaction by ID"""
    return db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()

# Trading logic functions
def execute_buy_trade(db: Session, portfolio_id: int, asset_id: int, 
                     quantity: Decimal, price: Decimal) -> dict:
    """Execute buy trade with perfect execution logic"""
    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")
    
    total_cost = quantity * price
    
    # Check if user has enough cash
    if portfolio.cash_balance < total_cost:
        raise ValueError("Insufficient cash balance")
    
    # Update cash balance
    portfolio.cash_balance -= total_cost
    
    # Get or create holding
    holding = get_holding(db, portfolio_id, asset_id)
    
    if holding:
        # Update existing holding with new average cost basis
        new_quantity = holding.quantity + quantity
        new_total_cost = holding.total_cost + total_cost
        new_avg_cost = new_total_cost / new_quantity
        
        update_holding(db, holding.holding_id, new_quantity, new_avg_cost, new_total_cost)
    else:
        # Create new holding
        create_holding(db, HoldingCreate(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            quantity=quantity,
            average_cost_basis=price,
            total_cost=total_cost
        ))
    
    # Create transaction record
    transaction = create_transaction(db, TransactionCreate(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        transaction_type="BUY",
        quantity=quantity,
        price_per_unit=price,
        total_amount=total_cost,
        market_price_at_execution=price
    ))
    
    # Update user stats
    update_user_stats_after_trade(db, portfolio.user_id, "BUY", quantity, price)
    
    return {
        "transaction_id": transaction.transaction_id,
        "new_cash_balance": portfolio.cash_balance,
        "message": f"Successfully bought {quantity} shares"
    }

def execute_sell_trade(db: Session, portfolio_id: int, asset_id: int, 
                      quantity: Decimal, price: Decimal) -> dict:
    """Execute sell trade with perfect execution logic"""
    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")
    
    # Get existing holding
    holding = get_holding(db, portfolio_id, asset_id)
    if not holding or holding.quantity < quantity:
        raise ValueError("Insufficient shares to sell")
    
    total_proceeds = quantity * price
    
    # Update cash balance
    portfolio.cash_balance += total_proceeds
    
    # Update holding
    new_quantity = holding.quantity - quantity
    if new_quantity == 0:
        # Delete holding if no shares left
        delete_holding(db, holding.holding_id)
    else:
        # Update holding quantity (cost basis remains same)
        new_total_cost = holding.average_cost_basis * new_quantity
        update_holding(db, holding.holding_id, new_quantity, 
                      holding.average_cost_basis, new_total_cost)
    
    # Create transaction record
    transaction = create_transaction(db, TransactionCreate(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        transaction_type="SELL",
        quantity=quantity,
        price_per_unit=price,
        total_amount=total_proceeds,
        market_price_at_execution=price
    ))
    
    # Determine if this was a winning or losing trade
    cost_basis_per_share = holding.average_cost_basis
    profit_per_share = price - cost_basis_per_share
    is_winning_trade = profit_per_share > 0
    
    # Update user stats
    update_user_stats_after_trade(db, portfolio.user_id, "SELL", quantity, price, 
                                 is_winning_trade=is_winning_trade)
    
    return {
        "transaction_id": transaction.transaction_id,
        "new_cash_balance": portfolio.cash_balance,
        "profit_loss": profit_per_share * quantity,
        "message": f"Successfully sold {quantity} shares"
    }

# User Stats CRUD operations
def get_user_stats(db: Session, user_id: str) -> Optional[UserStats]:
    """Get user statistics"""
    return db.query(UserStats).filter(UserStats.user_id == user_id).first()

def create_user_stats(db: Session, user_id: str) -> UserStats:
    """Create initial user stats"""
    db_stats = UserStats(user_id=user_id)
    db.add(db_stats)
    db.commit()
    db.refresh(db_stats)
    return db_stats

def update_user_stats_after_trade(db: Session, user_id: str, trade_type: str, 
                                 quantity: Decimal, price: Decimal, 
                                 is_winning_trade: bool = None) -> UserStats:
    """Update user statistics after a trade"""
    stats = get_user_stats(db, user_id)
    if not stats:
        stats = create_user_stats(db, user_id)
    
    if trade_type == "BUY":
        stats.total_trades += 1
    elif trade_type == "SELL" and is_winning_trade is not None:
        if is_winning_trade:
            stats.winning_trades += 1
        else:
            stats.losing_trades += 1
    
    stats.last_trade_date = datetime.utcnow()
    
    # Calculate portfolio performance
    portfolio = get_user_portfolio(db, user_id)
    if portfolio:
        total_value = calculate_portfolio_value(db, portfolio.portfolio_id)
        stats.total_return = total_value - portfolio.initial_balance
        if portfolio.initial_balance > 0:
            stats.total_return_percentage = (stats.total_return / portfolio.initial_balance) * 100
    
    db.commit()
    db.refresh(stats)
    return stats

def calculate_portfolio_value(db: Session, portfolio_id: int, current_prices: dict = None) -> Decimal:
    """Calculate total portfolio value including cash and holdings"""
    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        return Decimal("0.00")
    
    total_value = portfolio.cash_balance
    
    holdings = get_user_holdings(db, portfolio_id)
    for holding in holdings:
        # Use current price if provided, otherwise use cost basis
        current_price = current_prices.get(holding.asset.symbol, holding.average_cost_basis) if current_prices else holding.average_cost_basis
        total_value += holding.quantity * Decimal(str(current_price))
    
    return total_value

# Leaderboard functions
def get_leaderboard(db: Session, limit: int = 100) -> List[dict]:
    """Get leaderboard data"""
    # This is a complex query that ranks users by portfolio performance
    query = db.query(
        User.user_id,
        User.username,
        UserStats.total_return_percentage,
        UserStats.total_trades,
        UserStats.winning_trades,
        UserStats.losing_trades,
        Portfolio.cash_balance,
        Portfolio.initial_balance
    ).join(UserStats, User.user_id == UserStats.user_id)\
     .join(Portfolio, User.user_id == Portfolio.user_id)\
     .filter(UserStats.total_trades > 0)\
     .order_by(desc(UserStats.total_return_percentage))\
     .limit(limit)
    
    results = []
    for rank, row in enumerate(query.all(), 1):
        win_rate = (row.winning_trades / row.total_trades * 100) if row.total_trades > 0 else 0
        portfolio_value = row.cash_balance + (row.initial_balance * (1 + row.total_return_percentage / 100))
        
        results.append({
            "rank": rank,
            "user_id": row.user_id,
            "username": row.username,
            "total_return_percentage": float(row.total_return_percentage),
            "portfolio_value": float(portfolio_value),
            "win_rate": win_rate,
            "total_trades": row.total_trades
        })
    
    return results

def get_user_rank(db: Session, user_id: str) -> Optional[int]:
    """Get user's current rank"""
    leaderboard = get_leaderboard(db, limit=1000)
    for entry in leaderboard:
        if entry["user_id"] == user_id:
            return entry["rank"]
    return None

# Watchlist CRUD operations
def get_watchlist_by_user_id(db: Session, user_id: str) -> List[Watchlist]:
    """Get watchlist by user ID"""
    return db.query(Watchlist).options(
        joinedload(Watchlist.asset)
    ).filter(Watchlist.user_id == user_id).all()

def get_watchlist_item(db: Session, user_id: str, asset_id: int) -> Optional[Watchlist]:
    """Get specific watchlist item"""
    return db.query(Watchlist).filter(
        and_(Watchlist.user_id == user_id, Watchlist.asset_id == asset_id)
    ).first()

def create_watchlist_item(db: Session, watchlist_create) -> Watchlist:
    """Create watchlist item"""
    db_watchlist = Watchlist(
        user_id=watchlist_create.user_id,
        asset_id=watchlist_create.asset_id,
        notes=watchlist_create.notes
    )
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist

def get_user_watchlist(db: Session, user_id: str) -> List[Watchlist]:
    """Get user's watchlist"""
    return db.query(Watchlist).options(
        joinedload(Watchlist.asset)
    ).filter(Watchlist.user_id == user_id).all()

def add_to_watchlist(db: Session, user_id: str, asset_id: int, notes: str = None) -> Watchlist:
    """Add asset to watchlist"""
    # Check if already in watchlist
    existing = db.query(Watchlist).filter(
        and_(Watchlist.user_id == user_id, Watchlist.asset_id == asset_id)
    ).first()
    
    if existing:
        return existing
    
    db_watchlist = Watchlist(
        user_id=user_id,
        asset_id=asset_id,
        notes=notes
    )
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist

def remove_from_watchlist(db: Session, user_id: str, asset_id: int) -> bool:
    """Remove asset from watchlist"""
    watchlist_item = db.query(Watchlist).filter(
        and_(Watchlist.user_id == user_id, Watchlist.asset_id == asset_id)
    ).first()
    
    if watchlist_item:
        db.delete(watchlist_item)
        db.commit()
        return True
    return False 