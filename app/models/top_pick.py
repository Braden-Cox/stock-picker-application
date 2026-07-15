from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base
from datetime import datetime, timezone


class TopPick(Base):
    __tablename__ = "top_picks"

    pick_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(50), nullable=False)
    user_id = Column(String(50), nullable=False)
    tickers = Column(ARRAY(String(5)), nullable=False)
    score = Column(Float, nullable=False)
    sentiment = Column(String(10), nullable=True)
    generated_at = Column(DateTime, default=datetime.now(timezone.utc))
    is_current = Column(Boolean, default=True)
