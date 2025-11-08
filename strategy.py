"""
Strategy Process

Reads latest prices from shared memory (written by OrderBook),
connects to the Gateway's news feed to receive sentiment, and
sends orders to the OrderManager based on a pluggable strategy
function.
"""

import socket
import time
import json
from statistics import mean

# --- Make the "Play Button" work ---
import sys
import os
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(current_file_path)
sys.path.insert(0, project_root)
# --- End of fix ---

from shared_memory_utils import SharedPriceBook
from network_utils import send_message, receive_messages
from config import (
    HOST,
    NEWS_PORT,
    ORDER_PORT,
    SHARED_MEMORY_NAME,
    SYMBOLS,
    SHORT_WINDOW,
    LONG_WINDOW,
    BULLISH_THRESHOLD,
    BEARISH_THRESHOLD,
    TRADE_QUANTITY,  # add this in config.py
)


def ma_news_strategy_decision(
    price_history,
    price,
    sentiment,
    position,
    short_window=SHORT_WINDOW,
    long_window=LONG_WINDOW,
    bullish_threshold=BULLISH_THRESHOLD,
    bearish_threshold=BEARISH_THRESHOLD,
):
    """
    Moving average crossover + news sentiment strategy.

    Returns:
        None if no action should be taken, or a dict:
            {
                "side": "BUY" or "SELL",
                "desired_position": "LONG" or "SHORT",
                "reason": "text explanation"
            }
    """

    if len(price_history) < long_window:
        return None

    short_ma = mean(price_history[-short_window:])
    long_ma_val = mean(price_history[-long_window:])

    if short_ma > long_ma_val:
        price_signal = "BUY"
    elif short_ma < long_ma_val:
        price_signal = "SELL"
    else:
        price_signal = "HOLD"

    if sentiment > bullish_threshold:
        news_signal = "BUY"
    elif sentiment < bearish_threshold:
        news_signal = "SELL"
    else:
        news_signal = "HOLD"

    print(
        f"[Strategy] price={price:.2f}, short_ma={short_ma:.2f}, "
        f"long_ma={long_ma_val:.2f}, sentiment={sentiment}, "
        f"price_signal={price_signal}, news_signal={news_signal}, "
        f"position={position}"
    )

    if price_signal == "BUY" and news_signal == "BUY":
        desired_position = "LONG"
        side = "BUY"
        reason = "Both price and news signals indicate BUY"
    elif price_signal == "SELL" and news_signal == "SELL":
        desired_position = "SHORT"
        side = "SELL"
        reason = "Both price and news signals indicate SELL"
    else:
        return None

    if position == desired_position:
        print("[Strategy] Desired position matches current position. No new order.")
        return None

    return {
        "side": side,
        "desired_position": desired_position,
        "reason": reason,
    }


def run_strategy():
    """
    Orchestration function for the Strategy process.

    - Attaches to shared memory
    - Connects to news feed and OrderManager
    - Maintains price history and position
    - On each news tick:
        * reads latest price
        * calls ma_news_strategy_decision
        * if decision exists, sends an order
    """

    print("[Strategy] Starting...")

    if not SYMBOLS:
        print("[Strategy] No symbols configured in SYMBOLS. Exiting.")
        return

    trade_symbol = SYMBOLS[0]
    print(f"[Strategy] Trading symbol: {trade_symbol}")

    # Attach to shared memory
    try:
        book = SharedPriceBook(name=SHARED_MEMORY_NAME, create=False)
    except FileNotFoundError:
        print(f"[Strategy] Shared memory '{SHARED_MEMORY_NAME}' not found. Is OrderBook running?")
        return

    print(f"[Strategy] Attached to SharedPriceBook '{SHARED_MEMORY_NAME}'.")

    # Connect to news feed once
    try:
        news_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        news_socket.connect((HOST, NEWS_PORT))
        print(f"[Strategy] Connected to news feed at {HOST}:{NEWS_PORT}.")
    except OSError as e:
        print(f"[Strategy] Could not connect to news feed: {e}")
        book.close()
        return

    # Connect to OrderManager once
    try:
        order_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        order_socket.connect((HOST, ORDER_PORT))
        print(f"[Strategy] Connected to OrderManager at {HOST}:{ORDER_PORT}.")
    except OSError as e:
        print(f"[Strategy] Could not connect to OrderManager: {e}")
        news_socket.close()
        book.close()
        return

    price_history = []
    position = None

    try:
        for news_msg in receive_messages(news_socket):
            try:
                sentiment_str = news_msg.decode("utf-8").strip()
                sentiment = int(sentiment_str)
            except ValueError:
                print(f"[Strategy] Could not parse sentiment from message: {news_msg!r}")
                continue

            price = book.read(trade_symbol)
            if price is None:
                print(f"[Strategy] No price available yet for {trade_symbol}. Skipping tick.")
                continue

            price = float(price)

            price_history.append(price)
            if len(price_history) > LONG_WINDOW:
                price_history.pop(0)

            decision = ma_news_strategy_decision(
                price_history=price_history,
                price=price,
                sentiment=sentiment,
                position=position,
            )

            if decision is None:
                continue

            side = decision["side"]
            desired_position = decision["desired_position"]
            reason = decision["reason"]

            short_ma = mean(price_history[-SHORT_WINDOW:])
            long_ma = mean(price_history[-LONG_WINDOW:])

            order = {
                "symbol": trade_symbol,
                "side": side,
                "quantity": TRADE_QUANTITY,
                "price": price,
                "sentiment": sentiment,
                "short_ma": short_ma,
                "long_ma": long_ma,
                "position_before": position,
                "position_after": desired_position,
                "reason": reason,
                "timestamp": time.time(),
            }

            try:
                order_bytes = json.dumps(order).encode("utf-8")
                send_message(order_socket, order_bytes)
                print(f"[Strategy] Sent order: {order}")
                position = desired_position
            except OSError as e:
                print(f"[Strategy] Error sending order: {e}")
                break

    finally:
        news_socket.close()
        order_socket.close()
        book.close()
        print("[Strategy] Closed connections and detached from shared memory.")


if __name__ == "__main__":
    run_strategy()
