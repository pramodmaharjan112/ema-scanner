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

STOCKS = ["AAPL", "NVDA", "TSLA", "MSFT", "META", "AMZN","SOFI","NOK"]

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
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=10
        )

        print("Telegram:", response.text)

    except Exception as e:
        print("Telegram Error:", e)


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

    # Flatten columns if MultiIndex exists
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"]

    # Force Series (very important fix)
    close = pd.Series(close).squeeze()

    close = close.astype(float).dropna()

    if close.ndim != 1:
        close = close.values.ravel()
        close = pd.Series(close)

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    rsi = RSIIndicator(close=close, window=14).rsi()

    return close, ema9, ema21, rsi


# ======================
# SIGNAL ENGINE
# ======================
def check_ema(symbol, state):

    try:

        df = yf.download(
            symbol,
            interval="5m",
            period="1d",
            progress=False,
            auto_adjust=True
        )

        if df.empty:
            print(symbol, "No data")
            return

        close, ema9, ema21, rsi = calculate_indicators(df)

        if len(close) < 30:
            print(symbol, "Not enough data")
            return

        prev9 = ema9.iloc[-2]
        curr9 = ema9.iloc[-1]

        prev21 = ema21.iloc[-2]
        curr21 = ema21.iloc[-1]

        curr_rsi = rsi.iloc[-1]

        price = round(float(close.iloc[-1]), 2)

        last_signal = state.get(symbol, "NONE")

        # BUY
        if (
            prev9 < prev21
            and curr9 > curr21
            and curr_rsi > 50
            and curr_rsi < 70
        ):

            if last_signal != "BUY":

                send_message(
                    f"🟢 BUY SIGNAL\n\n"
                    f"Stock: {symbol}\n"
                    f"Price: ${price}\n"
                    f"RSI: {round(curr_rsi, 2)}\n"
                    f"EMA9 crossed ABOVE EMA21"
                )

                state[symbol] = "BUY"

        # SELL
        elif (
            prev9 > prev21
            and curr9 < curr21
            and curr_rsi < 50
            and curr_rsi > 30
        ):

            if last_signal != "SELL":

                send_message(
                    f"🔴 SELL SIGNAL\n\n"
                    f"Stock: {symbol}\n"
                    f"Price: ${price}\n"
                    f"RSI: {round(curr_rsi, 2)}\n"
                    f"EMA9 crossed BELOW EMA21"
                )

                state[symbol] = "SELL"

        else:
            print(symbol, "No strong signal")

    except Exception as e:
        print(symbol, "ERROR:", e)


# ======================
# MAIN
# ======================
def main():

    print("PRO Trading Bot Started")

    print("Telegram token set:", bool(TELEGRAM_TOKEN))
    print("Chat ID set:", bool(CHAT_ID))

    state = load_state()

    for stock in STOCKS:
        check_ema(stock, state)

    save_state(state)


if __name__ == "__main__":
    main()
