"""
Data Gateway Process

Acts as a TCP server on two ports:
- Price Port: Streams random-walk price data.
- News Port: Streams random market sentiment data.

Uses threading to handle multiple clients and broadcast data concurrently.
"""

import socket
import threading
import time
import random

# --- Make the "Play Button" work ---
import sys
import os
current_file_path = os.path.abspath(__file__)
# Go up one level from the script to the project root
project_root = os.path.dirname(current_file_path) 
sys.path.insert(0, project_root)
# --- End of fix ---

from network_utils import send_message
from config import HOST, PRICE_PORT, NEWS_PORT, SYMBOLS

# --- Global Storage for Clients ---
# We need to store all connected clients so our broadcaster
# threads can send them data.
price_clients = []
price_clients_lock = threading.Lock()

news_clients = []
news_clients_lock = threading.Lock()

# Store the last price to create a "random walk"
current_prices = {symbol: random.uniform(100, 300) for symbol in SYMBOLS}
# ------------------------------------

tick_counter = 0
gateway_start_time = time.time()

def generate_price_data():
    """Generates a new random-walk price for each symbol."""
    global current_prices
    messages = []
    for symbol in SYMBOLS:
        # Create a small random change
        change = random.uniform(-0.5, 0.5)
        # Ensure price doesn't go negative
        current_prices[symbol] = max(0.01, current_prices[symbol] + change)
        # Format: "AAPL,150.23"
        messages.append(f"{symbol},{current_prices[symbol]:.2f}")
    
    # Join all messages with our delimiter: "AAPL,150.23*MSFT,310.45"
    return "*".join(messages)

def broadcast_prices():
    """
    Periodically generates and broadcasts price data to all
    connected price clients.
    """
    global tick_counter, gateway_start_time

    while True:
        try:
            time.sleep(1)  # You will change this to 0.1, 0.01 etc for throughput tests
            
            message_data = generate_price_data()
            if not message_data:
                continue

            with price_clients_lock:
                current_clients = list(price_clients)

            if not current_clients:
                print(f"[Gateway-Price] No price clients connected. Skipping broadcast.", end='\r')
                continue

            # Performance: timestamp before sending (t1) and tick count
            tick_counter += 1
            t1 = time.time()
            elapsed = t1 - gateway_start_time
            throughput = tick_counter / elapsed if elapsed > 0 else 0.0

            print(
                f"\n[Gateway-Perf] tick={tick_counter} t1={t1:.6f} "
                f"throughput_est={throughput:.2f} ticks/sec "
                f"msg={message_data}"
            )

            for client_socket in current_clients:
                try:
                    send_message(client_socket, message_data.encode('utf-8'))
                except (BrokenPipeError, ConnectionResetError):
                    print(f"\n[Gateway-Price] Client disconnected. Removing.")
                    with price_clients_lock:
                        if client_socket in price_clients:
                            price_clients.remove(client_socket)
                            client_socket.close()

        except Exception as e:
            print(f"\n[Gateway-Price] Error in broadcast: {e}")


def broadcast_news():
    """
    A thread target function.
    Periodically generates and broadcasts news sentiment to all
    connected news clients.
    """
    while True:
        try:
            time.sleep(3) # Broadcast news every 3 seconds
            
            # Generate a sentiment score from 0 to 100
            sentiment = random.randint(0, 100)
            message_data = str(sentiment)
            
            with news_clients_lock:
                current_clients = list(news_clients)
            
            if not current_clients:
                print(f"[Gateway-News] No news clients connected. Skipping broadcast.", end='\r')
                continue
                
            print(f"\n[Gateway-News] Broadcasting sentiment to {len(current_clients)} client(s): {message_data}")

            for client_socket in current_clients:
                try:
                    send_message(client_socket, message_data.encode('utf-8'))
                except (BrokenPipeError, ConnectionResetError):
                    print(f"\n[Gateway-News] Client disconnected. Removing.")
                    with news_clients_lock:
                        if client_socket in news_clients:
                            news_clients.remove(client_socket)
                            client_socket.close()

        except Exception as e:
            print(f"\n[Gateway-News] Error in broadcast: {e}")

def server_loop(port, client_list, lock, server_name):
    """
    A thread target function.
    Listens on a specific port and adds new clients to the
    appropriate list.
    """
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # This allows us to re-use the address (port) immediately after stopping the program
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, port))
        server_socket.listen(5)
        print(f"[{server_name}] Server is live, listening on {HOST}:{port}...")

        while True:
            # This line "blocks" (waits) until a client connects
            client_socket, client_address = server_socket.accept()
            
            # Safely add the new client to our shared list
            with lock:
                client_list.append(client_socket)
            
            print(f"\n[{server_name}] Client connected from {client_address}. Total clients: {len(client_list)}")

    except OSError as e:
        print(f"[{server_name}] Socket error: {e}")
    finally:
        if server_socket:
            server_socket.close()

def run_gateway():
    """
Setting up 'gateway.py' - This file acts as the central data broadcaster for our trading system.
    """
    print("[Gateway] Starting all services...")
    
    # --- Create our 4 threads ---
    
    # 1. Price Acceptor Thread
    price_server_thread = threading.Thread(
        target=server_loop, 
        args=(PRICE_PORT, price_clients, price_clients_lock, "Gateway-Price"),
        daemon=True # Run as background thread
    )
    
    # 2. News Acceptor Thread
    news_server_thread = threading.Thread(
        target=server_loop, 
        args=(NEWS_PORT, news_clients, news_clients_lock, "Gateway-News"),
        daemon=True
    )
    
    # 3. Price Broadcaster Thread
    price_broadcast_thread = threading.Thread(
        target=broadcast_prices,
        daemon=True
    )
    
    # 4. News Broadcaster Thread
    news_broadcast_thread = threading.Thread(
        target=broadcast_news,
        daemon=True
    )

    # --- Start all threads ---
    price_server_thread.start()
    news_server_thread.start()
    price_broadcast_thread.start()
    news_broadcast_thread.start()
    
    print("[Gateway] All services running.")
    
    # Keep the main thread alive.
    # If the main thread exits, all daemon threads stop.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Gateway] Shutting down...")
        # Threads are daemons, so they will exit automatically

if __name__ == "__main__":
    run_gateway()