# Verifies the picks made by users in the database to prepare for the User_Credibility pipeline.
# This is done by running the posts through the LLM to check for relevance and sentiment, and then updating the database with the results.

from app.models.post import Post
from app.models.user import User
from datetime import datetime, timedelta
from app.pipeline.scrape_posts import scrape_posts_for_user
from app.pipeline.store_posts import store_posts
from app.pipeline.llm_relevance import run_relevance_pipeline
from app.pipeline.llm_sentiment import run_sentiment_pipeline
from app.services.yfinance import get_stock_data
from sqlalchemy import func

# Outcomes of trying to price a single ticker.
OK = "ok"  # we got a usable price series
NO_DATA = "no_data"  # yfinance has nothing for this symbol/window - permanent
ERROR = "error"  # the call blew up (rate limit, network) - worth retrying

BULLISH_THRESHOLD = 3.0
BEARISH_THRESHOLD = -3.0
NEUTRAL_UPPER = 3.0
NEUTRAL_LOWER = -1.0


def get_posts_from_db(
    user_id,
    db_session,
    batch_size=500,
    historical=False,
    thirty_days_ago=None,
    llm_processed=False,
):
    return (
        db_session.query(Post)
        .filter(
            Post.user_id == user_id,
            Post.is_valid == True,
            Post.pick_verified == False,
            Post.is_historical == historical,
            (Post.timestamp < thirty_days_ago if thirty_days_ago else True),
            Post.llm_processed == llm_processed,
            func.array_length(Post.tickers, 1) > 0,
            Post.tickers[1].isnot(None),
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
    try:
        historical_posts = scrape_posts_for_user(
            all=True,
            limit_calls=5,
            user_id=user_id,
            date_start=date_start,
            date_end=date_end,
        )
    except Exception as e:
        print(f"Skipping user {user_id}, could not scrape historical posts: {e}")
        return [], thirty_days_ago, False
    return historical_posts, thirty_days_ago, True


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


def update_posts_db(scored, unscorable, db_session):
    for post in scored:
        post.pick_verified = True
    for post in unscorable:
        post.pick_correct = None
        post.pick_verified = True
    db_session.commit()


def update_user_last_historical_post(user, db_session, last_historical_post):
    user.last_historical_post = last_historical_post
    db_session.commit()


def score_ticker(ticker, timestamp):
    try:
        data = get_stock_data(ticker, timestamp)
    except Exception as e:
        print(f"Error fetching stock data for ticker {ticker}: {e}")
        return None, ERROR

    if not data:
        return None, NO_DATA

    day_0 = data.get("day_0")
    if not day_0:  # None or 0 - can't compute a percentage against it
        return None, NO_DATA

    changes = []
    for label in ("day_30", "day_60", "day_90"):
        price = data.get(label)
        if price is None:
            continue
        changes.append(((price - day_0) / day_0) * 100)

    if not changes:
        return None, NO_DATA

    return sum(changes) / len(changes), OK


def verify_picks(posts):
    """Score each post against price data.

    Returns (scored, unscorable, retry).
    Crucially, missing price data is never treated as a 0% move.
    """
    scored = []
    unscorable = []
    retry = []

    for post in posts:
        changes = []
        statuses = []

        for ticker in post.tickers or []:
            change, status = score_ticker(ticker, post.timestamp)
            statuses.append(status)
            if change is not None:
                changes.append(change)

        if not changes:
            if ERROR in statuses:
                # Transient failure, retry later
                retry.append(post)
            else:
                post.pick_correct = None
                unscorable.append(post)
            continue

        # only tickers that have data
        avg_percent_change = sum(changes) / len(changes)

        if post.sentiment == "bullish":
            post.pick_correct = avg_percent_change > BULLISH_THRESHOLD
        elif post.sentiment == "bearish":
            post.pick_correct = avg_percent_change < BEARISH_THRESHOLD
        else:  # neutral
            post.pick_correct = NEUTRAL_LOWER < avg_percent_change < NEUTRAL_UPPER

        scored.append(post)

    return scored, unscorable, retry


def run_ai_verification(user_id, db_session):
    # Placeholder for the logic to run AI verification on posts
    posts = get_unprocessed_historical_posts(user_id, db_session, stage="relevance")
    llm_relevance_historical_check(db_session, posts)
    posts = get_unprocessed_historical_posts(user_id, db_session, stage="sentiment")
    llm_sentiment_historical_check(db_session, posts)


def run_verify_picks_pipeline(user_id, db_session, limit=None, skip_scrape=False):
    user = get_user_from_db(db_session, user_id)
    if user is None:
        raise ValueError(
            f"No user found for user_id {user_id} — expected an existing user from a valid post"
        )
    last_historical_post = user.last_historical_post

    thirty_days_ago = datetime.now() - timedelta(days=30)

    if not skip_scrape:
        print(
            f"Scraping historical posts for user {user_id} since {last_historical_post}"
        )
        start_time = datetime.now()

        historical_posts, thirty_days_ago, scrape_ok = scrape_historical_posts_for_user(
            user_id, last_historical_post
        )
        end_time = datetime.now()
        print(f"Scraping historical posts completed in {end_time - start_time}")

        if scrape_ok:
            print(f"Storing historical posts for user {user_id}")
            start_time = datetime.now()
            store_scraped_posts(historical_posts, db_session, historical=True)
            end_time = datetime.now()
            print(f"Storing historical posts completed in {end_time - start_time}")

            # Only advance the watermark when the scrape actually succeeded,
            # otherwise a failed scrape looks like a completed one.
            update_user_last_historical_post(
                user, db_session, last_historical_post=thirty_days_ago
            )

        run_ai_verification(user_id, db_session)

    print(f"Retrieving posts from the database for user {user_id}")
    start_time = datetime.now()

    posts = get_posts_from_db(
        user_id,
        db_session,
        **({"batch_size": limit} if limit else {}),
        historical=True,
        thirty_days_ago=thirty_days_ago,
        llm_processed=True,
    )
    posts.extend(
        get_posts_from_db(
            user_id,
            db_session,
            **({"batch_size": limit} if limit else {}),
            historical=False,
            thirty_days_ago=thirty_days_ago,
            llm_processed=True,
        )
    )

    end_time = datetime.now()
    print(f"Retrieving posts completed in {end_time - start_time}")
    start_time = datetime.now()
    print(f"Verifying picks for user {user_id} ({len(posts)} posts)")

    scored, unscorable, retry = verify_picks(posts)

    end_time = datetime.now()
    print(
        f"Verifying picks completed in {end_time - start_time} "
        f"({len(scored)} scored, {len(unscorable)} no price data, {len(retry)} deferred)"
    )

    start_time = datetime.now()

    update_posts_db(scored, unscorable, db_session)

    end_time = datetime.now()
    print(f"Updating posts in the database completed in {end_time - start_time}")


def get_users_with_pending_posts(db_session, ignore_cooldown=False):
    thirty_one_days_ago = datetime.now() - timedelta(days=31)
    query = (
        db_session.query(Post.user_id)
        .join(User, User.user_id == Post.user_id)
        .filter(
            Post.is_valid == True,
            Post.pick_verified == False,
            Post.is_historical == False,
        )
    )
    if not ignore_cooldown:
        query = query.filter(
            (User.last_historical_post == None)
            | (User.last_historical_post < thirty_one_days_ago)
        )
    return query.distinct().all()


def get_args():
    import argparse

    parser = argparse.ArgumentParser(description="Run the verify picks pipeline.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of posts to process.",
    )
    parser.add_argument(
        "--user_id",
        type=str,
        help="The user_id to process.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all users.",
    )
    parser.add_argument(
        "--skip_scrape",
        action="store_true",
        help="Skip scraping historical posts. Only re-score posts already in the database.",
    )
    parser.add_argument(
        "--ignore_cooldown",
        action="store_true",
        help="Ignore the user last historical post in getting users. re-runs for all users"
    )
    return parser.parse_args()


def main():
    from datetime import datetime, timezone
 
    start_time = datetime.now(timezone.utc)
    args = get_args()
 
    if args.user_id is None and args.all is False:
        print(
            "Please provide a user_id to process or use the --all flag to process all users."
        )
        return
    elif args.user_id is None and args.all is True:
        from app.database import get_db
 
        db_session = next(get_db())
        users = get_users_with_pending_posts(db_session, args.ignore_cooldown)
        if len(users) == 0:
            print("No users with pending posts found.")
        else:
            print(f"Found {len(users)} users with pending posts.")
            for user in users:
                try:
                    run_verify_picks_pipeline(
                        user[0],
                        db_session,
                        limit=args.limit,
                        skip_scrape=args.skip_scrape,
                    )
                except Exception as e:
                    print(f"An error occurred while processing user {user[0]}: {e}")
                    db_session.rollback()
        db_session.close()
    else:
        user_id = args.user_id
        try:
            from app.database import get_db
 
            db_session = next(get_db())
            run_verify_picks_pipeline(
                user_id, db_session, limit=args.limit, skip_scrape=args.skip_scrape
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            print(f"Rolling back the session")
            db_session.rollback()
        finally:
            db_session.close()
 
    end_time = datetime.now(timezone.utc)
    print(f"Total time taken: {end_time - start_time}")


if __name__ == "__main__":
    main()
