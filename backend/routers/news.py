from fastapi import APIRouter, Depends, HTTPException
from typing import List
from dependencies import get_current_user, FirebaseUser
from services.market_data_client import market_data_client

router = APIRouter()

@router.get("/news/general")
async def get_general_news(current_user: FirebaseUser = Depends(get_current_user)):
    """Get general market news."""
    try:
        articles = await market_data_client.get_general_news()
        return {
            "articles": articles,
            "total": len(articles),
            "cache_hit": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get news: {str(e)}")

@router.get("/news/{symbol}")
async def get_company_news(symbol: str, current_user: FirebaseUser = Depends(get_current_user)):
    """Get company-specific news."""
    try:
        articles = await market_data_client.get_company_news(symbol)
        return {
            "articles": articles,
            "total": len(articles),
            "symbol": symbol.upper(),
            "cache_hit": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get news: {str(e)}")