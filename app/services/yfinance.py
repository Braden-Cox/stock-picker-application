import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# Horizons measured in calendar days from the post timestamp.
OFFSETS = {"day_0": 0, "day_30": 30, "day_60": 60, "day_90": 90}

# If the nearest available trading day is further than this from the target
# date, treat the horizon as missing rather than silently using a stale price.
MAX_STALENESS_DAYS = 7


def _to_naive_datetime(value):
    """Accept a datetime, date, or string and return a tz-naive UTC datetime.

    Returns None if the value can't be parsed. This exists because posts.timestamp
    may be stored as a varchar containing X's raw createdAt string.
    """
    if value is None:
        return None

    if isinstance(value, str):
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(parsed):
            return None
        value = parsed.to_pydatetime()

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    # datetime.date and anything pandas can coerce
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    parsed = parsed.to_pydatetime()
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _close_series(data, ticker):
    """Pull a single Close price Series out of a yfinance download result."""
    if "Close" not in data:
        return None

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        if ticker in close.columns:
            close = close[ticker]
        elif close.shape[1] == 1:
            close = close.iloc[:, 0]
        else:
            return None

    close = close.dropna()
    if close.empty:
        return None

    # Normalise the index to tz-naive so it can be compared against naive targets.
    if getattr(close.index, "tz", None) is not None:
        close.index = close.index.tz_localize(None)

    return close.sort_index()


def get_stock_data(ticker, start_date):
    """Return closing prices at ~0/30/60/90 days after start_date.

    Returns None if no usable price data exists for this ticker and window.
    Individual horizons may be None if that far out isn't available yet.
    """
    start = _to_naive_datetime(start_date)
    if start is None:
        return None

    # Pad the front so day_0 resolves even if the post lands on a weekend or
    # holiday, and the back so day_90 has room.
    data = yf.download(
        ticker,
        start=start - timedelta(days=7),
        end=start + timedelta(days=100),
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data is None or data.empty:
        return None

    close = _close_series(data, ticker)
    if close is None:
        return None

    prices = {}
    for label, offset in OFFSETS.items():
        target = start + timedelta(days=offset)
        eligible = close.loc[:target]
        if eligible.empty:
            prices[label] = None
            continue

        last_ts = eligible.index[-1].to_pydatetime()
        if (target - last_ts).days > MAX_STALENESS_DAYS:
            prices[label] = None
            continue

        prices[label] = float(eligible.iloc[-1])

    if prices.get("day_0") is None:
        return None

    return prices