from app.models.post import Post
from app.models.top_pick import TopPick
from app.models.user import User
from app.database import get_db
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session


class TopPickResponse(BaseModel):
    post_id: str
    username: str
    user_id: str
    tickers: Optional[List[str]] = None
    score: float
    sentiment: Optional[str]
    post_content: str


router = APIRouter(prefix="/picks", tags=["picks"])


def get_top_picks(db):
    return db.query(TopPick).filter(TopPick.is_current == True).all()


def get_posts_for_top_picks(db, top_picks):
    post_ids = [top_pick.post_id for top_pick in top_picks]
    return db.query(Post).filter(Post.post_id.in_(post_ids)).all()


def get_top_picks_response(db: Session) -> List[TopPickResponse]:
    top_picks = get_top_picks(db)
    posts = get_posts_for_top_picks(db, top_picks)
    post_dict = {post.post_id: post for post in posts}

    top_picks_json = []
    for top_pick in top_picks:
        post = post_dict.get(top_pick.post_id)
        if post:
            top_picks_json.append(
                TopPickResponse(
                    post_id=top_pick.post_id,
                    username=post.username,
                    user_id=top_pick.user_id,
                    tickers=top_pick.tickers,
                    score=top_pick.score,
                    sentiment=top_pick.sentiment,
                    post_content=post.text,
                )
            )
    return top_picks_json


@router.get("/top", response_model=List[TopPickResponse])
def top_picks(db: Session = Depends(get_db)):
    return get_top_picks_response(db)


class TopPickFullResponse(BaseModel):
    # pick
    pick_id: int
    score: float
    sentiment: Optional[str]
    generated_at: Optional[datetime]
    # post
    post_id: str
    username: str
    user_id: str
    post_content: str
    tickers: Optional[List[str]] = None
    timestamp: Optional[datetime]
    like_count: int
    repost_count: int
    url: str
    sentiment_score: Optional[float]
    is_related: Optional[bool]
    is_valid: Optional[bool]
    pick_verified: Optional[bool]
    pick_correct: Optional[bool]
    # user
    hit_rate: Optional[float]
    total_picks: Optional[int]
    correct_picks: Optional[int]
    pending_picks: Optional[int]
    user_list_status: Optional[str]

    class Config:
        from_attributes = True


@router.get("/top/full", response_model=List[TopPickFullResponse])
def top_picks_full(db: Session = Depends(get_db)):
    top_picks = db.query(TopPick).filter(TopPick.is_current == True).all()
    post_ids = [tp.post_id for tp in top_picks]
    user_ids = [tp.user_id for tp in top_picks]

    posts = {p.post_id: p for p in db.query(Post).filter(Post.post_id.in_(post_ids)).all()}
    users = {u.user_id: u for u in db.query(User).filter(User.user_id.in_(user_ids)).all()}

    results = []
    for tp in top_picks:
        post = posts.get(tp.post_id)
        user = users.get(tp.user_id)
        if not post:
            continue
        results.append(TopPickFullResponse(
            pick_id=tp.pick_id,
            score=tp.score,
            sentiment=tp.sentiment,
            generated_at=tp.generated_at,
            post_id=tp.post_id,
            username=post.username,
            user_id=tp.user_id,
            post_content=post.text,
            tickers=tp.tickers,
            timestamp=post.timestamp,
            like_count=post.like_count,
            repost_count=post.repost_count,
            url=post.url,
            sentiment_score=post.sentiment_score,
            is_related=post.is_related,
            is_valid=post.is_valid,
            pick_verified=post.pick_verified,
            pick_correct=post.pick_correct,
            hit_rate=user.hit_rate if user else None,
            total_picks=user.total_picks if user else None,
            correct_picks=user.correct_picks if user else None,
            pending_picks=getattr(user, 'pending_picks', None) if user else None,
            user_list_status=user.list_status if user else None,
        ))
    return results
