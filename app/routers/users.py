from app.models.user import User
from app.database import get_db
from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException


class UserCredibilityResponse(BaseModel):
    username: str
    hit_rate: Optional[float]
    list_status: Optional[str] = None
    total_picks: Optional[int]
    correct_picks: Optional[int]


class TopHittersResponse(BaseModel):
    user_id: str
    username: str
    hit_rate: Optional[float]
    total_picks: Optional[int]
    correct_picks: Optional[int]


router = APIRouter(prefix="/users", tags=["users"])


def get_user(db, user_id):
    return db.query(User).filter(User.user_id == user_id).first()


def get_top_users(db):
    return db.query(User).filter(User.list_status == "whitelist").order_by(User.hit_rate.desc()).all()


def get_user_credibility_response(db: Session, user_id: str) -> UserCredibilityResponse:
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return UserCredibilityResponse(
        username=user.username,
        hit_rate=user.hit_rate,
        list_status=user.list_status,
        total_picks=user.total_picks,
        correct_picks=user.correct_picks
    )


def get_top_hitters_response(db: Session) -> List[TopHittersResponse]:
    top_users = get_top_users(db)
    return [
        TopHittersResponse(
            user_id=user.user_id,
            username=user.username,
            hit_rate=user.hit_rate,
            total_picks=user.total_picks,
            correct_picks=user.correct_picks
        )
        for user in top_users
    ]


@router.get("/top", response_model=List[TopHittersResponse])
def top_picks(db: Session = Depends(get_db)):
    return get_top_hitters_response(db)


@router.get("/{user_id}", response_model=UserCredibilityResponse)
def user_credibility(user_id: str, db: Session = Depends(get_db)):
    return get_user_credibility_response(db, user_id)
