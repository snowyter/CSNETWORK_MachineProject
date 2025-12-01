import threading
import time
import sys
import socket

# Import your modules
import constants
from network_manager import NetworkManager
from pokemon_manager import PokemonManager
from game_engine import GameEngine

class PokemonGameClient:
    def __init__(self):
        print("=== POKEMON P2P BATTLE ===")
        
        # 1. Ask for Port (Crucial for running 2 instances on 1 computer)
        port_input = input(f"Enter your port (default {constants.DEFAULT_PORT}): ")
        self.my_port = int(port_input) if port_input else constants.DEFAULT_PORT
        
        # 2. Initialize Managers
        self.net = NetworkManager(port=self.my_port)
        self.poke = PokemonManager("pokemon.csv")
        self.engine = GameEngine(self.poke, self.net)
        
        # 3. State Flags
        self.running = True
        self.is_host = False
        self.input_thread = None

    def get_local_ip(self):
        """Helper to print your IP so your friend can join."""
        try:
            # We connect to a public DNS just to see what our network interface IP is
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def setup_connection(self):
        """Phase 1: Connect two computers via Handshake."""
        print(f"\nYour IP: {self.get_local_ip()} | Listening on Port: {self.my_port}")
        print("1. Host a Game")
        print("2. Join a Game")
        
        choice = input("Select option: ")
        
        if choice == '1':
            self.is_host = True
            print(f"\n[HOST] Waiting for challenger...")
            # Host sits and waits for the network loop to catch the Handshake
            
        elif choice == '2':
            self.is_host = False
            # 1. Get Target IP
            target_ip = input("Enter Host IP (use 127.0.0.1 for local): ")
            if not target_ip: target_ip = "127.0.0.1"

            # 2. Get Target Port (Important if testing locally)
            target_port_input = input(f"Enter Host Port (default {constants.DEFAULT_PORT}): ")
            target_port = int(target_port_input) if target_port_input else constants.DEFAULT_PORT
            
            # 3. Setup peer immediately
            self.net.set_peer(target_ip)
            # Override the default port in NetworkManager if user typed a specific one
            self.net.peer_address = (target_ip, target_port)
            
            # 4. Send Handshake
            print(f"\n[JOIN] Sending handshake to {target_ip}:{target_port}...")
            self.net.send_reliable(constants.MSG_HANDSHAKE_REQUEST, {
                "greeting": "Hello from Challenger"
            })
            
    def setup_game_data(self):
        """Phase 2: Pick Pokemon and exchange stats."""
        # Loop until valid pokemon selected
        while True:
            p_name = input("\nChoose your Pokemon (e.g. Bulbasaur): ").strip()
            data = self.poke.get_pokemon(p_name)
            if data:
                self.engine.set_my_pokemon(p_name)
                break
            else:
                print("Invalid Pokemon name! Check pokemon.csv for exact spelling.")

        # Send BATTLE_SETUP to opponent
        print("[SETUP] Sending Pokemon data to opponent...")
        setup_data = {
            constants.KEY_POKEMON_NAME: p_name,
            "hp": data['hp'],
            "attack": data['attack'],
            "defense": data['defense'],
            "speed": data['speed']
        }
        self.net.send_reliable(constants.MSG_BATTLE_SETUP, setup_data)
        
        print("Waiting for opponent to pick their Pokemon...")
        # We wait until the engine receives a BATTLE_SETUP message
        while self.engine.opponent_pokemon is None:
            self.network_loop_step()
            time.sleep(0.1)
            
        # Once we have opponent data, start the game logic
        self.engine.start_battle(self.is_host)

    def input_loop(self):
        """
        Phase 3: The Input Thread.
        Runs in background to capture typing without freezing the network.
        """
        print("\n--- COMMANDS ---")
        print("/attack [MoveName] -> Use a move (e.g. /attack Thunderbolt)")
        
        print("Available Moves:")
        for move, info in self.poke.moves.items():
            print(f"  - {move} ({info['type']})")

        print("/chat [Message]    -> Send text chat")
        print("/quit              -> Exit game")
        print("----------------")
        
        while self.running:
            try:
                # This line blocks, but only this thread blocks. Network keeps running.
                cmd = input() 
                
                if cmd.startswith("/quit"):
                    self.running = False
                    print("Quitting...")
                    break
                    
                elif cmd.startswith("/attack "):
                    move_name = cmd.split(" ", 1)[1]
                    self.engine.select_move(move_name)
                    
                elif cmd.startswith("/chat "):
                    msg_text = cmd.split(" ", 1)[1]
                    self.net.send_reliable(constants.MSG_CHAT_MESSAGE, {
                        constants.KEY_MSG_TEXT: msg_text
                    })
                    print(f"[YOU]: {msg_text}")
                
                else:
                    print("Unknown command. Use /attack or /chat")
            
            except EOFError:
                break
            except Exception as e:
                print(f"Input Error: {e}")

    def network_loop_step(self):
        """
        Runs one iteration of network processing.
        """
        # 1. Receive incoming
        msg = self.net.receive_message()
        if msg:
            msg_type = msg.get(constants.KEY_MSG_TYPE)
            
            # --- HANDSHAKE HANDLING (Connection Phase) ---
            if msg_type == constants.MSG_HANDSHAKE_REQUEST:
                print(f"[NET] Received Handshake Request from {self.net.peer_address}")
                # If we are Host, we must lock onto this peer now
                if self.is_host:
                    # peer_address is auto-set inside receive_message for the first packet
                    self.net.send_reliable(constants.MSG_HANDSHAKE_RESPONSE, {"status": "OK"})
                    print("Connected! Please pick your Pokemon.")

            elif msg_type == constants.MSG_HANDSHAKE_RESPONSE:
                print("[NET] Handshake Accepted! Connected.")

            # --- CHAT HANDLING ---
            elif msg_type == constants.MSG_CHAT_MESSAGE:
                text = msg.get(constants.KEY_MSG_TEXT)
                print(f"\n[OPPONENT]: {text}")

            # --- GAME ENGINE HANDLING ---
            else:
                self.engine.process_message(msg)

        # 2. Resend any lost packets
        self.net.check_resend()

    def run(self):
        # Step 1: Connect
        self.setup_connection()
        
        # Wait for handshake to complete (simple check: do we have a peer?)
        while self.net.peer_address is None:
            self.network_loop_step()
            time.sleep(0.1)
            
        # Step 2: Pick Pokemon
        self.setup_game_data()
        
        # Step 3: Start Input Thread
        self.input_thread = threading.Thread(target=self.input_loop)
        self.input_thread.daemon = True # Kills thread if main program exits
        self.input_thread.start()
        
        # Step 4: Main Network Loop
        print("Game Loop Started. Waiting for input...")
        while self.running:
            self.network_loop_step()
            
            # CPU rest to prevent 100% usage
            time.sleep(0.01) 

if __name__ == "__main__":
    client = PokemonGameClient()
    client.run()
