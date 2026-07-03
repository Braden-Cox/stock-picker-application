from app.database import get_db
from app.models.post import Post
from os import path


def store_posts(posts, db_session):
    completed_in_batch = 0
    BATCH_SIZE = 500  # Adjust the batch size as needed
    inserted_in_run = set()  # Track post_ids inserted in this run
    incoming_post_ids = {post["post_id"] for post in posts}
    existing_post_ids = {
        post.post_id
        for post in db_session.query(Post.post_id)
        .filter(Post.post_id.in_(incoming_post_ids))
        .all()
    }
    for post in posts:
        if (post["like_count"] + (post["repost_count"] * 2)) < 5:
            continue  # Skip posts that don't meet the threshold
        if (
            post["post_id"] not in existing_post_ids
            and post["post_id"] not in inserted_in_run
        ):
            new_post = Post(
                post_id=post["post_id"],
                tickers=post["tickers"],
                username=post["username"],
                user_id=post["user_id"],
                text=post["text"],
                timestamp=post["timestamp"],
                like_count=post["like_count"],
                repost_count=post["repost_count"],
                url=post["url"],
                time_scraped_at=post["time_scraped_at"],
                list_status="unknown",
                is_related=None,
                sentiment=None,
                sentiment_score=None,
                llm_processed=False,
                is_valid=None,
            )
            inserted_in_run.add(post["post_id"])
            db_session.add(new_post)
        else:
            existing_post = (
                db_session.query(Post).filter_by(post_id=post["post_id"]).first()
            )
            for ticker in post["tickers"]:
                if ticker not in existing_post.tickers:
                    existing_post.tickers = existing_post.tickers + [ticker]
        db_session.flush()
        completed_in_batch += 1
        if completed_in_batch >= BATCH_SIZE:
            db_session.commit()
            completed_in_batch = 0

    db_session.commit()


def get_args():
    import argparse

    parser = argparse.ArgumentParser(description="Store posts in the database.")
    parser.add_argument(
        "--tickers_list",
        type=str,
        default=None,
        help="A JSON file in the data folder containing a list of tickers to scrape posts for.",
    )
    return parser.parse_args()


def main():
    from app.pipeline.clean_tickers import clean_tickers
    from app.pipeline.fetch_tickers import fetch_tickers
    from app.pipeline.scrape_posts import scrape_posts
    from datetime import datetime, timezone

    start_time = datetime.now(timezone.utc)

    args = get_args()

    BASE_DIR = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))

    if not args.tickers_list:
        tickers = fetch_tickers()
        cleaned_tickers = clean_tickers(tickers)
        posts = scrape_posts(cleaned_tickers)
    else:
        import json

        with open(path.join(BASE_DIR, "data", args.tickers_list)) as f:
            posts = json.load(f)

    db_session = next(get_db())
    try:
        store_posts(posts, db_session)
        print(f"Stored {len(posts)} posts in the post database.")
    except Exception as e:
        db_session.rollback()
        print(f"An error occurred while storing posts: {e}")
        raise e
    finally:
        db_session.close()
    end_time = datetime.now(timezone.utc)
    print(f"Total time taken: {end_time - start_time}")


if __name__ == "__main__":
    main()
