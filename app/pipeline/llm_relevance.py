from app.database import get_db
from app.services.gemini import classify_relevance_with_gemini
from app.models.post import Post
from datetime import datetime
from app.models.user import User

# query postgresql database for posts


# pull 200 posts from the db
def get_posts_from_db(db_session, batch_size=200):
    return (
        db_session.query(Post)
        .join(User, User.user_id == Post.user_id)
        .filter(Post.is_related == None, Post.llm_processed == False, User.list_status != "blacklist")
        .order_by(Post.post_id)
        .limit(batch_size)
        .all()
    )


# send 50 posts to the gemini model for classification at a time
def get_relevance(posts, batch_size=50, historical=False):
    results = []
    for i in range(0, len(posts), batch_size):
        batch = posts[i : i + batch_size]
        post_texts = [post.text for post in batch]
        response = classify_relevance_with_gemini(post_texts, historical=historical)
        results.extend(response.results)
    return results


def update_db(posts, classifications, db_session, historical=False):
    for post, result in zip(posts, classifications):
        post.is_related = result.is_relevant
        if historical and result.is_relevant:
            post.tickers = [result.ticker]
    db_session.commit()


def run_relevance_pipeline(db_session, limit=None, posts=None, historical=False):
    limit = len(posts) if posts else limit
    while True:
        if posts is None:
            posts = get_posts_from_db(
                db_session, batch_size=min(200, limit) if limit else 200
            )
        if not posts:
            print("No more unprocessed posts found. Exiting.")
            break
        classifications = get_relevance(posts, historical=historical)
        update_db(posts, classifications, db_session, historical=historical)
        if limit:
            limit -= len(posts)
            if limit <= 0:
                break  # Exit after processing the specified limit of posts
        posts = (
            None  # Reset posts to None to fetch the next batch in the next iteration
        )


def get_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the relevance classification pipeline."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of posts to process (default: process all unprocessed posts)",
    )
    return parser.parse_args()


def main():
    start_time = datetime.now()
    args = get_args()
    db_session = next(get_db())
    try:
        run_relevance_pipeline(db_session, args.limit)
    except Exception as e:
        print(f"An error occurred: {e}")
        db_session.rollback()
        raise e
    finally:
        db_session.close()
    print("Relevance classification pipeline completed successfully.")
    end_time = datetime.now()
    print(f"Total time taken: {end_time - start_time}")


if __name__ == "__main__":
    main()
