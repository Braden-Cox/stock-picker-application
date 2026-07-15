from app.models.post import Post
from app.models.ticker import Ticker


def get_all_tickers(db_session):
    return db_session.query(Ticker).all()


def get_posts_for_ticker(db_session, ticker_symbol):
    return db_session.query(Post).filter(Post.tickers.contains([ticker_symbol])).all()


def update_ticker_status(db_session, min_posts=500, relevance_threshold=0.01):
    tickers = get_all_tickers(db_session)
    for ticker in tickers:
        if not ticker.is_active:
            continue  # already inactive — don't touch it

        posts = get_posts_for_ticker(db_session, ticker.ticker)
        total_scraped = len(posts)

        if total_scraped < min_posts:
            continue  # not enough data yet to trust the ratio

        relevant_posts = sum(1 for post in posts if post.is_related)
        relevance_rate = relevant_posts / total_scraped

        ticker.total_posts_scraped = total_scraped
        ticker.relevant_posts = relevant_posts
        ticker.relevance_rate = relevance_rate

        if relevance_rate < relevance_threshold:
            ticker.is_active = False
            ticker.flag_reason = "Ticker scrapes irrelevant posts too often"
            print(
                f"Deactivated {ticker.ticker}: relevance_rate={relevance_rate:.2%} over {total_scraped} posts"
            )

    db_session.commit()


def get_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Update ticker status based on post relevance."
    )
    parser.add_argument(
        "--min_posts",
        type=int,
        default=500,
        help="Minimum number of posts required to evaluate a ticker.",
    )
    parser.add_argument(
        "--relevance_threshold",
        type=float,
        default=0.01,
        help="Relevance rate threshold below which a ticker is deactivated.",
    )
    return parser.parse_args()


def main():
    from app.database import get_db

    args = get_args()

    db_session = next(get_db())
    try:
        update_ticker_status(db_session, args.min_posts, args.relevance_threshold)
    finally:
        db_session.close()


if __name__ == "__main__":
    main()