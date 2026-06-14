import os
import requests
import yfinance as yf
import pandas as pd

# ======================
# CONFIG
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "META", "AMZN"]

STATE_FILE = "state.txt"


# ======================
# TELEGRAM SENDER
# ======================
def send_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Missing Telegram credentials")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
        print("Telegram response:", response.text)
    except Exception as e:
        print("Telegram error:", e)


# ======================
# STATE HANDLING
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
# EMA CHECK
# ======================
def check_ema(symbol, state):
    try:
        df = yf.download(
            symbol,
            interval="5m",
            period="1d",
            progress=False
        )

        if df is None or df.empty:
            print(symbol, "no data")
            return

        # FIX: force clean series
        close = df["Close"]

# force it into 1D clean series no matter what yfinance returns
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]

close = close.dropna().astype(float)

        if len(close) < 30:
            print(symbol, "not enough data")
            return

        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()

        prev9, curr9 = ema9.iloc[-2], ema9.iloc[-1]
        prev21, curr21 = ema21.iloc[-2], ema21.iloc[-1]

        price = round(float(close.values[-1]), 2)

        last_signal = state.get(symbol, "NONE")

        # ======================
        # BUY SIGNAL
        # ======================
        if prev9 < prev21 and curr9 > curr21:
            if last_signal != "BUY":
                send_message(
                    f"🟢 BUY SIGNAL\n{symbol}\nEMA9 crossed ABOVE EMA21\nPrice: {price}"
                )
                state[symbol] = "BUY"

        # ======================
        # SELL SIGNAL
        # ======================
        elif prev9 > prev21 and curr9 < curr21:
            if last_signal != "SELL":
                send_message(
                    f"🔴 SELL SIGNAL\n{symbol}\nEMA9 crossed BELOW EMA21\nPrice: {price}"
                )
                state[symbol] = "SELL"

        else:
            print(symbol, "no crossover")

    except Exception as e:
        print(symbol, "ERROR:", e)


# ======================
# MAIN
# ======================
def main():
    print("EMA Bot Started")

    print("Telegram token set:", bool(TELEGRAM_TOKEN))
    print("Chat ID set:", bool(CHAT_ID))
    
        # ✅ TEST MESSAGE (ADD THIS)
    send_message("🧪 TEST: EMA bot Telegram is working")

    state = load_state()

    for stock in STOCKS:
        check_ema(stock, state)

    save_state(state)


if __name__ == "__main__":
    main()
