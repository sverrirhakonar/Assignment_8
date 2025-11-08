# Performance Report

| Metric                     | Description                                                              | Result           | Notes                                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Latency**          | Avg time between Gateway price tick (`t1`) and Strategy order (`t2`) | ~0.63 sec       | Based on `(t2 - t1)` from terminal (calculated by hand)                                                                |
| **Throughput**       | Average ticks per second from Gateway                                    | ~1.00 ticks/sec | Derived from `[Gateway-Perf] throughput_est` logs                                                                      |
| **Memory Footprint** | Shared memory size for price book                                        | 72 bytes         | 4 symbols × (10B str + 8B float)                                                                                        |
| **Reliability**      | Behavior on shutdown and disconnects                                     | Stable           | Clean shutdown on Ctrl+C; Gateway, OrderBook, Strategy close sockets and shared memory without errorsTest configuration: |

- Gateway sleep: 1.0s
- Symbols: AAPL, MSFT, GOOGL, AMZN
- Strategy: MA crossover + sentiment
- Quantity: 10

**Observation:**
Latency mainly depends on the delay between price and news broadcasts. Reducing `time.sleep()` in `gateway.py` improves throughput but increases CPU load.
