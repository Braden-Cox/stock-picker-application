from sqlalchemy import Column, String, Float, Integer, DateTime
from app.database import Base
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(50), primary_key=True)
    username = Column(String(50), nullable=False)
    list_status = Column(String(20), default="unknown")
    hit_rate = Column(Float, default=None)
    total_picks = Column(Integer, default=0)
    correct_picks = Column(Integer, default=0)
    pending_picks = Column(Integer, default=0)
    first_seen = Column(DateTime, default=datetime.now(timezone.utc))
    last_scraped = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_historical_post = Column(DateTime, default=None)
