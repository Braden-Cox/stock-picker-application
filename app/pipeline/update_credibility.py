from app.models.user import User
from app.models.post import Post


def get_users_with_pending_posts(db_session):
    posts = (
        db_session.query(Post.user_id)
        .filter(
            Post.is_valid == True,
            Post.pick_verified == False,
            Post.is_historical == False,
        )
        .distinct()
        .all()
    )
    user_ids = [post[0] for post in posts]
    return db_session.query(User).filter(User.user_id.in_(user_ids)).distinct().all()


def get_posts_for_user(db_session, user_id):
    return (
        db_session.query(Post)
        .filter(Post.user_id == user_id, Post.pick_verified == True)
        .all()
    )


def update_credibility_scores_for_users(db_session, user_id=None):
    if user_id is not None:
        user = db_session.query(User).filter(User.user_id == user_id).first()
        if user is None:
            raise ValueError(f"User with ID {user_id} not found.")
        users = [user]
    else:
        users = get_users_with_pending_posts(db_session)
    for user in users:
        posts = get_posts_for_user(db_session, user.user_id)
        if posts:
            correct_picks = sum(1 for post in posts if post.pick_correct)
            total_picks = len(posts)
            hit_rate = correct_picks / total_picks if total_picks > 6 else None
            user.hit_rate = hit_rate
            user.correct_picks = correct_picks
            user.total_picks = total_picks
            if hit_rate is None:
                user.list_status = "unknown"
            elif hit_rate >= 0.50:
                user.list_status = "whitelist"
            elif hit_rate < 0.10:
                user.list_status = "blacklist"
            else:
                user.list_status = "greylist"
        else:
            print(
                f"No verified posts found for user {user.user_id}. Skipping credibility score update."
            )
    db_session.commit()


def get_args():
    import argparse

    parser = argparse.ArgumentParser(description="Update credibility scores for users.")
    parser.add_argument(
        "--user-id",
        type=str,
        help="Optional user ID to update credibility score for a specific user",
    )
    return parser.parse_args()


def main():
    from app.database import get_db
    from datetime import datetime

    start_time = datetime.now()

    args = get_args()
    db_session = next(get_db())
    update_credibility_scores_for_users(db_session=db_session, user_id=args.user_id)

    end_time = datetime.now()
    print(f"Credibility score update completed in: {end_time - start_time}")


if __name__ == "__main__":
    main()
