# pip install streamlit plotly pandas requests streamlit-autorefresh

import time
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

BINANCE_URL = "https://api.binance.com/api/v3/klines"

def fetch_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    """
    Fetch OHLCV candlesticks from Binance.
    interval examples: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d
    """
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(BINANCE_URL, params=params, timeout=10)
    r.raise_for_status()
    raw = r.json()

    if not isinstance(raw, list) or len(raw) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(
        raw,
        columns=[
            "openTime","open","high","low","close","volume","closeTime",
            "qav","numTrades","takerBase","takerQuote","ignore"
        ],
    )

    # Convert types
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["openTime"]  = pd.to_datetime(df["openTime"],  unit="ms")
    df["closeTime"] = pd.to_datetime(df["closeTime"], unit="ms")
    return df


# -------------------- UI --------------------
st.set_page_config(page_title="BTC Candles (Live)", layout="wide")
st.title("🟠 BTC Candlestick — Live (Binance REST)")

col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
with col1:
    symbol = st.text_input("Symbol (Binance)", value="BTCUSDT").upper()
with col2:
    interval = st.selectbox(
        "Candle Interval",
        ["1m", "3m", "5m", "15m", "30m", "1h"],
        index=0,
        help="Binance native intervals (e.g., 1m = 1 minute).",
    )
with col3:
    history = st.slider("Candles Shown", min_value=50, max_value=1000, value=200, step=50)
with col4:
    # 5 seconds is a safe, conservative refresh to avoid rate limits.
    refresh_s = st.number_input("Refresh (sec)", min_value=5, max_value=60, value=5, step=1)

# Auto-refresh the app every refresh_s seconds (no deprecated APIs)
st_autorefresh(interval=refresh_s * 1000, key="data_refresh")
st.caption(f"Auto-refreshing every {refresh_s} seconds…")

# -------------------- Data & Chart --------------------
try:
    df = fetch_klines(symbol, interval, limit=history)

    if df.empty:
        st.warning("No data returned. Try a different symbol or interval.")
    else:
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["openTime"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    name=f"{symbol} {interval}",
                )
            ]
        )
        fig.update_layout(
            height=620,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Metrics
        last = df.iloc[-1]
        prev_close = df.iloc[-2]["close"] if len(df) > 1 else last["close"]
        st.metric(
            label=f"Last Close ({symbol})",
            value=f"{last['close']:.2f}",
            delta=f"{(last['close'] - prev_close):.2f}",
        )

        # Optional details
        with st.expander("Latest Candle Details"):
            st.write(
                {
                    "Open Time": last["openTime"],
                    "Close Time": last["closeTime"],
                    "Open": float(last["open"]),
                    "High": float(last["high"]),
                    "Low": float(last["low"]),
                    "Close": float(last["close"]),
                    "Volume": float(last["volume"]),
                    "Trades": int(last["numTrades"]),
                }
            )

    st.write("Created by Can Kocyigitoglu")

except requests.HTTPError as e:
    st.error(f"HTTP error: {e}")
except requests.RequestException as e:
    st.error(f"Network error: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
