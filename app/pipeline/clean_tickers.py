import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open(os.path.join(BASE_DIR, "data/common_words.json")) as f:
    COMMON_WORDS = json.load(f)
SPECIAL_CHARACTERS = set("!@#$%^&*()_+-=[]{}|;:'\",.<>?/`~")


def clean_tickers(tickers):
    cleaned_tickers = []

    for ticker in tickers:
        symbol = ticker["symbol"]
        is_active = True
        flag_reason = None
        needs_prefix = False

        if len(ticker["symbol"]) == 1:
            flag_reason = "Single character symbol"
            needs_prefix = True

        elif len(ticker["symbol"]) > 5:
            is_active = False
            flag_reason = "Symbol longer than 5 characters"

        elif ticker["symbol"] in COMMON_WORDS:
            flag_reason = "Symbol is a common word"
            needs_prefix = True

        elif "." in ticker["symbol"]:
            is_active = False
            flag_reason = "Ticker is not a regular stock (contains a dot)"
        elif any(char in symbol for char in SPECIAL_CHARACTERS):
            is_active = False
            flag_reason = "Ticker contains special characters"

        cleaned_tickers.append(
            {
                "ticker": ticker["symbol"].strip(),
                "company_name": ticker["name"],
                "exchange": ticker["exchange"],
                "is_active": is_active,
                "flag_reason": flag_reason,
                "needs_prefix": needs_prefix,
            }
        )

    return cleaned_tickers


if __name__ == "__main__":
    from app.pipeline.fetch_tickers import fetch_tickers

    tickers = clean_tickers(fetch_tickers())
    with open(os.path.join(BASE_DIR, "data/cleaned_tickers.json"), "w") as f:
        json.dump(tickers, f, indent=4)
