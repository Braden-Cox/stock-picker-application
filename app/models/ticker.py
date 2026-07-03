from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float
from app.database import Base
from datetime import datetime, timezone


class Ticker(Base):
    __tablename__ = "tickers"

    ticker = Column(String(10), primary_key=True)
    company_name = Column(String(255))
    exchange = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    flag_reason = Column(String(255))
    needs_prefix = Column(Boolean, nullable=False, default=False)
    first_seen = Column(DateTime, default=datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    total_posts_scraped = Column(Integer, default=0)
    relevant_posts = Column(Integer, default=0)
    relevance_rate = Column(Float, default=None)
