from app.models.post import Post
from app.models.user import User


def get_posts(db_session, post_id=None):
    if post_id is None:
        return (
            db_session.query(Post)
            .filter(
                Post.is_valid == True,
                Post.pick_verified == False,
                Post.is_historical == False,
            )
            .all()
        )
    else:
        return [
            (
                db_session.query(Post)
                .filter(
                    Post.post_id == post_id,
                    Post.is_valid == True,
                    Post.pick_verified == False,
                    Post.is_historical == False,
                )
                .first()
            )
        ]


def get_users_with_pending_posts(db_session, posts):
    user_ids = list(set(post.user_id for post in posts))
    return db_session.query(User).filter(User.user_id.in_(user_ids)).all()


def calculate_engagement_weight(post, cap=100):
    raw_engagement = post.like_count + (post.repost_count * 2)
    return min(raw_engagement / cap, 1.0)


def rank_picks(db_session, post_id=None):
    posts = get_posts(db_session, post_id=post_id)
    if post_id is not None and posts[0] is None:
        raise ValueError(f"Post with ID {post_id} not found.")
    if not posts:
        print("No posts to rank.")
        return []
    users = get_users_with_pending_posts(db_session, posts)
    user_hit_rates = {user.user_id: user.hit_rate for user in users}

    ranked_posts = []
    for post in posts:
        engagment_weight = calculate_engagement_weight(post)
        sentiment_score = post.sentiment_score
        hit_rate = user_hit_rates.get(post.user_id)
        if hit_rate is None:
            continue  # Skip posts for users without a hit rate
        post_score = sentiment_score * hit_rate * engagment_weight
        ranked_posts.append((post, post_score))
    ranked_posts.sort(key=lambda x: x[1], reverse=True)
    return ranked_posts


def build_json(input):
    return [
        {
            "post_id": post.post_id,
            "user_id": post.user_id,
            "ticker": post.tickers,
            "score": score,
            "sentiment": post.sentiment
        } for post, score in input
    ]

def get_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rank picks for users based on their credibility scores and other factors."
    )
    parser.add_argument(
        "--post_id",
        type=str,
        help="Optional post ID to rank picks for a specific post.",
    )
    return parser.parse_args()


def main():
    from app.database import get_db
    from datetime import datetime
    import json
    import os

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    start_time = datetime.now()

    args = get_args()
    db_session = next(get_db())
    try:
        ranked_posts = rank_picks(db_session=db_session, post_id=args.post_id)
        output = build_json(ranked_posts)
        output_file = os.path.join(BASE_DIR, "data", "ranked_picks.json")
        with open(output_file, "w") as f:
            json.dump(output, f, indent=4)
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        db_session.close()
    end_time = datetime.now()
    print(f"Pick ranking completed in: {end_time - start_time}")


if __name__ == "__main__":
    main()
