# CSNETWORK_MachineProject

# CSNETWORK Machine Project: P2P Pokémon Battle Protocol (PokeProtocol)

**Course:** CSNETWK

**Term:** 1T2526

## Project Overview

This project is an implementation of the **P2P Pokémon Battle Protocol (PokeProtocol)** over UDP. It features a fully functional turn-based battle system where two peers connect directly to battle using Pokémon data loaded from a CSV. The application includes a custom reliability layer to handle UDP packet loss, sequence ordering, and state synchronization.

We have implemented both a **Command Line Interface (CLI)** and a **Web-based Graphical User Interface (GUI)** using Flask and Socket.IO.

## Group Members

* **Kryster Knowell Limpin**

* **Justin Ice David**

## Work Distribution Matrix

We have divided the implementation tasks equally to ensure a balanced contribution to the codebase.

| **Component / Feature** | **Assigned Member** | **Description** | 
| :--- | :--- | :--- |
| **Game Logic (GameEngine)** | Kryster Knowell Limpin | Implemented the core state machine (`game_engine.py`), turn-based flow, and move selection logic. | 
| **Pokémon Data & Stats** | Kryster Knowell Limpin | Developed `pokemon_manager.py` to parse `pokemon.csv` and handle Pokémon data structures. | 
| **Damage Calculation** | Kryster Knowell Limpin | Implemented the RFC-compliant damage formula, including type effectiveness and stat boost logic. | 
| **CLI Implementation** | Kryster Knowell Limpin | Built the terminal-based interface (`main.py`) and the initial handshake/setup process. | 
| **Network Manager** | Justin Ice David | Developed `network_manager.py`, handling UDP socket binding, broadcasting, and packet construction. | 
| **Reliability Layer** | Justin Ice David | Implemented the Stop-and-Wait protocol, Sequence Numbers, ACKs, and Retransmission logic to ensure data integrity over UDP. | 
| **Web GUI Implementation** | Justin Ice David | Created `web_main.py` using Flask/SocketIO to provide a graphical battle interface (Bonus Feature). | 
| **Chat & Stickers** | Justin Ice David | Implemented the asynchronous chat system, including Base64 encoding/decoding for sticker transmission. | 

## Features Implemented

* **Core Protocol:** Full implementation of the PokeProtocol over UDP.

* **Reliability Layer:** Custom handling of Sequence Numbers and ACKs to prevent packet loss.

* **4-Step Turn Handshake:** `ATTACK_ANNOUNCE` -> `DEFENSE_ANNOUNCE` -> `CALCULATION_REPORT` -> `CALCULATION_CONFIRM`.

* **Modes:**

  * **P2P:** Direct IP connection.

  * **Broadcast:** Local network discovery.

  * **Spectator:** Allows a third peer to watch the battle passively.

* **Game Mechanics:**

  * Accurate Damage Calculation with Stat Boosts.

  * Win/Loss detection (`GAME_OVER`).

* **Web GUI:** A responsive browser-based interface for easier gameplay and visualization.

* **Chat:** Real-time text chat and image sticker support.

## How to Run

### Prerequisites

* Python 3.x

* Required libraries: `flask`, `flask_socketio` (for Web GUI)

```bash
pip install flask flask_socketio
