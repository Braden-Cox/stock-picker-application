# Verifies the picks made by users in the database to prepare for the User_Credibility pipeline.
# This is done by running the posts through the LLM to check for relevance and sentiment, and then updating the database with the results.

from app.database import get_db
from app.models.post import Post
from app.models.user import User
from datetime import datetime, timedelta
from app.pipeline.scrape_posts import scrape_posts_for_user
from app.pipeline.store_posts import store_posts
from app.pipeline.llm_relevance import run_relevance_pipeline
from app.pipeline.llm_sentiment import run_sentiment_pipeline


def get_posts_from_db(
    user_id, db_session, batch_size=10, historical=False, thirty_days_ago=None, llm_processed=False
):
    return (
        db_session.query(Post)
        .filter(
            Post.user_id == user_id,
            Post.is_valid == True,
            Post.pick_verified == False,
            Post.is_historical == historical,
            (
                Post.timestamp < thirty_days_ago
                if historical and thirty_days_ago
                else True
            ),
            Post.llm_processed == llm_processed,
        )
        .order_by(Post.post_id)
        .limit(batch_size)
        .all()
    )


def get_user_from_db(db_session, user_id):
    return (
        db_session.query(User)
        .filter(User.user_id == user_id)
        .order_by(User.user_id)
        .first()
    )


def scrape_historical_posts_for_user(user_id, last_historical_post=None):
    # Scrape past posts for the user and return them
    date = datetime.now()
    thirty_days_ago = date - timedelta(days=30)
    two_years_ago = date - timedelta(days=730)
    date_end = thirty_days_ago.strftime("%Y-%m-%d")
    date_start = (
        max(last_historical_post, two_years_ago)
        if last_historical_post
        else two_years_ago
    ).strftime("%Y-%m-%d")
    # Call the scrape_posts function with appropriate parameters to get past posts for the user
    historical_posts = scrape_posts_for_user(
        all=True,
        limit_calls=5,
        user_id=user_id,
        date_start=date_start,
        date_end=date_end,
    )
    return historical_posts, thirty_days_ago


def get_unprocessed_historical_posts(user_id, db_session, stage, batch_size=200):
    query = db_session.query(Post).filter(
        Post.user_id == user_id,
        Post.is_historical == True,
    )
    if stage == "relevance":
        query = query.filter(Post.is_related == None)
    elif stage == "sentiment":
        query = query.filter(Post.is_related == True, Post.llm_processed == False)
    return query.order_by(Post.post_id).limit(batch_size).all()


def store_scraped_posts(
    posts,
    db_session,
    historical=True,
):
    store_posts(posts, db_session, historical=historical)


def llm_relevance_historical_check(db_session, posts):
    run_relevance_pipeline(db_session, posts=posts, historical=True)


def llm_sentiment_historical_check(db_session, posts):
    run_sentiment_pipeline(db_session, posts=posts, historical=True)


def update_posts_db(posts, db_session):
    for post in posts:
        post.pick_verified = True
    db_session.commit()


def update_user_last_historical_post(user, db_session, last_historical_post):
    user.last_historical_post = last_historical_post
    db_session.commit()


def verify_picks(posts, db_session):
    # Placeholder for the logic to verify picks
    for post in posts:
        pass  # Implement the logic to verify picks based on relevance and sentiment
    pass


def run_ai_verification(user_id, db_session):
    # Placeholder for the logic to run AI verification on posts
    
    posts = get_unprocessed_historical_posts(user_id, db_session, stage="relevance")
    llm_relevance_historical_check(db_session, posts)
    posts = get_unprocessed_historical_posts(user_id, db_session, stage="sentiment")
    llm_sentiment_historical_check(db_session, posts)

def run_verify_picks_pipeline(user_id, db_session, limit=None):
    user = get_user_from_db(db_session, user_id)
    if user:
        last_historical_post = user.last_historical_post
    else:
        last_historical_post = None
    if user is None:
        raise ValueError(f"No user found for user_id {user_id} — expected an existing user from a valid post")
    print(f"Scraping historical posts for user {user_id} since {last_historical_post}")
    start_time = datetime.now()

    historical_posts, thirty_days_ago = scrape_historical_posts_for_user(user_id, last_historical_post)
    end_time = datetime.now()

    print(f"Scraping historical posts completed in {end_time - start_time}")
    print(f"Storing historical posts for user {user_id}")
    start_time = datetime.now()

    store_scraped_posts(historical_posts, db_session, historical=True)

    end_time = datetime.now()
    print(f"Storing historical posts completed in {end_time - start_time}")

    update_user_last_historical_post(user, db_session, last_historical_post=thirty_days_ago)

    run_ai_verification(user_id, db_session)

    print(f"Retrieving posts from the database for user {user_id}")
    start_time = datetime.now()

    posts = get_posts_from_db(
        user_id,
        db_session,
        **({"batch_size": limit} if limit else {}),
        historical=True,
        thirty_days_ago=thirty_days_ago,
        llm_processed=True
    )
    posts.extend(
        get_posts_from_db(
            user_id,
            db_session,
            **({"batch_size": limit} if limit else {}),
            historical=False,
            thirty_days_ago=thirty_days_ago,
            llm_processed=True
        )
    )

    end_time = datetime.now()
    print(f"Retrieving posts completed in {end_time - start_time}")
    start_time = datetime.now()
    print(f"Verifying picks for user {user_id}")

    posts = verify_picks(posts, db_session)

    end_time = datetime.now()
    print(f"Verifying picks completed in {end_time - start_time}")

    start_time = datetime.now()

    update_posts_db(posts, db_session)

    end_time = datetime.now()
    print(f"Updating posts in the database completed in {end_time - start_time}")


def get_args():
    import argparse

    parser = argparse.ArgumentParser(description="Run the verify picks pipeline.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of posts to process.",
    )
    return parser.parse_args()


def main():
    from datetime import datetime, timezone

    start_time = datetime.now(timezone.utc)
    # Placeholder for the main logic to run the verify picks pipeline
    end_time = datetime.now(timezone.utc)
    print(f"Total time taken: {end_time - start_time}")


if __name__ == "__main__":
    main()
