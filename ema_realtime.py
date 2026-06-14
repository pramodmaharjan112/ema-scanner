import os
import requests
import yfinance as yf
import pandas as pd

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "META", "AMZN"]

STATE_FILE = "state.txt"


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        lines = f.read().splitlines()
    return dict(line.split(":") for line in lines if ":" in line)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        for k, v in state.items():
            f.write(f"{k}:{v}\n")


def check_ema(symbol, state):
    df = yf.download(
        symbol,
        interval="5m",
        period="1d",
        progress=False
    )

    if len(df) < 30:
        return

    close = df["Close"]

    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()

    prev9, curr9 = ema9.iloc[-2], ema9.iloc[-1]
    prev21, curr21 = ema21.iloc[-2], ema21.iloc[-1]

    price = round(float(close.iloc[-1]), 2)

    last_signal = state.get(symbol, "NONE")

    # BUY CROSS
    if prev9 < prev21 and curr9 > curr21:
        if last_signal != "BUY":
            send_message(f"🟢 BUY {symbol}\nEMA9 crossed above EMA21\nPrice: {price}")
            state[symbol] = "BUY"

    # SELL CROSS
    elif prev9 > prev21 and curr9 < curr21:
        if last_signal != "SELL":
            send_message(f"🔴 SELL {symbol}\nEMA9 crossed below EMA21\nPrice: {price}")
            state[symbol] = "SELL"


def main():
    def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text
        }
    )

    print("Telegram response:", response.text)
    state = load_state()

    for stock in STOCKS:
        try:
            check_ema(stock, state)
        except Exception as e:
            print(stock, e)

    save_state(state)


if __name__ == "__main__":
    main()
