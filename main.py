# main.py

from multiprocessing import Process

from gateway import run_gateway
from orderbook import run_orderbook
from strategy import run_strategy
from order_manager import run_ordermanager


def main():
    processes = [
        Process(target=run_gateway),
        Process(target=run_orderbook),
        Process(target=run_strategy),
        Process(target=run_ordermanager),
    ]

    for p in processes:
        p.start()

    try:
        # Wait for all processes
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n[Main] Caught KeyboardInterrupt, terminating child processes...")
        for p in processes:
            p.terminate()


if __name__ == "__main__":
    main()
