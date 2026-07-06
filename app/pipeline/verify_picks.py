from app.database import get_db
from app.models.post import Post
from app.models.user import User
from datetime import datetime, timedelta
from app.pipeline.update_credibility import update_credibility_scores_for_users
from app.pipeline.scrape_posts import scrape_posts_for_user


def get_posts_from_db(db_session, batch_size=10, historical=False):
    return (
        db_session.query(Post)
        .filter(
            Post.is_valid == True,
            Post.pick_verified == False,
            Post.is_historical == historical,
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
    # Placeholder for the logic to retrieve posts for a specific user
    # Scrape past posts for the user and return them
    date = datetime.now()
    thirty_days_ago = date - timedelta(days=30)
    two_years_ago = date - timedelta(days=730)
    date_end = thirty_days_ago.strftime("%Y-%m-%d")
    date_start = (max(last_historical_post, two_years_ago) if last_historical_post else two_years_ago).strftime("%Y-%m-%d")
    # Call the scrape_posts function with appropriate parameters to get past posts for the user
    historical_posts = scrape_posts_for_user(all = True, limit_calls=5, user_id=user_id, date_start=date_start, date_end=date_end)
    return historical_posts

def store_scraped_posts(posts, db_session):
    # Placeholder for the logic to store scraped posts in the database
    pass

def llm_relevance_historical_check(posts, db_session):
    # Placeholder for the logic to perform LLM relevance and historical checks on posts
    pass

def llm_sentiment_historical_check(posts, db_session):
    # Placeholder for the logic to perform LLM sentiment and historical checks on posts
    pass

def update_posts_db(posts, db_session):
    for post in posts:
        post.pick_verified = True
    db_session.commit()


def update_users_db():
    update_credibility_scores_for_users()
    pass


def verify_picks(posts, db_session):
    # Placeholder for the logic to verify picks
    
        
    pass


def run_verify_picks_pipeline(user_id, db_session, limit=None):
    # Placeholder for the main logic to run the verify picks pipeline
    posts = get_posts_from_db(db_session, batch_size=min(10, limit) if limit else 10)
    for post in posts:
        user_id = post.user_id
        user = get_user_from_db(db_session, user_id)
        if user:
            last_historical_post = user.last_historical_post
        else:
            last_historical_post = None
        historical_posts = scrape_historical_posts_for_user(user_id, last_historical_post)

        credibility_score = verify_picks(historical_posts, db_session)
    pass

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
