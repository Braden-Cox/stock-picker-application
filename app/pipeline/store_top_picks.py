from app.models.top_pick import TopPick
from app.models.post import Post


def build_pool_of_picks(ranked_posts, previous_top_picks):
    pool_of_picks = {}

    for tp in previous_top_picks:
        pool_of_picks[tp.post_id] = {
            "post_id": tp.post_id,
            "user_id": tp.user_id,
            "tickers": tp.tickers if tp.tickers else None,
            "score": tp.score,
            "sentiment": tp.sentiment,
            "existing_top_pick": tp,
        }

    for post, score in ranked_posts:
            existing = pool_of_picks.get(post.post_id, {}).get("existing_top_pick")
            pool_of_picks[post.post_id] = {
                "post_id": post.post_id,
                "user_id": post.user_id,
                "tickers": post.tickers if post.tickers else None,
                "score": score,
                "sentiment": post.sentiment,
                "existing_top_pick": existing,
            }

    return list(pool_of_picks.values())

def get_existing_rows(db_session, post_ids):
    if not post_ids:
        return {}
    rows = db_session.query(TopPick).filter(TopPick.post_id.in_(post_ids)).all()
    return {row.post_id: row for row in rows}


def store_top_picks(db_session, ranked_posts, top_n=20):
    # Mark all existing top picks as not current
    previous_top_picks = get_previous_top_picks(db_session)

    pool_of_picks = build_pool_of_picks(ranked_posts, previous_top_picks)
    pool_of_picks.sort(key=lambda x: x["score"], reverse=True)

    existing_rows = get_existing_rows(
        db_session, [data["post_id"] for data in pool_of_picks]
    )
 
    inserted = 0
    updated = 0

    # Store new top picks
    for i, data in enumerate(pool_of_picks):
        is_current = i < top_n
        row = data["existing_top_pick"] or existing_rows.get(data["post_id"])
 
        if row is not None:
            row.is_current = is_current
            row.score = data["score"]
            row.sentiment = data["sentiment"]
            row.tickers = data["tickers"]
            updated += 1
        elif is_current:
            # Only picks that actually made the cut get a row. The old code
            # inserted one per ranked post, which is why the table grew far
            # past top_n.
            db_session.add(
                TopPick(
                    post_id=data["post_id"],
                    user_id=data["user_id"],
                    tickers=data["tickers"],
                    score=data["score"],
                    sentiment=data["sentiment"],
                    is_current=True,
                )
            )
            inserted += 1
        # else: didn't make the cut and has no row — nothing to store
 
    db_session.commit()
    print(f"Top picks: {inserted} inserted, {updated} updated, top_n={top_n}")


def get_previous_top_picks(db_session):
    return db_session.query(TopPick).filter(TopPick.is_current == True).all()


def unpack_json_to_ranked_posts(json_data):
    ranked_posts = []
    for item in json_data:
        post = Post(
            post_id=item["post_id"],
            user_id=item["user_id"],
            tickers=item["ticker"],
            sentiment=item.get("sentiment"),
        )
        score=item.get("score", 0.0)
        ranked_posts.append((post, score))
    return ranked_posts


def get_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Rank stock picks based on sentiment and user credibility."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Optional input file containing posts to rank. If not provided, all posts will be ranked.",
    )
    parser.add_argument(
        "--top_n",
        type=int,
        default=20,
        help="Number of top picks to store. Default is 20.",
    )
    return parser.parse_args()


def main():
    from app.database import get_db
    from datetime import datetime
    import json
    import os
    from app.pipeline.rank_picks import rank_picks

    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    start_time = datetime.now()
    args = get_args()
    db_session = next(get_db())

    try:
        if args.input is not None:
            input_file = os.path.join(BASE_DIR, "data", args.input)
            with open(input_file, "r") as f:
                ranked_posts = unpack_json_to_ranked_posts(json.load(f))
        else:
            ranked_posts = rank_picks(db_session=db_session, post_id=None)
        store_top_picks(
            db_session=db_session, ranked_posts=ranked_posts, top_n=args.top_n
        )
        print(
            f"Top picks stored successfully. Total time taken: {datetime.now() - start_time}"
        )
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        db_session.close()
    end_time = datetime.now()
    print(f"Total time taken: {end_time - start_time}")


if __name__ == "__main__":
    main()
