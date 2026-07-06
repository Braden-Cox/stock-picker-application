import yfinance as yf
from datetime import datetime, timedelta

def get_stock_data(ticker, start_date):
    data = yf.download(ticker, start=start_date, end=start_date + timedelta(days=95), interval="1mo")
    
    if data.empty:
        return None
    
    else:
        prices = {}
        labels = ["day_0", "day_30", "day_60", "day_90"]
        for i, label in enumerate(labels):
            if i < len(data):
                prices[label] = data["Close"].iloc[i]
            else:
                prices[label] = None
        return prices