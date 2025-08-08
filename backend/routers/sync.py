from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
import logging

from database import get_db
from dependencies import get_current_user
from schemas import (
    SyncMigrateRequest, 
    SyncMigrateResponse, 
    PortfolioCreate, 
    AssetCreate,
    HoldingCreate, 
    TransactionCreate,
    WatchlistCreate
)
import crud

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/migrate", response_model=SyncMigrateResponse)
async def migrate_local_data(
    sync_request: SyncMigrateRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Migrate local data from anonymous user to authenticated Firebase user.
    This endpoint is called after successful login to sync local data to the server.
    """
    try:
        # Verify that the current user matches the Firebase user in the request
        if current_user != sync_request.firebase_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID mismatch - can only migrate your own data"
            )
        
        # User MUST already exist (should be created during registration)
        user = crud.get_user(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please complete registration first by calling /api/auth/register"
            )
        
        migrated_items: Dict[str, int] = {
            "portfolio": 0,
            "holdings": 0,
            "transactions": 0,
            "watchlist": 0
        }

        # 1. Migrate Portfolio Data
        if sync_request.data.portfolio:
            portfolio_data = sync_request.data.portfolio
            
            # Portfolio should already exist from registration
            portfolio = crud.get_portfolio_by_user_id(db, current_user)
            if not portfolio:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User portfolio not found. Please contact support - this should not happen for registered users."
                )
            
            # Update existing portfolio with migrated data
            crud.update_portfolio(db, portfolio.portfolio_id, 
                                cash_balance=portfolio_data.cash_balance,
                                initial_balance=portfolio_data.initial_balance)
            logger.info(f"Updated portfolio for user {current_user}")
            
            migrated_items["portfolio"] = 1

        # Get the user's portfolio for subsequent operations
        portfolio = crud.get_portfolio_by_user_id(db, current_user)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve user portfolio"
            )

        # 2. Migrate Holdings
        for holding_data in sync_request.data.holdings:
            try:
                # Get or create asset
                asset = crud.get_asset_by_symbol(db, holding_data.symbol)
                if not asset:
                    asset_create = AssetCreate(
                        symbol=holding_data.symbol,
                        name=holding_data.name,
                        asset_type="STOCK"
                    )
                    asset = crud.create_asset(db, asset_create)

                # Check if holding already exists
                existing_holding = crud.get_holding_by_portfolio_and_asset(
                    db, portfolio.portfolio_id, asset.asset_id
                )
                
                if existing_holding:
                    # Update existing holding (use the local data as it's more recent)
                    crud.update_holding(db, existing_holding.holding_id,
                                      quantity=holding_data.quantity,
                                      average_cost_basis=holding_data.average_cost_basis,
                                      total_cost=holding_data.quantity * holding_data.average_cost_basis)
                else:
                    # Create new holding
                    holding_create = HoldingCreate(
                        portfolio_id=portfolio.portfolio_id,
                        asset_id=asset.asset_id,
                        quantity=holding_data.quantity,
                        average_cost_basis=holding_data.average_cost_basis,
                        total_cost=holding_data.quantity * holding_data.average_cost_basis
                    )
                    crud.create_holding(db, holding_create)
                
                migrated_items["holdings"] += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate holding {holding_data.symbol}: {e}")
                # Continue with other holdings

        # 3. Migrate Transactions
        for transaction_data in sync_request.data.transactions:
            try:
                # Get or create asset
                asset = crud.get_asset_by_symbol(db, transaction_data.symbol)
                if not asset:
                    asset_create = AssetCreate(
                        symbol=transaction_data.symbol,
                        name=transaction_data.symbol,  # Use symbol as name if not available
                        asset_type="STOCK"
                    )
                    asset = crud.create_asset(db, asset_create)

                # Check if transaction already exists (using the UUID from frontend)
                existing_transaction = crud.get_transaction_by_external_id(db, transaction_data.id)
                if not existing_transaction:
                    # Convert transaction type from frontend format ('buy'/'sell') to backend format ('BUY'/'SELL')
                    transaction_type = transaction_data.type.upper()
                    
                    transaction_create = TransactionCreate(
                        portfolio_id=portfolio.portfolio_id,
                        asset_id=asset.asset_id,
                        transaction_type=transaction_type,
                        quantity=transaction_data.quantity,
                        price_per_unit=transaction_data.price,
                        total_amount=transaction_data.total_value,
                        fees=Decimal("0.00"),
                        market_price_at_execution=transaction_data.price,
                        execution_notes=f"Migrated from local data - Original ID: {transaction_data.id}"
                    )
                    crud.create_transaction(db, transaction_create)
                    migrated_items["transactions"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to migrate transaction {transaction_data.id}: {e}")
                # Continue with other transactions

        # 4. Migrate Watchlist
        for watchlist_data in sync_request.data.watchlist:
            try:
                # Get or create asset
                asset = crud.get_asset_by_symbol(db, watchlist_data.symbol)
                if not asset:
                    asset_create = AssetCreate(
                        symbol=watchlist_data.symbol,
                        name=watchlist_data.name,
                        asset_type="STOCK"
                    )
                    asset = crud.create_asset(db, asset_create)

                # Check if watchlist item already exists
                existing_watchlist = crud.get_watchlist_item(db, current_user, asset.asset_id)
                if not existing_watchlist:
                    watchlist_create = WatchlistCreate(
                        user_id=current_user,
                        asset_id=asset.asset_id,
                        notes=f"Added on {watchlist_data.added_at.strftime('%Y-%m-%d')}"
                    )
                    crud.create_watchlist_item(db, watchlist_create)
                    migrated_items["watchlist"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to migrate watchlist item {watchlist_data.symbol}: {e}")
                # Continue with other watchlist items

        # Log successful migration
        total_migrated = sum(migrated_items.values())
        logger.info(f"Successfully migrated {total_migrated} items for user {current_user}: {migrated_items}")

        return SyncMigrateResponse(
            success=True,
            message=f"Successfully migrated {total_migrated} items to your account",
            migrated_items=migrated_items,
            user_id=current_user,
            migration_timestamp=datetime.now()
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Migration failed for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )

@router.get("/status")
async def get_sync_status(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the sync status for the current user.
    Returns information about the user's data in the cloud.
    """
    try:
        user = crud.get_user(db, current_user)
        if not user:
            return {
                "has_cloud_data": False,
                "message": "No cloud data found for this user"
            }

        portfolio = crud.get_portfolio_by_user_id(db, current_user)
        holdings_count = len(crud.get_holdings_by_portfolio_id(db, portfolio.portfolio_id)) if portfolio else 0
        transactions_count = len(crud.get_transactions_by_portfolio_id(db, portfolio.portfolio_id)) if portfolio else 0
        watchlist_count = len(crud.get_watchlist_by_user_id(db, current_user))

        return {
            "has_cloud_data": True,
            "user_id": current_user,
            "data_summary": {
                "portfolio": 1 if portfolio else 0,
                "holdings": holdings_count,
                "transactions": transactions_count,
                "watchlist": watchlist_count
            },
            "last_updated": portfolio.updated_at if portfolio else None
        }

    except Exception as e:
        logger.error(f"Failed to get sync status for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync status"
        )