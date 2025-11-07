"""
Network utility functions for the trading system.

Provides robust methods for sending and receiving messages over TCP sockets,
handling message framing with a custom delimiter.
"""

import socket
from config import MESSAGE_DELIMITER, HOST, PRICE_PORT, NEWS_PORT, ORDER_PORT

def send_message(sock: socket.socket, message: bytes):
    """
    Sends a message over a socket, appending a delimiter.
    
    Args:
        sock: The socket.socket object to send data through.
        message: The raw bytes to send (without delimiter).
        
    Raises:
        OSError: If the socket connection is broken or closed.
    """
    if not isinstance(message, bytes):
        raise TypeError(f"Message must be bytes, not {type(message)}")
        
    try:
        # Append the delimiter to frame the message
        sock.sendall(message + MESSAGE_DELIMITER)
    except OSError as e:
        print(f"Error sending message: {e}")
        # Re-raise the exception so the caller can handle it (e.g., disconnect client)
        raise

def receive_messages(sock: socket.socket, buffer_size: int = 4096):
    """
    A generator function to receive and parse messages from a socket.
    
    It handles partial messages, multiple messages in one chunk,
    and cleanly exits when the socket is closed.
    
    Args:
        sock: The socket.socket object to read data from.
        buffer_size: The number of bytes to read at a time.
        
    Yields:
        bytes: A single, complete message (without the delimiter).
    """
    # This buffer stores incomplete message parts
    buffer = b""
    
    try:
        while True:
            # Read a chunk of data from the socket
            chunk = sock.recv(buffer_size)
            
            if not chunk:
                # Socket was closed cleanly by the other side
                # If there's any leftover data in the buffer, it's an incomplete message.
                if buffer:
                    print(f"Incomplete message in buffer (socket closed): {buffer}")
                break # Exit the generator
                
            # Add the new chunk to our buffer
            buffer += chunk
            
            # Keep processing the buffer as long as our delimiter is in it
            while MESSAGE_DELIMITER in buffer:
                # Split at the *first* delimiter.
                # 'message' will be the complete message.
                # 'buffer' will be whatever is left *after* the first delimiter.
                message, buffer = buffer.split(MESSAGE_DELIMITER, 1)
                
                # 'yield' turns this function into a generator.
                # It "returns" the message to the caller,
                # but pauses here, ready to resume the next time.
                yield message
                
    except ConnectionResetError:
        print("Socket connection reset by peer.")
    except OSError as e:
        print(f"Error receiving data: {e}")
    finally:
        # This generator is done
        print("Socket closed or error. Exiting receive_messages.")
        sock.close()