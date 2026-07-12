from app.database import get_db
from app.models.ticker import Ticker
from datetime import datetime, timezone


def store_tickers(tickers, db_session):
    for ticker in tickers:
        existing_ticker = (
            db_session.query(Ticker).filter_by(ticker=ticker["ticker"]).first()
        )
        if existing_ticker is None:
            new_ticker = Ticker(
                ticker=ticker["ticker"],
                company_name=ticker["company_name"],
                exchange=ticker["exchange"],
                is_active=ticker["is_active"],
                flag_reason=ticker["flag_reason"],
                needs_prefix=ticker["needs_prefix"],
                first_seen=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
            )
            db_session.add(new_ticker)
        else:
            existing_ticker.company_name = ticker["company_name"]
            existing_ticker.exchange = ticker["exchange"]
            existing_ticker.is_active = ticker["is_active"]
            existing_ticker.flag_reason = ticker["flag_reason"]
            existing_ticker.needs_prefix = ticker["needs_prefix"]
            existing_ticker.last_updated = datetime.now(timezone.utc)
    db_session.commit()


def main():
    from app.pipeline.clean_tickers import clean_tickers
    from app.pipeline.fetch_tickers import fetch_tickers
    import os
    import argparse

    argument_parser = argparse.ArgumentParser(
        description="Store tickers in the database."
    )
    argument_parser.add_argument(
        "--tickers_list",
        type=str,
        default=None,
        help="A JSON file in the data folder containing a list of tickers to store in the database.",
    )
    args = argument_parser.parse_args()
    db_session = next(get_db())
    if args.tickers_list:
        import json

        BASE_DIR = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        with open(os.path.join(BASE_DIR, "data", args.tickers_list)) as f:
            tickers = json.load(f)
    else:
        tickers = clean_tickers(fetch_tickers())
    try:
        store_tickers(tickers, db_session)
        print(f"Stored {len(tickers)} tickers in the ticker database.")
    except Exception as e:
        db_session.rollback()
        print(f"An error occurred while storing tickers: {e}")
        raise e
    finally:
        db_session.close()


if __name__ == "__main__":
    main()
