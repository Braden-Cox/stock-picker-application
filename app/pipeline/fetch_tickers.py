import requests


def fetch_tickers():
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    API_URLS = {
        "nasdaq": "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&exchange=nasdaq",
        "nyse": "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&exchange=nyse",
    }

    nasdaq = requests.get(API_URLS["nasdaq"], headers=HEADERS)
    nyse = requests.get(API_URLS["nyse"], headers=HEADERS)

    nasdaq_data = nasdaq.json()
    nyse_data = nyse.json()
    tickers = []

    for row in nasdaq_data["data"]["table"]["rows"]:
        tickers.append(
            {"symbol": row["symbol"].strip(), "name": row["name"], "exchange": "NASDAQ"}
        )

    for row in nyse_data["data"]["table"]["rows"]:
        tickers.append(
            {"symbol": row["symbol"].strip(), "name": row["name"], "exchange": "NYSE"}
        )

    return tickers


if __name__ == "__main__":
    tickers = fetch_tickers()
    print(tickers)
