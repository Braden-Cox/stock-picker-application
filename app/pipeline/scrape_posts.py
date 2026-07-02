from datetime import datetime, timedelta, timezone
import requests
import os
from clean_tickers import clean_tickers
import argparse
import json
from app.config import settings

getXAPI_key = settings.GETXAPI_KEY

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

args = parser.parse_args()


def scrape_posts():
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    tickers = clean_tickers()
    posts = []
    has_more = True
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    start_time = datetime.now(timezone.utc)
    i = args.limit_tickers
    j = 0
    for ticker in tickers:
        if j < i:
            if not ticker["is_active"]:
                print(f"Skipping inactive ticker: {ticker['ticker']}")
                continue
            if ticker["needs_prefix"]:
                query = f"${ticker['ticker']} since:{seven_days_ago} {lang()}".strip()
            else:
                query = f"{ticker['ticker']} since:{seven_days_ago} {lang()}".strip()
            print(f"Scraping posts for ticker: {ticker['ticker']}")
            cursor = None
            call_count = 0
            scrape_start_time = datetime.now(timezone.utc)
            while call_count < args.limit_calls:
                try:
                    params = {"q": query, "product": "Latest"}
                    if cursor:
                        params["cursor"] = cursor
                    response = requests.get(
                        "https://api.getxapi.com/twitter/tweet/advanced_search",
                        params=params,
                        headers={"Authorization": "Bearer " + getXAPI_key},
                    )
                    call_count += 1
                    data = response.json()
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
                    if args.all == False:
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


def lang():
    if args.lang == "all":
        return ""
    else:
        return f"lang:{args.lang}"


if __name__ == "__main__":
    posts = scrape_posts()
    print(f"Scraped {len(posts)} posts.")
    # Save the posts to a JSON file
    output_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "posts.json",
    )
    with open(output_file, "w") as f:
        json.dump(posts, f, indent=4)
    print(f"Saved posts to {output_file}")
