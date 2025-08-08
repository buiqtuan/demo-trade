from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging
import firebase_admin
from firebase_admin import auth, credentials
import os
from pydantic import BaseModel

from database import get_db
from dependencies import get_current_user
from schemas import UserCreate, UserResponse, PortfolioCreate
import crud

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Firebase token verification schema
class FirebaseTokenRequest(BaseModel):
    firebase_token: str
    email: Optional[str] = None
    display_name: Optional[str] = None

# User profile update schema
class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

# Initialize Firebase Admin SDK (if not already initialized)
try:
    firebase_admin.get_app()
except ValueError:
    # Firebase app not initialized, initialize it
    if os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
        cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"))
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")
    else:
        logger.warning("Firebase service account key not found. Firebase token verification will fail.")

@router.post("/register", response_model=UserResponse)
async def register_user(
    token_request: FirebaseTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user after Firebase authentication.
    This endpoint creates the user in the backend database and sets up their default portfolio.
    """
    try:
        # Verify Firebase token
        try:
            decoded_token = auth.verify_id_token(token_request.firebase_token)
            firebase_user_id = decoded_token['uid']
            firebase_email = decoded_token.get('email', token_request.email)
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )
        
        # Check if user already exists
        existing_user = crud.get_user(db, firebase_user_id)
        if existing_user:
            logger.info(f"User {firebase_user_id} already exists, returning existing user")
            return existing_user
        
        # Generate username if not provided
        username = token_request.display_name or f"user_{firebase_user_id[:8]}"
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while crud.get_user_by_username(db, username):
            username = f"{base_username}_{counter}"
            counter += 1
        
        # Create user
        user_create = UserCreate(
            user_id=firebase_user_id,
            email=firebase_email or "",
            username=username
        )
        
        # Create user in database
        user = crud.create_user(db, user_create)
        
        # Create default portfolio with $10,000 starting balance
        portfolio_create = PortfolioCreate(
            user_id=firebase_user_id,
            cash_balance=Decimal("10000.00"),
            initial_balance=Decimal("10000.00")
        )
        portfolio = crud.create_portfolio(db, portfolio_create)
        
        logger.info(f"Successfully registered user {firebase_user_id} with portfolio {portfolio.portfolio_id}")
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's profile information.
    """
    try:
        user = crud.get_user(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile for {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile information.
    """
    try:
        user = crud.get_user(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Prepare update data (only include non-None values)
        update_data = {}
        for field, value in profile_update.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        # Check username uniqueness if username is being updated
        if "username" in update_data and update_data["username"] != user.username:
            existing_user = crud.get_user_by_username(db, update_data["username"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Update user
        updated_user = crud.update_user(db, current_user, **update_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )
        
        logger.info(f"Successfully updated profile for user {current_user}")
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile for {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )

@router.delete("/account")
async def delete_user_account(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's account and all associated data.
    This is a destructive operation that cannot be undone.
    """
    try:
        user = crud.get_user(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found"
            )
        
        # TODO: Implement cascade deletion of user data
        # This should delete portfolio, holdings, transactions, watchlist, etc.
        # For now, we'll just mark the user as inactive
        crud.update_user(db, current_user, is_active=False)
        
        logger.info(f"Successfully deactivated account for user {current_user}")
        
        return {
            "success": True,
            "message": "Account has been deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete account for {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )

@router.post("/verify-token")
async def verify_firebase_token(
    token_request: FirebaseTokenRequest
):
    """
    Verify a Firebase token without registering the user.
    Public endpoint - useful for validating tokens on the frontend.
    """
    try:
        decoded_token = auth.verify_id_token(token_request.firebase_token)
        
        return {
            "valid": True,
            "user_id": decoded_token['uid'],
            "email": decoded_token.get('email'),
            "email_verified": decoded_token.get('email_verified', False)
        }
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return {
            "valid": False,
            "error": "Invalid or expired token"
        }
