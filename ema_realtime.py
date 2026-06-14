import os
import requests
import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "META", "AMZN"]

STATE_FILE = "state.txt"


# ======================
# TELEGRAM
# ======================
def send_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Missing Telegram credentials")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


# ======================
# STATE
# ======================
def load_state():
    state = {}
    if not os.path.exists(STATE_FILE):
        return state

    with open(STATE_FILE, "r") as f:
        for line in f:
            if ":" in line:
                k, v = line.strip().split(":")
                state[k] = v
    return state


def save_state(state):
    with open(STATE_FILE, "w") as f:
        for k, v in state.items():
            f.write(f"{k}:{v}\n")


# ======================
# INDICATORS
# ======================
def calculate_indicators(df):
    close = df["Close"].astype(float)

    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()

    rsi = RSIIndicator(close, window=14).rsi()

    return ema9, ema21, rsi


# ======================
# SIGNAL ENGINE (PRO LOGIC)
# ======================
def check_ema(symbol, state):
    try:
        df = yf.download(symbol, interval="5m", period="1d", progress=False)

        if df is None or df.empty:
            print(symbol, "no data")
            return

        if len(df) < 50:
            print(symbol, "not enough data")
            return

        ema9, ema21, rsi = calculate_indicators(df)

        prev9, curr9 = ema9.iloc[-2], ema9.iloc[-1]
        prev21, curr21 = ema21.iloc[-2], ema21.iloc[-1]
        curr_rsi = rsi.iloc[-1]

        price = round(float(df["Close"].iloc[-1]), 2)

        last_signal = state.get(symbol, "NONE")

        # ======================
        # STRONG BUY SIGNAL
        # ======================
        buy_condition = (
            prev9 < prev21 and
            curr9 > curr21 and
            curr_rsi > 50 and
            curr_rsi < 70
        )

        # ======================
        # STRONG SELL SIGNAL
        # ======================
        sell_condition = (
            prev9 > prev21 and
            curr9 < curr21 and
            curr_rsi < 50 and
            curr_rsi > 30
        )

        # BUY
        if buy_condition and last_signal != "BUY":
            send_message(
                f"🟢 STRONG BUY SIGNAL\n{symbol}\nPrice: {price}\nRSI: {round(curr_rsi,2)}"
            )
            state[symbol] = "BUY"

        # SELL
        elif sell_condition and last_signal != "SELL":
            send_message(
                f"🔴 STRONG SELL SIGNAL\n{symbol}\nPrice: {price}\nRSI: {round(curr_rsi,2)}"
            )
            state[symbol] = "SELL"

        else:
            print(symbol, "no strong signal")

    except Exception as e:
        print(symbol, "ERROR:", e)


# ======================
# MAIN
# ======================
def main():
    print("PRO Trading Bot Started")

    send_message("🚀 Pro EMA Bot Started")

    state = load_state()

    for stock in STOCKS:
        check_ema(stock, state)

    save_state(state)


if __name__ == "__main__":
    main()
