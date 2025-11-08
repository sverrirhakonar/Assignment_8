"""
Defines the SharedPriceBook class for high-speed, inter-process
communication of market data using multiprocessing.shared_memory
and NumPy structured arrays.
"""

import numpy as np
import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
from config import SYMBOLS, SHARED_MEMORY_NAME

class SharedPriceBook:
    """
    A class that wraps a NumPy structured array in shared memory.
    This provides a high-performance way for the OrderBook to write
    price data and for the Strategy to read it.

    The structure is an array of:
    [ ('AAPL', 0.0), ('MSFT', 0.0), ... ]
    """
    def __init__(self, name=SHARED_MEMORY_NAME, create=False):
        """
        Initialize the SharedPriceBook.

        Args:
            name (str): The public name of the shared memory block.
            create (bool):
                - If True: Create a new shared memory block.
                  (Used by the OrderBook process)
                - If False: Attach to an existing block.
                  (Used by the Strategy process)
        """
        self.symbols = SYMBOLS
        self.symbol_to_index = {symbol: i for i, symbol in enumerate(self.symbols)}

        # Define the 'spreadsheet' structure:
        # 'S10' is a 10-byte string for the symbol
        # 'f8' is a 64-bit float (double) for the price
        self.dtype = [('symbol', 'S10'), ('price', 'f8')]
        self.num_symbols = len(self.symbols)

        # Calculate the total size needed for the array
        item_size = np.dtype(self.dtype).itemsize
        self.total_size_bytes = self.num_symbols * item_size

        # memory footprint
        approx_entry_bytes = 10 + 8  # 10 bytes for symbol, 8 for price
        approx_total_bytes = approx_entry_bytes * self.num_symbols

        print(
            f"[SharedPriceBook-Perf] symbols={self.num_symbols} "
            f"approx_footprint={approx_total_bytes} bytes "
            f"(dtype_size={self.total_size_bytes} bytes)"
        )


        self.name = name
        self.shm = None
        self.price_array = None # This will be our NumPy "view"

        if create:
            # We are the OrderBook (creator)
            try:
                # Create the shared memory block
                self.shm = SharedMemory(name=self.name, create=True, size=self.total_size_bytes)
                print(f"Created shared memory block '{self.name}' ({self.total_size_bytes} bytes)")
            except FileExistsError:
                # This handles a messy shutdown from a previous run
                print(f"Shared memory block '{self.name}' already exists. Attaching...")
                self.shm = SharedMemory(name=self.name, create=False)
                # Don't re-initialize, just attach
        else:
            # We are the Strategy (attacher)
            try:
                self.shm = SharedMemory(name=self.name, create=False)
                print(f"Attached to shared memory block '{self.name}'")
            except FileNotFoundError:
                print(f"ERROR: Shared memory block '{self.name}' not found.")
                print("Is the OrderBook process running?")
                raise

        # Now, create the NumPy array "view" on top of the shared memory buffer
        self.price_array = np.ndarray(
            shape=(self.num_symbols,),
            dtype=self.dtype,
            buffer=self.shm.buf
        )
        # A lock to prevent race conditions (e.g., writing while reading)
        # This lock is shared by all processes that use this class
        self.lock = mp.Lock()

        if create:
            # If we just created it, we need to fill in the symbol names
            self._init_array_data()

        

    def _init_array_data(self):
        """
        [Internal] Fills the array with initial symbol data.
        Only called by the creator process.
        """
        print("Initializing shared memory array with symbols...")
        with self.lock:
            for i, symbol in enumerate(self.symbols):
                self.price_array[i]['symbol'] = symbol.encode('utf-8')
                self.price_array[i]['price'] = 0.0 # Start prices at 0
        print("Initialization complete.")

    def update(self, symbol, price):
        """
        Update the price for a given symbol.
        This is the "write" operation, used by the OrderBook.
        """
        if symbol not in self.symbol_to_index:
            print(f"Warning: Symbol '{symbol}' not tracked in shared memory.")
            return

        idx = self.symbol_to_index[symbol]
        
        # Hang the "Do Not Disturb" sign
        with self.lock:
            # Update the price in the array
            self.price_array[idx]['price'] = price
        # "Do Not Disturb" sign is automatically removed

    def read(self, symbol):
        """
        Read the price for a given symbol.
        This is the "read" operation, used by the Strategy.
        """
        if symbol not in self.symbol_to_index:
            print(f"Warning: Symbol '{symbol}' not tracked.")
            return None

        idx = self.symbol_to_index[symbol]

        # Wait if the "Do Not Disturb" sign is up
        with self.lock:
            # Read the price from the array
            price = self.price_array[idx]['price']
        # Sign is removed
        
        return price
    
    def get_all_prices(self):
        """
        Returns a copy of all data as a dictionary.
        Safer for reading multiple values.
        """
        with self.lock:
            # Create a deep copy to avoid issues outside the lock
            data_copy = np.copy(self.price_array)
        
        return {
            row['symbol'].decode('utf-8'): row['price'] for row in data_copy
        }

    def close(self):
        """
        Close the shared memory object.
        This "detaches" the process from the memory block.
        """
        if self.shm:
            self.shm.close()
            print(f"Detached from shared memory block '{self.name}'.")

    def unlink(self):
        """
        Request that the shared memory block be destroyed.
        Only the *creator* (OrderBook) should call this on exit.
        """
        if self.shm:
            try:
                self.shm.unlink() # Destroy the block
                print(f"Shared memory block '{self.name}' destroyed.")
            except FileNotFoundError:
                pass # Already destroyed, which is fine