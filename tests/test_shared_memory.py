"""
Unit test for shared_memory_utils.py

This test confirms that two separate processes can
successfully write and read from the SharedPriceBook.
"""

import unittest
import multiprocessing as mp
import time

# --- This is the new part to make the Play Button work ---
import sys
import os

# Get the path of the current file (e.g., .../Assignment_8/tests/test_shared_memory.py)
current_file_path = os.path.abspath(__file__)

# Get the directory of the current file (e.g., .../Assignment_8/tests)
tests_dir = os.path.dirname(current_file_path)

# Get the parent directory (the 'Assignment_8' project root)
project_root = os.path.dirname(tests_dir)

# Add the project root to Python's "search path"
sys.path.insert(0, project_root)
# --- End of new part ---

from shared_memory_utils import SharedPriceBook
from config import SHARED_MEMORY_NAME, SYMBOLS

# === Target function for the child process (Reader) ===

def reader_process_task(shm_name, symbol, result_queue):
    """
    This function runs in a separate process.
    It attaches to the shared memory, reads a value,
    and puts the result in a queue.
    """
    try:
        # Attach to the *existing* shared memory
        book = SharedPriceBook(name=shm_name, create=False)
        
        # Give the writer a moment just in case
        time.sleep(0.1) 
        
        # Read the value
        price = book.read(symbol)
        
        # Put the read value into the queue to send it back
        result_queue.put(price)
        
        book.close()
    except Exception as e:
        print(f"[Reader Process] Error: {e}")
        result_queue.put(e)

# === Main Test Case ===

class TestSharedPriceBook(unittest.TestCase):

    def setUp(self):
        """
        Set up the test. This runs *before* each test function.
        We act as the "Creator" process.
        """
        print("\n[Main Process] Creating SharedPriceBook...")
        # Create the shared memory block
        self.book = SharedPriceBook(name=SHARED_MEMORY_NAME, create=True)
        self.shm_name = self.book.name
        self.result_queue = mp.Queue()

    def tearDown(self):
        """
        Tear down the test. This runs *after* each test function.
        We clean up the shared memory.
        """
        print("[Main Process] Cleaning up SharedPriceBook...")
        self.book.close()
        self.book.unlink() # Destroy the block
        self.result_queue.close()

    def test_write_and_read_across_processes(self):
        """
        Tests the core functionality:
        1. Main process writes a value.
        2. Child process reads the value.
        3. Main process verifies the value.
        """
        print("[Main Process] Test: test_write_and_read_across_processes")
        test_symbol = 'AAPL'
        test_price = 150.75
        
        # 1. Main process writes a value
        print(f"[Main Process] Writing {test_symbol} = {test_price}")
        self.book.update(test_symbol, test_price)
        
        # 2. Start the child process to read the value
        reader_process = mp.Process(
            target=reader_process_task,
            args=(self.shm_name, test_symbol, self.result_queue)
        )
        
        reader_process.start()
        
        # 3. Main process gets the result from the queue
        try:
            # Wait for the result for up to 5 seconds
            read_price = self.result_queue.get(timeout=5)
            print(f"[Main Process] Got price from reader: {read_price}")
        except mp.queues.Empty:
            self.fail("Test timed out: Reader process did not return a value.")
            
        reader_process.join(timeout=1)
        if reader_process.is_alive():
            print("[Main Process] Forcibly terminating reader process.")
            reader_process.terminate()

        # 4. Verify the value
        self.assertEqual(read_price, test_price)

    def test_update_and_read_latest(self):
        """
        Tests that the reader process gets the *latest* updated value.
        """
        print("[Main Process] Test: test_update_and_read_latest")
        test_symbol = 'MSFT'
        
        # Write an initial value
        self.book.update(test_symbol, 300.0)
        time.sleep(0.01)
        
        # Write the *final* value
        final_price = 301.50
        print(f"[Main Process] Writing {test_symbol} = {final_price}")
        self.book.update(test_symbol, final_price)
        
        # Start the child process
        reader_process = mp.Process(
            target=reader_process_task,
            args=(self.shm_name, test_symbol, self.result_queue)
        )
        
        reader_process.start()
        
        # Get the result
        try:
            read_price = self.result_queue.get(timeout=5)
            print(f"[Main Process] Got price from reader: {read_price}")
        except mp.queues.Empty:
            self.fail("Test timed out: Reader process did not return a value.")
            
        reader_process.join(timeout=1)
        if reader_process.is_alive():
            print("[Main Process] Forcibly terminating reader process.")
            reader_process.terminate()

        # Verify it's the latest price
        self.assertEqual(read_price, final_price)

if __name__ == '__main__':
    # We must use 'spawn' or 'forkserver' for multiprocessing on Windows/macOS
    mp.set_start_method('spawn')
    unittest.main()