"""
Unit test for network_utils.py
"""

import unittest
import socket
import threading
import time

# --- This is the new part to make the Play Button work ---
import sys
import os

# Get the path of the current file (e.g., .../Assignment_8/tests/test_network_utils.py)
current_file_path = os.path.abspath(__file__)

# Get the directory of the current file (e.g., .../Assignment_8/tests)
tests_dir = os.path.dirname(current_file_path)

# Get the parent directory (the 'Assignment_8' project root)
project_root = os.path.dirname(tests_dir)

# Add the project root to Python's "search path"
sys.path.insert(0, project_root)
# --- End of new part ---


# Change this line back:
from network_utils import send_message, receive_messages
# Not: from ..network_utils import ...

from config import MESSAGE_DELIMITER
# And change this line back:
# Not: from ..config import ...


# Use a specific port for testing
TEST_HOST = '127.0.0.1'
TEST_PORT = 9999

class TestNetworkUtils(unittest.TestCase):

    def setUp(self):
        """Set up the server in a separate thread for each test."""
        self.server_socket = None
        self.client_socket = None
        self.server_thread = None
        self.received_messages = []  # List to store messages received by the server
        self.server_ready_event = threading.Event()
        self.stop_server_event = threading.Event()

    def tearDown(self):
        """Clean up all sockets and threads."""
        self.stop_server_event.set()
        
        # We connect to the server one last time to unblock the .accept()
        # This helps shut down the server thread cleanly
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((TEST_HOST, TEST_PORT))
        except ConnectionRefusedError:
            pass # Server was already down, which is fine

        if self.server_thread:
            self.server_thread.join(timeout=2) # Wait for thread to finish
            
        if self.client_socket:
            self.client_socket.close()
            
        if self.server_socket:
            self.server_socket.close()

    def _server_thread_target(self):
        """
        This function runs in a separate thread.
        It's a mini-server that listens for one connection,
        receives messages, and stores them.
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # This allows us to re-use the port quickly after a test
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((TEST_HOST, TEST_PORT))
            self.server_socket.listen(1)
            
            # Signal that the server is ready to accept connections
            self.server_ready_event.set()
            
            # Wait for a client to connect
            # Set a timeout so it can check the stop_server_event
            self.server_socket.settimeout(1.0)
            
            client_conn = None
            while not self.stop_server_event.is_set():
                try:
                    client_conn, addr = self.server_socket.accept()
                    # We got a connection, break the loop
                    break 
                except socket.timeout:
                    continue # Loop again to check stop_server_event

            if client_conn:
                # Once connected, loop and receive messages
                print("Test server: Client connected.")
                for msg in receive_messages(client_conn):
                    self.received_messages.append(msg)
                print("Test server: Client disconnected.")
                client_conn.close()
                
        except Exception as e:
            if not self.stop_server_event.is_set():
                print(f"Test server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            self.server_ready_event.set() # Ensure main thread isn't blocked if setup fails

    def test_send_and_receive_messages(self):
        """
        The main test case.
        1. Starts the server thread.
        2. Connects as a client.
        3. Sends multiple messages.
        4. Verifies the server received them correctly.
        """
        # 1. Start the server thread
        self.server_thread = threading.Thread(target=self._server_thread_target)
        self.server_thread.start()
        
        # Wait for the server to be ready (up to 5 seconds)
        ready = self.server_ready_event.wait(timeout=5)
        self.assertTrue(ready, "Server thread did not start up in time.")

        # 2. Connect as a client
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((TEST_HOST, TEST_PORT))

        # 3. Send multiple messages
        messages_to_send = [
            b"AAPL,150.00",
            b"MSFT,320.50",
            b"A very long message with lots of text" * 10
        ]
        
        for msg in messages_to_send:
            send_message(self.client_socket, msg)
            time.sleep(0.01) # Small delay to be realistic

        # 4. Close the client socket (this signals the server to stop)
        self.client_socket.close()
        self.client_socket = None

        # Wait for the server thread to finish processing
        self.server_thread.join(timeout=5)

        # 5. Verify the server received the messages correctly
        self.assertEqual(len(self.received_messages), len(messages_to_send))
        self.assertEqual(self.received_messages, messages_to_send)
        print("TestNetworkUtils: All messages received correctly.")

if __name__ == '__main__':
    unittest.main()