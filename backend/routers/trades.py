from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import os
from decimal import Decimal
import logging

from database import get_db
from dependencies import get_current_user, FirebaseUser, check_user_permission
from schemas import TradeRequest, TradeResponse, TransactionResponse, APIResponse
from services.market_data_client import market_data_client, MarketDataValidationError, MarketDataConnectionError
import crud

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade_request: TradeRequest,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a trade (buy or sell) with perfect execution logic.
    
    - Gets current market price from Market Data Aggregator
    - Executes trade at market price
    - Updates user's portfolio and holdings
    - Records transaction in database
    """
    try:
        # Input validation
        if not trade_request.ticker or not trade_request.ticker.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticker symbol cannot be empty"
            )
        
        if trade_request.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than 0"
            )
        
        # Normalize ticker symbol
        normalized_ticker = trade_request.ticker.strip().upper()
        
        # Get user's portfolio
        portfolio = crud.get_user_portfolio(db, current_user.uid)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found. Please create an account first."
            )
        
        # Get or create the asset
        asset = crud.get_or_create_asset(
            db, 
            symbol=normalized_ticker,
            name=normalized_ticker  # Will be updated with real name if available
        )
        
        # Get current market price from Market Data Aggregator
        try:
            quote = await market_data_client.get_quote(normalized_ticker)
            if quote and quote.price > 0:
                current_price = Decimal(str(quote.price))
                logger.info(f"Got price for {normalized_ticker}: ${current_price} from {quote.source}")
            else:
                # Fallback to mock price if no data available
                raise Exception("No price data from market data aggregator")
        except MarketDataValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ticker symbol: {str(e)}"
            )
        except MarketDataConnectionError as e:
            logger.error(f"Market data service unavailable: {e}")
            # Use mock price for development/testing
            import random
            current_price = Decimal(str(round(random.uniform(50, 500), 2)))
            logger.warning(f"Using mock price for {normalized_ticker}: ${current_price}")
        except Exception as e:
            logger.error(f"Error fetching price from market data aggregator: {e}")
            # Use mock price for development/testing
            import random
            current_price = Decimal(str(round(random.uniform(50, 500), 2)))
            logger.warning(f"Using mock price for {normalized_ticker}: ${current_price}")
        
        # Execute the trade based on action
        if trade_request.action.upper() == "BUY":
            result = crud.execute_buy_trade(
                db=db,
                portfolio_id=portfolio.portfolio_id,
                asset_id=asset.asset_id,
                quantity=trade_request.quantity,
                price=current_price
            )
        elif trade_request.action.upper() == "SELL":
            result = crud.execute_sell_trade(
                db=db,
                portfolio_id=portfolio.portfolio_id,
                asset_id=asset.asset_id,
                quantity=trade_request.quantity,
                price=current_price
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Must be 'BUY' or 'SELL'"
            )
        
        # Calculate total portfolio value
        total_portfolio_value = crud.calculate_portfolio_value(db, portfolio.portfolio_id)
        
        return TradeResponse(
            message=result["message"],
            transaction_id=result["transaction_id"],
            execution_price=current_price,
            total_amount=trade_request.quantity * current_price,
            new_cash_balance=result["new_cash_balance"],
            total_portfolio_value=total_portfolio_value,
            symbol=normalized_ticker,
            quantity=trade_request.quantity,
            action=trade_request.action.upper()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error executing trade: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during trade execution"
        )

@router.get("/history", response_model=List[TransactionResponse])
async def get_trade_history(
    limit: int = 50,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's trading history.
    
    Returns a list of recent transactions ordered by timestamp (newest first).
    """
    try:
        # Get user's portfolio
        portfolio = crud.get_user_portfolio(db, current_user.uid)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        # Get transactions
        transactions = crud.get_user_transactions(db, portfolio.portfolio_id, limit)
        
        # Convert to response format
        response_transactions = []
        for transaction in transactions:
            response_transactions.append(TransactionResponse(
                transaction_id=transaction.transaction_id,
                portfolio_id=transaction.portfolio_id,
                asset_id=transaction.asset_id,
                transaction_type=transaction.transaction_type,
                quantity=transaction.quantity,
                price_per_unit=transaction.price_per_unit,
                total_amount=transaction.total_amount,
                fees=transaction.fees,
                timestamp=transaction.timestamp,
                symbol=transaction.asset.symbol,
                name=transaction.asset.name,
                market_price_at_execution=transaction.market_price_at_execution,
                execution_notes=transaction.execution_notes
            ))
        
        return response_transactions
        
    except Exception as e:
        print(f"Error fetching trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching trade history"
        )

@router.get("/transaction/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_details(
    transaction_id: int,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific transaction.
    
    Users can only access their own transactions.
    """
    try:
        # Get transaction
        transaction = crud.get_transaction(db, transaction_id)
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        # Check if user owns this transaction
        portfolio = crud.get_user_portfolio(db, current_user.uid)
        if not portfolio or transaction.portfolio_id != portfolio.portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this transaction"
            )
        
        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            portfolio_id=transaction.portfolio_id,
            asset_id=transaction.asset_id,
            transaction_type=transaction.transaction_type,
            quantity=transaction.quantity,
            price_per_unit=transaction.price_per_unit,
            total_amount=transaction.total_amount,
            fees=transaction.fees,
            timestamp=transaction.timestamp,
            symbol=transaction.asset.symbol,
            name=transaction.asset.name,
            market_price_at_execution=transaction.market_price_at_execution,
            execution_notes=transaction.execution_notes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching transaction details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching transaction details"
        )

@router.get("/validate", response_model=APIResponse)
async def validate_trade(
    ticker: str,
    quantity: float,
    action: str,
    current_user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate if a trade can be executed without actually executing it.
    
    Useful for frontend validation before submitting the actual trade.
    """
    try:
        # Input validation
        if not ticker or not ticker.strip():
            return APIResponse(
                success=False,
                message="Ticker symbol cannot be empty"
            )
        
        # Normalize ticker symbol
        normalized_ticker = ticker.strip().upper()
        
        # Basic validation
        if action.upper() not in ["BUY", "SELL"]:
            return APIResponse(
                success=False,
                message="Invalid action. Must be 'BUY' or 'SELL'"
            )
        
        if quantity <= 0:
            return APIResponse(
                success=False,
                message="Quantity must be greater than 0"
            )
        
        # Get user's portfolio
        portfolio = crud.get_user_portfolio(db, current_user.uid)
        if not portfolio:
            return APIResponse(
                success=False,
                message="Portfolio not found"
            )
        
        # Get current price from Market Data Aggregator
        try:
            quote = await market_data_client.get_quote(normalized_ticker)
            if quote and quote.price > 0:
                current_price = Decimal(str(quote.price))
            else:
                current_price = Decimal("100.00")  # Mock price
        except MarketDataValidationError as e:
            return APIResponse(
                success=False,
                message=f"Invalid ticker symbol: {str(e)}"
            )
        except (MarketDataConnectionError, Exception):
            current_price = Decimal("100.00")  # Mock price
        
        if action.upper() == "BUY":
            total_cost = Decimal(str(quantity)) * current_price
            if portfolio.cash_balance < total_cost:
                return APIResponse(
                    success=False,
                    message=f"Insufficient cash. Required: ${total_cost}, Available: ${portfolio.cash_balance}"
                )
        elif action.upper() == "SELL":
            # Check if user has enough shares
            asset = crud.get_asset_by_symbol(db, normalized_ticker)
            if asset:
                holding = crud.get_holding(db, portfolio.portfolio_id, asset.asset_id)
                if not holding or holding.quantity < Decimal(str(quantity)):
                    available_shares = holding.quantity if holding else 0
                    return APIResponse(
                        success=False,
                        message=f"Insufficient shares. Required: {quantity}, Available: {available_shares}"
                    )
        
        return APIResponse(
            success=True,
            message="Trade validation successful",
            data={
                "estimated_price": float(current_price),
                "estimated_total": float(Decimal(str(quantity)) * current_price)
            }
        )
        
    except Exception as e:
        print(f"Error validating trade: {e}")
        return APIResponse(
            success=False,
            message="Error validating trade"
        ) 