# Multi-Process Trading System
### Authors: Sverrir Hakonarson, Robert Asgeirsson
#### Had assistance from chatGPT in the making of the project

This project simulates a high-frequency trading (HFT) system using four independent Python processes. It demonstrates real-world interprocess communication (IPC) techniques, including:

* **TCP Sockets:** For sending and receiving event-driven messages (like news and orders).
* **Shared Memory:** For high-speed, low-latency state sharing (like the current price book).

This project emphasizes process separation, synchronization, and robust communication, which are core principles of financial systems architecture.

## Watch the video to see the system in action

[![Watch the video](https://img.youtube.com/vi/Eb1ZTa4o6m4/maxresdefault.jpg)](https://www.youtube.com/watch?v=Eb1ZTa4o6m4)


## Architecture

The system is composed of four specialists who work in separate, locked rooms. They communicate only through **Telephones (Sockets)** for messages or a public **Whiteboard (Shared Memory)** for live data.

**Diagram:**
`[ Gateway ] -> [ OrderBook ] -> [ Strategy ] -> [ OrderManager ]`

### Components

1.  **`gateway.py` (The "News Room")**
    * Acts as a **Server** on two ports.
    * **Price Port (9000):** Shouts a new stock price every second to anyone listening.
    * **News Port (9001):** Shouts a new "market mood" (sentiment score) every 3 seconds.

2.  **`order_manager.py` (The "Broker")**
    * Acts as a **Server** on one port.
    * **Order Port (9002):** Listens patiently for trade orders. When it receives one, it logs it and prints a confirmation.

3.  **`orderbook.py` (The "Intern")**
    * Acts as a **Client** to the `Gateway` and the **Writer** to the `Whiteboard`.
    * **Calls** the `Gateway` (Port 9000) to get prices.
    * **Writes** those prices instantly to the `Whiteboard (Shared Memory)`.
    * Its only job is to ensure the Whiteboard *always* has the latest price.

4.  **`strategy.py` (The "Star Trader")**
    * The "brain" of the operation. Acts as a **Client** to everyone.
    * **Reads** prices instantly from the `Whiteboard (Shared Memory)`.
    * **Calls** the `Gateway` (Port 9001) to get the "market mood."
    * **Calls** the `OrderManager` (Port 9002) to send a trade *only when* the price signal and news signal agree.

### Communication

* **Sockets (Telephones):** Used for event-driven, one-way messages (Gateway -> OrderBook, Gateway -> Strategy, Strategy -> OrderManager).
* **Shared Memory (Whiteboard):** A `numpy` structured array used for *state*. The `Strategy` can read the latest price with near-zero latency, without ever having to ask for it. A `Lock` ensures data is not corrupted during writes.

## How to Run

This system is designed to be run in four separate terminal windows to demonstrate true process independence.

**Prerequisites:**
* Python 3.x
* `numpy` (`pip install numpy`)

### 1. Open 4 Terminal Windows

Arrange your terminals so you can see all four at once.

### 2. Run the Processes (in order)

**In Terminal 1: Start the Order Manager (Broker)**
```bash
python order_manager.py
