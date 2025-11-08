"""
Central configuration file for the trading system.

Stores all shared constants like host, ports, and message delimiters
to ensure all components use the same settings.
"""

import os

# --- Network Settings ---
# Use '0.0.0.0' to allow connections from other machines in the network
# Use '127.0.0.1' (localhost) to only allow connections from this machine
HOST = '127.0.0.1'

# Port for the Gateway to broadcast price data
PRICE_PORT = 9000

# Port for the Gateway to broadcast news sentiment data
NEWS_PORT = 9001

# Port for the Strategy to send orders to the OrderManager
ORDER_PORT = 9002

# --- Message Protocol ---
# A consistent delimiter to mark the end of one message and the start of another.
# We use a single byte that is unlikely to appear in the data itself.
MESSAGE_DELIMITER = b'*'

# --- Shared Memory Settings ---
# A unique name for the shared memory block
# We use an environment variable or a default
SHARED_MEMORY_NAME = os.environ.get('TRADING_SHM_NAME', 'trading_system_shm')

# List of symbols to track in the order book
# Keeping this in config makes it easy to add/remove symbols
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

# --- Strategy Settings ---
SHORT_WINDOW = 5  # Short moving average window
LONG_WINDOW = 20  # Long moving average window
BULLISH_THRESHOLD = 70  # Sentiment score > 70 is bullish
BEARISH_THRESHOLD = 30  # Sentiment score < 30 is bearish
TRADE_QUANTITY = 10  # Quantity of shares to trade