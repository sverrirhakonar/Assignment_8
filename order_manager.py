"""
Order Manager Process

Acts as a TCP server, listening for order messages from the
Strategy process. It deserializes and logs any orders it receives.
"""

import socket
import json
import threading

# --- Make the "Play Button" work ---
import sys
import os
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(current_file_path)
sys.path.insert(0, project_root)
# --- End of fix ---

from network_utils import receive_messages
from config import HOST, ORDER_PORT

def handle_client(client_socket: socket.socket):
    """
    Handles a single client connection in a separate thread.
    Listens for messages, deserializes them, and logs them.
    """
    print(f"[OrderManager] Client connected from {client_socket.getpeername()}")
    
    # Use our reliable message receiver
    # This loop will run until the client disconnects
    for message in receive_messages(client_socket):
        try:
            # Assume the message is JSON, decode it from bytes
            order = json.loads(message.decode('utf-8'))
            
            # Log the trade confirmation
            print("\n" + "=" * 30)
            print(f"[OrderManager] Received Trade:")
            print(f"  Symbol: {order.get('symbol')}")
            print(f"  Side:   {order.get('side')}")
            print(f"  Price:  ${order.get('price'):.2f}")
            print(f"  Qty:    {order.get('quantity')}")
            print(f"  Reason: {order.get('reason')}")
            print("=" * 30 + "\n")
            
        except json.JSONDecodeError:
            print(f"[OrderManager] Received malformed data: {message}")
        except Exception as e:
            print(f"[OrderManager] Error processing message: {e}")

def run_ordermanager():
    """
    Starts the Order Manager server.
    Listens for connections and spawns a thread for each client.
    """
    server_socket = None
    try:
        # Create a TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # This allows us to reuse the address if we restart the server quickly
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to our host and port
        server_socket.bind((HOST, ORDER_PORT))
        
        # Start listening for connections (allow up to 5 in the queue)
        server_socket.listen(5)
        
        print(f"[OrderManager] Server is live, listening on {HOST}:{ORDER_PORT}...")
        
        while True:
            # Wait for a new client to connect
            # This line "blocks" (pauses) until a connection happens
            client_socket, client_address = server_socket.accept()
            
            # When a client connects, create a new thread to handle it.
            # This way, we can handle multiple strategies at once
            # without the main server loop getting stuck.
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket,)
            )
            client_thread.daemon = True # Run as a background thread
            client_thread.start()
            
    except OSError as e:
        print(f"[OrderManager] Socket error: {e}")
    except KeyboardInterrupt:
        print("\n[OrderManager] Shutting down...")
    finally:
        if server_socket:
            print("[OrderManager] Closing server socket.")
            server_socket.close()

if __name__ == "__main__":
    run_ordermanager()