import threading
import time
import sys
import socket
import random
import base64

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
        self.is_spectator = False
        self.input_thread = None
        self.player_name = "Player"

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
        self.player_name = input("Enter your name: ") or "Player"
        
        print("1. Host a Game")
        print("2. Join a Game")
        print("3. Spectate a Game")
        print("4. Scan for Games (Broadcast)")
        
        choice = input("Select option: ")
        
        if choice == '1':
            self.is_host = True
            print(f"\n[HOST] Waiting for challenger...")
            # Announce via Broadcast
            self.net.send_broadcast(constants.MSG_BATTLE_SETUP, {
                "communication_mode": "BROADCAST",
                "status": "OPEN",
                "host_name": self.player_name
            })
            
        elif choice == '2':
            self.is_host = False
            self.join_game(is_spectator=False)
            
        elif choice == '3':
            self.is_host = False
            self.is_spectator = True
            self.join_game(is_spectator=True)

        elif choice == '4':
            print("Scanning for games...")
            # Listen for broadcast announcements
            start_time = time.time()
            found_games = []
            while time.time() - start_time < 5: # Scan for 5 seconds
                msg = self.net.receive_message()
                if msg and msg.get(constants.KEY_MSG_TYPE) == constants.MSG_BATTLE_SETUP:
                     if msg.get("communication_mode") == "BROADCAST":
                         addr = msg.get('source_addr')
                         if addr not in [g['addr'] for g in found_games]:
                             found_games.append({'addr': addr, 'host': msg.get('host_name')})
                             print(f"Found game hosted by {msg.get('host_name')} at {addr}")
                time.sleep(0.1)
            
            if not found_games:
                print("No games found. Try joining manually.")
                self.join_game(is_spectator=False)
            else:
                print("\nSelect a game to join:")
                for i, g in enumerate(found_games):
                    print(f"{i+1}. {g['host']} ({g['addr']})")
                
                try:
                    idx = int(input("Enter number: ")) - 1
                    target_ip = found_games[idx]['addr'][0]
                    target_port = found_games[idx]['addr'][1]
                    
                    self.net.set_peer(target_ip)
                    self.net.peer_address = (target_ip, target_port)
                    
                    print(f"Joining {target_ip}:{target_port}...")
                    self.net.send_reliable(constants.MSG_HANDSHAKE_REQUEST, {
                        constants.KEY_SENDER: self.player_name
                    })
                except:
                    print("Invalid selection.")

    def join_game(self, is_spectator):
        # 1. Get Target IP
        target_ip = input("Enter Host IP (use 127.0.0.1 for local): ")
        if not target_ip: target_ip = "127.0.0.1"

        # 2. Get Target Port (Important if testing locally)
        target_port_input = input(f"Enter Host Port (default {constants.DEFAULT_PORT}): ")
        target_port = int(target_port_input) if target_port_input else constants.DEFAULT_PORT
        
        # 3. Setup peer immediately
        self.net.set_peer(target_ip)
        self.net.peer_address = (target_ip, target_port)
        
        # 4. Send Handshake
        msg_type = constants.MSG_SPECTATOR_REQUEST if is_spectator else constants.MSG_HANDSHAKE_REQUEST
        print(f"\n[JOIN] Sending {msg_type} to {target_ip}:{target_port}...")
        
        self.net.send_reliable(msg_type, {
            constants.KEY_SENDER: self.player_name
        })
            
    def setup_game_data(self):
        """Phase 2: Pick Pokemon and exchange stats."""
        import json # Import here to avoid messing with top of file for now
        
        if self.is_spectator:
            print("[SPECTATOR] Waiting for battle to start...")
            # Spectator just waits for messages
            while self.running:
                self.network_loop_step()
                time.sleep(0.1)
            return

        # 1. Communication Mode Selection (RFC 4.4) - Moved to top for UX
        print("\nSelect Communication Mode:")
        print("1. P2P (Direct)")
        print("2. BROADCAST (Local Network)")
        comm_mode = constants.MODE_P2P # Default
        while True:
            mode_choice = input("Enter choice (1/2): ").strip()
            if mode_choice == "1":
                comm_mode = constants.MODE_P2P
                break
            elif mode_choice == "2":
                comm_mode = constants.MODE_BROADCAST
                break
            else:
                print("Invalid choice.")

        # 2. Pick Pokemon
        while True:
            p_name = input("\nChoose your Pokemon (e.g. Bulbasaur): ").strip()
            data = self.poke.get_pokemon(p_name)
            if data:
                break
            else:
                print("Invalid Pokemon name! Check pokemon.csv for exact spelling.")
        
        # 3. Stat Boost Allocation
        print("\nAllocate 10 Stat Boosts (Sp. Atk and Sp. Def).")
        while True:
            try:
                sp_atk = int(input("Sp. Atk Boosts (0-10): "))
                sp_def = int(input("Sp. Def Boosts (0-10): "))
                if sp_atk + sp_def <= 10:
                    break
                print("Total must be <= 10!")
            except ValueError:
                print("Invalid number.")

        self.engine.set_my_pokemon(p_name, sp_atk, sp_def)

        # Send BATTLE_SETUP to opponent
        print("[SETUP] Sending Pokemon data to opponent...")
        
        # RFC 4.4 Compliance
        boosts_data = {
            "special_attack_uses": sp_atk,
            "special_defense_uses": sp_def
        }
        
        setup_data = {
            constants.KEY_POKEMON_NAME: p_name,
            constants.KEY_STAT_BOOSTS: json.dumps(boosts_data),
            constants.KEY_POKEMON_DATA: json.dumps(data),
            constants.KEY_COMM_MODE: comm_mode 
        }
        self.net.send_reliable(constants.MSG_BATTLE_SETUP, setup_data)
        
        print("Waiting for opponent to pick their Pokemon...")
        # We wait until the engine receives a BATTLE_SETUP message
        while self.engine.opponent_pokemon is None:
            self.network_loop_step()
            time.sleep(0.1)
            
        # Once we have opponent data, start the game logic
        # Note: start_battle is called after Handshake Response (for seed) AND Setup
        # But we need to make sure we have the seed.
        if self.engine.seed is not None:
             self.engine.start_battle(self.is_host, self.engine.seed)
        else:
            # Wait for seed if we are joiner? Host generates it.
            # Host sets seed in handshake response handling.
            pass

    def input_loop(self):
        """
        Phase 3: The Input Thread.
        Runs in background to capture typing without freezing the network.
        """
        print("\n--- COMMANDS ---")
        if not self.is_spectator:
            print("/attack [MoveName] -> Use a move")
            print("/attack [MoveName] boost -> Use a move with boost")
        print("/chat [Message]    -> Send text chat")
        print("/sticker [Base64]  -> Send sticker")
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
                    
                elif cmd.startswith("/attack ") and not self.is_spectator:
                    parts = cmd.split(" ")
                    move_name = parts[1]
                    use_boost = "boost" in parts
                    self.engine.select_move(move_name, use_boost)
                    
                elif cmd.startswith("/chat "):
                    msg_text = cmd.split(" ", 1)[1]
                    self.net.send_reliable(constants.MSG_CHAT_MESSAGE, {
                        constants.KEY_SENDER: self.player_name,
                        constants.KEY_CONTENT_TYPE: constants.CONTENT_TYPE_TEXT,
                        constants.KEY_MSG_TEXT: msg_text
                    })
                    print(f"[YOU]: {msg_text}")
                    
                elif cmd.startswith("/sticker "):
                    sticker_data = cmd.split(" ", 1)[1]
                    self.net.send_reliable(constants.MSG_CHAT_MESSAGE, {
                        constants.KEY_SENDER: self.player_name,
                        constants.KEY_CONTENT_TYPE: constants.CONTENT_TYPE_STICKER,
                        constants.KEY_STICKER_DATA: sticker_data
                    })
                    print(f"[YOU]: Sent a sticker.")
                
                else:
                    if self.is_spectator and cmd.startswith("/attack"):
                        print("Spectators cannot attack!")
                    else:
                        print("Unknown command.")
            
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
                print(f"[NET] Received Handshake Request from {msg.get('source_addr')}")
                if self.is_host:
                    # Set peer
                    self.net.peer_address = msg.get('source_addr')
                    # Generate Seed
                    seed = random.randint(1000, 9999)
                    self.engine.seed = seed
                    # Send Response
                    self.net.send_reliable(constants.MSG_HANDSHAKE_RESPONSE, {
                        constants.KEY_SEED: seed,
                        "status": "OK"
                    })
                    print(f"Connected! Seed: {seed}. Please pick your Pokemon.")
                    # Host waits for Setup Phase now.
                    # self.engine.start_battle(True, seed) -> REMOVED

            elif msg_type == constants.MSG_SPECTATOR_REQUEST:
                print(f"[NET] Spectator joined from {msg.get('source_addr')}")
                self.net.add_spectator(msg.get('source_addr'))
                # Send ACK manually or rely on reliability layer if we want
                # But we should probably send current state or at least a welcome
                self.net.send_reliable(constants.MSG_CHAT_MESSAGE, {
                    constants.KEY_SENDER: "HOST",
                    constants.KEY_CONTENT_TYPE: constants.CONTENT_TYPE_TEXT,
                    constants.KEY_MSG_TEXT: "Welcome Spectator!"
                })

            elif msg_type == constants.MSG_HANDSHAKE_RESPONSE:
                seed = msg.get(constants.KEY_SEED)
                print(f"[NET] Handshake Accepted! Seed: {seed}")
                self.engine.seed = int(seed)
                # Joiner waits for Setup Phase now.
                # self.engine.start_battle(False, seed) -> REMOVED

            # --- CHAT HANDLING ---
            elif msg_type == constants.MSG_CHAT_MESSAGE:
                sender = msg.get(constants.KEY_SENDER, "Unknown")
                content_type = msg.get(constants.KEY_CONTENT_TYPE)
                
                if content_type == constants.CONTENT_TYPE_STICKER:
                    print(f"\n[{sender}]: [STICKER RECEIVED]")
                else:
                    text = msg.get(constants.KEY_MSG_TEXT)
                    print(f"\n[{sender}]: {text}")

                # HOST RELAY LOGIC
                if self.is_host:
                    source_addr = msg.get('source_addr')
                    
                    # Prepare data for relay (remove internal/header keys)
                    relay_data = {k: v for k, v in msg.items() if k not in [
                        constants.KEY_MSG_TYPE, constants.KEY_SEQ_NUM, 'source_addr'
                    ]}
                    
                    # 1. If from Opponent -> Relay to ALL Spectators
                    if source_addr == self.net.peer_address:
                        for spec in self.net.spectators:
                            try:
                                packet = self.net.construct_message(constants.MSG_CHAT_MESSAGE, relay_data)
                                self.net.sock.sendto(packet, spec)
                            except: pass
                            
                    # 2. If from Spectator -> Relay to Opponent + Other Spectators
                    elif source_addr in self.net.spectators:
                        # To Opponent
                        if self.net.peer_address:
                            try:
                                packet = self.net.construct_message(constants.MSG_CHAT_MESSAGE, relay_data)
                                self.net.sock.sendto(packet, self.net.peer_address)
                            except: pass
                        
                        # To Other Spectators
                        for spec in self.net.spectators:
                            if spec != source_addr:
                                try:
                                    packet = self.net.construct_message(constants.MSG_CHAT_MESSAGE, relay_data)
                                    self.net.sock.sendto(packet, spec)
                                except: pass

            # --- GAME ENGINE HANDLING ---
            else:
                self.engine.process_message(msg)

        # 2. Resend any lost packets
        self.net.check_resend()

    def run(self):
        # Step 1: Connect
        self.setup_connection()
        
        # Wait for connection (Handshake Complete)
        print("Waiting for connection...")
        while self.engine.seed is None:
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
