from app.services.anthropic import classify_sentiment_with_haiku
from app.database import get_db
from app.models.post import Post



def get_posts_from_db(db_session, batch_size=400):
    return (
        db_session.query(Post)
        .filter(Post.is_related != None, Post.llm_processed == False)
        .order_by(Post.post_id)
        .limit(batch_size)
        .all()
    )


def update_db(posts, sentiments, db_session):
    for post, sentiment in zip(posts, sentiments):
        post.sentiment = sentiment.label
        post.sentiment_score = sentiment.score
        post.llm_processed = True
    db_session.commit()


def get_sentiment(posts, batch_size=100):
    results = []
    for i in range(0, len(posts), batch_size):
        batch = posts[i : i + batch_size]
        post_texts = [post.text for post in batch]
        response = classify_sentiment_with_haiku(post_texts)
        results.extend(response.results)
    return results

def run_sentiment_pipeline(db_session, limit=None):
    pass


def get_args():
    import argparse

    parser = argparse.ArgumentParser(description="Run the sentiment classification pipeline.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of posts to process (default: process all unprocessed posts)"
    )
    return parser.parse_args()


def main():
    args = get_args()
    db_session = next(get_db())
    try:
        run_sentiment_pipeline(db_session, limit=args.limit)
    except Exception as e:
        print(f"An error occurred: {e}")
        db_session.rollback()
        raise e
    finally:
        db_session.close()
    print("Sentiment classification pipeline completed successfully.")

if __name__ == "__main__":
    main()
