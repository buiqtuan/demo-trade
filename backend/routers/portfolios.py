from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from database import get_db
from dependencies import get_current_user, FirebaseUser, check_user_permission
from schemas import (
    PortfolioSummary, HoldingResponse, UserStatsResponse, 
    LeaderboardResponse, LeaderboardEntry, UserCreate, UserResponse
)
import crud

router = APIRouter()

@router.get("/portfolios/{user_id}", response_model=PortfolioSummary)
async def get_portfolio(
    user_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's complete portfolio information including:
    - Cash balance and initial balance
    - All holdings with current values
    - Total portfolio value and returns
    """
    try:
        # Check permission - users can only access their own portfolio
        check_user_permission(current_user.uid, user_id)
        
        # Get user's portfolio
        portfolio = crud.get_user_portfolio(db, user_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        # Get holdings with asset information
        holdings_response = []
        for holding in portfolio.holdings:
            holdings_response.append(HoldingResponse(
                holding_id=holding.holding_id,
                portfolio_id=holding.portfolio_id,
                asset_id=holding.asset_id,
                quantity=holding.quantity,
                average_cost_basis=holding.average_cost_basis,
                total_cost=holding.total_cost,
                symbol=holding.asset.symbol,
                name=holding.asset.name,
                created_at=holding.created_at,
                updated_at=holding.updated_at
            ))
        
        # Calculate total portfolio value (cash + holdings at cost basis)
        total_holdings_value = sum(holding.total_cost for holding in portfolio.holdings)
        total_portfolio_value = portfolio.cash_balance + total_holdings_value
        
        # Calculate returns
        total_return = total_portfolio_value - portfolio.initial_balance
        total_return_percentage = (total_return / portfolio.initial_balance * 100) if portfolio.initial_balance > 0 else 0
        
        return PortfolioSummary(
            user_id=portfolio.user_id,
            cash_balance=portfolio.cash_balance,
            initial_balance=portfolio.initial_balance,
            total_portfolio_value=total_portfolio_value,
            total_return=total_return,
            total_return_percentage=total_return_percentage,
            holdings=holdings_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching portfolio data"
        )

@router.get("/users/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's trading statistics including:
    - Total trades, win/loss counts
    - Win rate percentage
    - Total returns and portfolio performance
    - Current rank and streaks
    """
    try:
        # Check permission - users can only access their own stats
        check_user_permission(current_user.uid, user_id)
        
        # Get user stats
        stats = crud.get_user_stats(db, user_id)
        if not stats:
            # Create initial stats if they don't exist
            stats = crud.create_user_stats(db, user_id)
        
        # Get current rank
        current_rank = crud.get_user_rank(db, user_id)
        
        return UserStatsResponse(
            stats_id=stats.stats_id,
            user_id=stats.user_id,
            total_trades=stats.total_trades,
            winning_trades=stats.winning_trades,
            losing_trades=stats.losing_trades,
            total_return=stats.total_return,
            total_return_percentage=stats.total_return_percentage,
            win_rate=stats.win_rate,
            max_drawdown=stats.max_drawdown,
            current_rank=current_rank,
            best_rank=stats.best_rank,
            streak_days=stats.streak_days,
            last_trade_date=stats.last_trade_date,
            created_at=stats.created_at,
            updated_at=stats.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user statistics"
        )

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = 100,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get trading leaderboard showing top performing users.
    
    Returns users ranked by portfolio performance (total return percentage).
    """
    try:
        # Get leaderboard data
        leaderboard_data = crud.get_leaderboard(db, limit)
        
        # Convert to response format
        entries = []
        for entry in leaderboard_data:
            entries.append(LeaderboardEntry(
                rank=entry["rank"],
                user_id=entry["user_id"],
                username=entry["username"],
                total_return_percentage=Decimal(str(entry["total_return_percentage"])),
                portfolio_value=Decimal(str(entry["portfolio_value"])),
                win_rate=entry["win_rate"],
                total_trades=entry["total_trades"]
            ))
        
        # Get current user's rank
        user_rank = crud.get_user_rank(db, current_user.uid)
        
        return LeaderboardResponse(
            entries=entries,
            total_users=len(entries),
            user_rank=user_rank
        )
        
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching leaderboard data"
        )

@router.get("/users/{user_id}/rank")
async def get_user_rank(
    user_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current rank in the leaderboard.
    """
    try:
        # Check permission
        check_user_permission(current_user.uid, user_id)
        
        rank = crud.get_user_rank(db, user_id)
        if rank is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User rank not found. User may not have any trades yet."
            )
        
        return {"rank": rank}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user rank: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user rank"
        )

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user_data: UserCreate,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user account in the database.
    
    This should be called after successful Firebase Auth registration
    to create the user's profile and initial portfolio.
    """
    try:
        # Verify that the current user is creating their own account
        if current_user.uid != user_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create your own account"
            )
        
        # Check if user already exists
        existing_user = crud.get_user(db, user_data.user_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User account already exists"
            )
        
        # Check if email or username is already taken
        if crud.get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered"
            )
        
        if crud.get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken"
            )
        
        # Create the user account
        new_user = crud.create_user(db, user_data)
        
        return UserResponse(
            user_id=new_user.user_id,
            email=new_user.email,
            username=new_user.username,
            created_at=new_user.created_at,
            is_active=new_user.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user account"
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user profile information.
    
    Users can only access their own profile for privacy.
    """
    try:
        # Check permission
        check_user_permission(current_user.uid, user_id)
        
        # Get user
        user = crud.get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            created_at=user.created_at,
            is_active=user.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile"
        )

@router.get("/portfolios/{user_id}/value")
async def get_portfolio_value(
    user_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current total portfolio value.
    
    Useful for quick checks without fetching full portfolio data.
    """
    try:
        # Check permission
        check_user_permission(current_user.uid, user_id)
        
        # Get portfolio
        portfolio = crud.get_user_portfolio(db, user_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        # Calculate total value
        total_value = crud.calculate_portfolio_value(db, portfolio.portfolio_id)
        
        return {
            "user_id": user_id,
            "cash_balance": float(portfolio.cash_balance),
            "total_portfolio_value": float(total_value),
            "initial_balance": float(portfolio.initial_balance),
            "total_return": float(total_value - portfolio.initial_balance),
            "total_return_percentage": float((total_value - portfolio.initial_balance) / portfolio.initial_balance * 100) if portfolio.initial_balance > 0 else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error calculating portfolio value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating portfolio value"
        ) 