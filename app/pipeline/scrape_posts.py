from datetime import datetime, timedelta, timezone
import os
import json
from app.service.getx import getXAPI_scrape_posts


def scrape_posts(tickers, all=False, limit_tickers=2, limit_calls=2, language="en"):
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    posts = []
    has_more = True
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
        "%Y-%m-%d"
    )
    start_time = datetime.now(timezone.utc)
    i = limit_tickers
    j = 0
    for ticker in tickers:
        if j < i:
            if not ticker["is_active"]:
                print(f"Skipping inactive ticker: {ticker['ticker']}")
                continue
            if ticker["needs_prefix"]:
                query = f"${ticker['ticker']} since:{seven_days_ago} {lang(language)}".strip()
            else:
                query = f"{ticker['ticker']} since:{seven_days_ago} {lang(language)}".strip()
            print(f"Scraping posts for ticker: {ticker['ticker']}")
            cursor = None
            call_count = 0
            scrape_start_time = datetime.now(timezone.utc)
            while call_count < limit_calls:
                try:
                    data = getXAPI_scrape_posts(query, cursor)
                    call_count += 1
                    has_more = data["has_more"]
                    next_cursor = data["next_cursor"]
                    cursor = next_cursor
                    for tweet in data["tweets"]:
                        post = {
                            "post_id": tweet["id"],
                            "text": tweet["text"],
                            "username": tweet["author"]["userName"],
                            "user_id": tweet["author"]["id"],
                            "timestamp": tweet["createdAt"],
                            "like_count": tweet["likeCount"],
                            "repost_count": tweet["retweetCount"],
                            "time_scraped_at": datetime.now(timezone.utc).isoformat(),
                            "tickers": [ticker["ticker"]],
                            "url": tweet["url"],
                        }
                        posts.append(post)
                    if all == False:
                        scrape_end_time = datetime.now(timezone.utc)
                        print(
                            f"Finished scraping posts for ticker: {ticker['ticker']} in {scrape_end_time - scrape_start_time}"
                        )
                        break
                    if has_more == False:
                        scrape_end_time = datetime.now(timezone.utc)
                        print(
                            f"Finished scraping posts for ticker: {ticker['ticker']} in {scrape_end_time - scrape_start_time}"
                        )
                        break
                except Exception as e:
                    print(f"Error scraping posts for ticker {ticker['ticker']}: {e}")
                    scrape_end_time = datetime.now(timezone.utc)
                    print(
                        f"Finished scraping posts for ticker: {ticker['ticker']} in {scrape_end_time - scrape_start_time}"
                    )
                    break
        else:
            print(f"Reached limit of {i} tickers scraped. Stopping.")
            break
        j += 1
    end_time = datetime.now(timezone.utc)
    print(f"Total time taken: {end_time - start_time}")
    return posts


def lang(language):
    if language == "all":
        return ""
    else:
        return f"lang:{language}"


def get_args():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape posts for tickers")
    parser.add_argument(
        "--all", default=False, action="store_true", help="Scrape posts for all tickers"
    )
    parser.add_argument(
        "--limit_tickers",
        type=int,
        default=2,
        help="Limit the number of tickers scraped (default: 2)",
    )
    parser.add_argument(
        "--limit_calls",
        type=int,
        default=2,
        help="Limit the number of API calls (default: 2)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="en",
        help="Language of the posts to scrape (default: en) (all for all languages)",
    )

    return parser.parse_args()


def main():
    from app.pipeline.fetch_tickers import fetch_tickers
    from app.pipeline.clean_tickers import clean_tickers

    args = get_args()
    tickers = fetch_tickers()
    cleaned_tickers = clean_tickers(tickers)
    posts = scrape_posts(
        cleaned_tickers,
        all=args.all,
        limit_tickers=args.limit_tickers,
        limit_calls=args.limit_calls,
        language=args.lang,
    )
    print(f"Scraped {len(posts)} posts.")
    output_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "posts.json",
    )
    with open(output_file, "w") as f:
        json.dump(posts, f, indent=4)
    print(f"Saved posts to {output_file}")


if __name__ == "__main__":
    main()
