from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Float
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base
from datetime import datetime, timezone


class Post(Base):
    __tablename__ = "posts"

    post_id = Column(String(50), primary_key=True)
    tickers = Column(ARRAY(String(5)), nullable=False)
    username = Column(String(50), nullable=False)
    user_id = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    like_count = Column(Integer, nullable=False)
    repost_count = Column(Integer, nullable=False)
    url = Column(String(255), nullable=False)
    time_scraped_at = Column(DateTime, default=datetime.now(timezone.utc))
    list_status = Column(String(20), default="unknown")
    is_related = Column(Boolean, default=None)
    sentiment = Column(String(10), default=None)
    sentiment_score = Column(Float, default=None)
    llm_processed = Column(Boolean, default=False)
    is_valid = Column(Boolean, default=None)
    is_historical = Column(Boolean, default=False)
    pick_verified = Column(Boolean, default=False)
    pick_correct = Column(Boolean, default=None)
