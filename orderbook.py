"""
Order Book Process

Connects to the Gateway's price feed as a TCP client.
It is the *creator* of the SharedPriceBook.
It receives price data, parses it, and updates the shared memory
for the Strategy process to read.
"""

import socket
import time

# --- Make the "Play Button" work ---
import sys
import os
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(current_file_path)
sys.path.insert(0, project_root)
# --- End of fix ---

from network_utils import receive_messages
from shared_memory_utils import SharedPriceBook
from config import HOST, PRICE_PORT, SHARED_MEMORY_NAME, SYMBOLS

def run_orderbook():
    """
    Main function for the OrderBook.
    - Creates the SharedPriceBook
    - Connects to the Gateway's price feed
    - Loops forever, updating shared memory with new prices
    """
    
    print("[OrderBook] Starting...")
    book = None
    client_socket = None

    try:
        # 1. Create the SharedPriceBook (as the creator)
        # This is the "bulletin board"
        book = SharedPriceBook(name=SHARED_MEMORY_NAME, create=True)
        print(f"[OrderBook] SharedPriceBook '{SHARED_MEMORY_NAME}' created.")
        
        while True: # Main loop for connection retries
            try:
                # 2. Connect to the Gateway's price feed
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print(f"[OrderBook] Attempting to connect to Gateway at {HOST}:{PRICE_PORT}...")
                client_socket.connect((HOST, PRICE_PORT))
                print("[OrderBook] Connected to Gateway price feed.")

                # 3. Loop forever, receiving and processing messages
                # Our utility function handles all the buffering
                for message_block in receive_messages(client_socket):
                    
                    # The Gateway sends all symbols in one block, e.g. "AAPL,150*MSFT,300"
                    # We must split them by the delimiter (which is also '*')
                    # This is a bit of a quirk since our delimiter is also the separator.
                    # A better protocol would use a different separator, but this works.
                    
                    # receive_messages() already yields one message at a time.
                    # But our gateway *builds* one message with delimiters inside it.
                    # Let's handle both cases.
                    
                    try:
                        decoded_block = message_block.decode('utf-8')
                        
                        # Split by '*' just in case gateway sent "AAPL,150*MSFT,300"
                        # as a single message payload (which it does)
                        individual_updates = decoded_block.split('*')
                        
                        for update_str in individual_updates:
                            if not update_str:
                                continue
                                
                            # Parse the individual "SYMBOL,PRICE" string
                            symbol, price_str = update_str.split(',')
                            price = float(price_str)
                            
                            # 4. Update the "bulletin board"
                            book.update(symbol, price)
                            print(f"[OrderBook] Updated {symbol} -> ${price:.2f}", end=' | ')
                        
                        print() # Newline after a full batch of updates

                    except (ValueError, IndexError) as e:
                        print(f"\n[OrderBook] Error parsing data: {e}. Data: '{message_block}'")
                    except Exception as e:
                        print(f"\n[OrderBook] Generic error processing message: {e}")

            except ConnectionRefusedError:
                print("[OrderBook] Connection refused. Is Gateway running? Retrying in 5s...")
                time.sleep(5)
            except (ConnectionResetError, BrokenPipeError):
                print("[OrderBook] Gateway disconnected. Retrying in 5s...")
                time.sleep(5)
            except Exception as e:
                print(f"[OrderBook] An unexpected error occurred: {e}. Retrying in 5s...")
                time.sleep(5)
            finally:
                if client_socket:
                    client_socket.close()
                    client_socket = None # Ensure we create a new socket
    
    except KeyboardInterrupt:
        print("\n[OrderBook] Shutting down...")
    finally:
        # 5. CRITICAL: Clean up the shared memory
        if book:
            print("[OrderBook] Unlinking shared memory...")
            book.unlink() # Destroy the "bulletin board"
            book.close()
            print("[OrderBook] Closed.")
        if client_socket:
            client_socket.close()

if __name__ == "__main__":
    run_orderbook()