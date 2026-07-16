from app.models.post import Post
from app.models.top_pick import TopPick
from app.database import get_db
from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session


class TopPickResponse(BaseModel):
    post_id: str
    username: str
    user_id: str
    tickers: List[str]
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
