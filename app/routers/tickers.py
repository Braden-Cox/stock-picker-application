from app.models.ticker import Ticker
from app.database import get_db
from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException


class TickerResponse(BaseModel):
    ticker: str
    company_name: Optional[str]
    exchange: str
    is_active: bool
    flag_reason: Optional[str]
    relevance_rate: Optional[float]
    total_posts_scraped: int


router = APIRouter(prefix="/tickers", tags=["tickers"])


def get_ticker(db, ticker_symbol):
    return db.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()


def get_active_tickers(db):
    return db.query(Ticker).filter(Ticker.is_active == True).all()


def get_ticker_credibility_response(db: Session, ticker_symbol: str) -> TickerResponse:
    ticker = get_ticker(db, ticker_symbol.upper())
    if ticker is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_symbol} not found")
    return TickerResponse(
        ticker=ticker.ticker,
        company_name=ticker.company_name,
        exchange=ticker.exchange,
        is_active=ticker.is_active,
        flag_reason=ticker.flag_reason,
        relevance_rate=ticker.relevance_rate,
        total_posts_scraped=ticker.total_posts_scraped
    )


def get_active_tickers_response(db: Session) -> List[TickerResponse]:
    active_tickers = get_active_tickers(db)
    return [
        TickerResponse(
            ticker=ticker.ticker,
            company_name=ticker.company_name,
            exchange=ticker.exchange,
            is_active=ticker.is_active,
            flag_reason=ticker.flag_reason,
            relevance_rate=ticker.relevance_rate,
            total_posts_scraped=ticker.total_posts_scraped
        )
        for ticker in active_tickers
    ]


@router.get("/active", response_model=List[TickerResponse])
def top_active_tickers(db: Session = Depends(get_db)):
    return get_active_tickers_response(db)


@router.get("/{ticker_symbol}", response_model=TickerResponse)
def ticker_credibility(ticker_symbol: str, db: Session = Depends(get_db)):
    return get_ticker_credibility_response(db, ticker_symbol)
