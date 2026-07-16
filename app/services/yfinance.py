import yfinance as yf
from datetime import datetime, timedelta


def get_stock_data(ticker, start_date):
    data = yf.download(
        ticker, start=start_date, end=start_date + timedelta(days=95), interval="1mo"
    )

    if data.empty:
        return None

    close_prices = data["Close"]
    if hasattr(close_prices, "columns"):
        close_prices = close_prices[ticker]
        
    prices = {}
    labels = ["day_0", "day_30", "day_60", "day_90"]
    for i, label in enumerate(labels):
        if i < len(close_prices):
            prices[label] = float(close_prices.iloc[i])
        else:
            prices[label] = None
    return prices
