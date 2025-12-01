import constants
import random
from pokemon_manager import PokemonManager

class GameEngine:
    def __init__(self, pokemon_manager, network_manager):
        # 1. Connect to the Data Source.
        self.pokemon_manager = pokemon_manager
        self.network_manager = network_manager
        
        # 2. Initialize State
        self.state = constants.STATE_SETUP
        self.is_host = False
        self.seed = None
        self.rng = random.Random()
        
        # 3. Player Data
        self.my_pokemon = None
        self.opponent_pokemon = None
        self.my_stat_boosts = {"sp_atk": 0, "sp_def": 0} # Available uses
        self.opp_stat_boosts = {"sp_atk": 0, "sp_def": 0}
        
        # 4. Turn Management
        self.is_my_turn = False 
        self.turn_data = {} # Stores move, boosts for current turn
        self.pending_confirmation = False # Waiting for CALCULATION_CONFIRM

    def set_my_pokemon(self, name, sp_atk_boosts=0, sp_def_boosts=0):
        """Called when YOU pick a pokemon from the UI/Console."""
        data = self.pokemon_manager.get_pokemon(name)
        if data:
            self.my_pokemon = data.copy()
            self.my_pokemon[constants.KEY_MAX_HP] = self.my_pokemon[constants.KEY_HP]
            self.my_stat_boosts = {"sp_atk": sp_atk_boosts, "sp_def": sp_def_boosts}
            print(f"You selected {name}!")
            return True
        else:
            print(f"Error: Pokemon '{name}' not found.")
            return False

    def set_opponent_pokemon(self, name, stats=None, boosts=None):
        """Called when we receive a BATTLE_SETUP message from the enemy."""
        data = self.pokemon_manager.get_pokemon(name)
        if data:
            self.opponent_pokemon = data.copy()
            self.opponent_pokemon[constants.KEY_MAX_HP] = self.opponent_pokemon[constants.KEY_HP]
            # Optionally update stats if provided (e.g. if they have custom stats)
            if stats:
                for k, v in stats.items():
                    if k in self.opponent_pokemon:
                        self.opponent_pokemon[k] = int(v)
            
            if boosts:
                # Parse boosts string "atk,def"
                try:
                    parts = boosts.split(',')
                    self.opp_stat_boosts = {
                        "sp_atk": int(parts[0]),
                        "sp_def": int(parts[1])
                    }
                except:
                    print("Error parsing opponent boosts")

            print(f"Opponent selected {name}!")
            return True
        return False
    
    def start_battle(self, is_host, seed=None):
        """
        Initializes battle state.
        """
        self.is_host = is_host
        if seed is not None:
            self.seed = int(seed)
            # IMPORTANT: Set GLOBAL random seed because pokemon_manager uses random module directly
            random.seed(self.seed)
            print(f"Battle Seed: {self.seed}")
        
        # RFC: Host goes first
        self.is_my_turn = is_host
            
        print(f"Battle Started! My Turn: {self.is_my_turn}")
        if self.is_my_turn:
            print("Use /attack [MoveName] to attack!")
        else:
            print("Waiting for opponent...")
        self.state = constants.STATE_WAITING_FOR_MOVE

    def select_move(self, move_name, use_boost=False):
        """
        Called when user types /attack [MoveName]
        """
        if self.state != constants.STATE_WAITING_FOR_MOVE:
            print("Cannot move right now.")
            return

        if not self.is_my_turn:
            print("It is not your turn!")
            return

        # Validate move
        move = self.pokemon_manager.get_move(move_name)
        if not move:
            print(f"Unknown move: {move_name}")
            print(f"Available moves: {list(self.pokemon_manager.moves.keys())}")
            return

        self.turn_data = {
            "move_name": move_name,
            "attacker": self.my_pokemon['name'],
            "defender": self.opponent_pokemon['name'],
            "use_boost": use_boost
        }
        
        print(f"You chose {move_name}. Waiting for opponent to acknowledge...")
        
        # Send Announce (Step 1)
        payload = {
            constants.KEY_MOVE_NAME: move_name
        }
        
        self.network_manager.send_reliable(constants.MSG_ATTACK_ANNOUNCE, payload)

    def process_message(self, message):
        """
        The Main Brain. Decides what to do with a network message.
        """
        msg_type = message.get(constants.KEY_MSG_TYPE)
        
        print(f"[Engine] Processing {msg_type}...")

        # 1. SETUP PHASE
        if msg_type == constants.MSG_BATTLE_SETUP:
            opp_name = message.get(constants.KEY_POKEMON_NAME)
            boosts_str = message.get(constants.KEY_STAT_BOOSTS)
            self.set_opponent_pokemon(opp_name, boosts=boosts_str)
            
            if self.my_pokemon and self.opponent_pokemon:
                print("Battle Setup Complete.")

        # 2. TURN HANDSHAKE
        # Step 1: Receive Attack Announce (Defender side)
        elif msg_type == constants.MSG_ATTACK_ANNOUNCE:
            move_name = message.get(constants.KEY_MOVE_NAME)
            print(f"Opponent announced attack: {move_name}")
            
            # Store turn data
            self.turn_data = {
                "move_name": move_name,
                "attacker": self.opponent_pokemon['name'],
                "defender": self.my_pokemon['name']
            }
            
            # Step 2: Send Defense Announce
            self.network_manager.send_reliable(constants.MSG_DEFENSE_ANNOUNCE, {})
            
            # Transition to processing
            self.state = constants.STATE_PROCESSING_TURN
            self.calculate_and_report()

        # Step 2 Response: Receive Defense Announce (Attacker side)
        elif msg_type == constants.MSG_DEFENSE_ANNOUNCE:
            print("Opponent is ready. Calculating damage...")
            self.state = constants.STATE_PROCESSING_TURN
            self.calculate_and_report()

        # Step 3: Receive Calculation Report
        elif msg_type == constants.MSG_CALCULATION_REPORT:
            self.handle_calculation_report(message)

        # Step 4: Receive Confirmation
        elif msg_type == constants.MSG_CALCULATION_CONFIRM:
            print("Turn confirmed.")
            self.end_turn()

        # Discrepancy Resolution
        elif msg_type == constants.MSG_RESOLUTION_REQUEST:
            print("Received Resolution Request. Re-evaluating...")
            # For simplicity, we just accept their value if we are not host, or something.
            # But RFC says "If it agrees... sends ACK".
            pass

        # Game Over
        elif msg_type == constants.MSG_GAME_OVER:
            winner = message.get(constants.KEY_WINNER)
            print(f"GAME OVER! Winner: {winner}")
            self.state = constants.STATE_GAME_OVER

        return None
    
    def calculate_and_report(self):
        """
        Step 3: Calculate damage and send report.
        """
        move_name = self.turn_data.get("move_name")
        attacker_name = self.turn_data.get("attacker")
        defender_name = self.turn_data.get("defender")
        
        # Determine Boosts
        # If I am the attacker, I use MY atk boost. If opponent is attacker, use THEIR atk boost.
        if attacker_name == self.my_pokemon['name']:
            use_atk = self.my_stat_boosts['sp_atk'] > 0
        else:
            use_atk = self.opp_stat_boosts['sp_atk'] > 0
            
        if defender_name == self.my_pokemon['name']:
            use_def = self.my_stat_boosts['sp_def'] > 0
        else:
            use_def = self.opp_stat_boosts['sp_def'] > 0

        # Calculate
        result = self.pokemon_manager.calculate_damage(
            attacker_name, 
            defender_name, 
            move_name,
            use_atk_boost=use_atk,
            use_def_boost=use_def
        )
        damage = result['damage']
        
        # Store local calculation
        self.turn_data["local_damage"] = damage
        
        # Send Report
        # We need to predict HP remaining.
        if self.is_my_turn:
            current_hp = self.opponent_pokemon[constants.KEY_HP]
            remaining = current_hp - damage
        else:
            current_hp = self.my_pokemon[constants.KEY_HP]
            remaining = current_hp - damage
            
        report = {
            constants.KEY_ATTACKER: attacker_name,
            constants.KEY_MOVE_USED: move_name,
            constants.KEY_DMG_DEALT: damage,
            constants.KEY_HP_REMAINING: remaining,
            constants.KEY_STATUS_MSG: f"{attacker_name} used {move_name}!"
        }
        self.network_manager.send_reliable(constants.MSG_CALCULATION_REPORT, report)

    def handle_calculation_report(self, message):
        """
        Compare local calculation with received report.
        """
        remote_damage = int(message.get(constants.KEY_DMG_DEALT))
        local_damage = self.turn_data.get("local_damage")
        
        if remote_damage == local_damage:
            print(f"Calculations match! Damage: {local_damage}")
            
            # Apply damage
            if self.is_my_turn:
                self.opponent_pokemon[constants.KEY_HP] -= local_damage
            else:
                self.my_pokemon[constants.KEY_HP] -= local_damage
                
            # Send Confirm
            self.network_manager.send_reliable(constants.MSG_CALCULATION_CONFIRM, {})
            
            # Check Game Over
            if self.my_pokemon[constants.KEY_HP] <= 0:
                self.send_game_over(self.opponent_pokemon['name'], self.my_pokemon['name'])
            elif self.opponent_pokemon[constants.KEY_HP] <= 0:
                # Wait for opponent to send Game Over or we can send it too
                pass
                
            if not self.pending_confirmation:
                self.pending_confirmation = True
            else:
                self.end_turn()
                
        else:
            print(f"DISCREPANCY! Local: {local_damage}, Remote: {remote_damage}")
            # Send Resolution Request
            res_data = {
                constants.KEY_ATTACKER: self.turn_data["attacker"],
                constants.KEY_MOVE_USED: self.turn_data["move_name"],
                constants.KEY_DMG_DEALT: local_damage
            }
            self.network_manager.send_reliable(constants.MSG_RESOLUTION_REQUEST, res_data)

    def end_turn(self):
        self.pending_confirmation = False
        self.is_my_turn = not self.is_my_turn
        self.state = constants.STATE_WAITING_FOR_MOVE
        print(f"Turn ended. My Turn: {self.is_my_turn}")
        if self.is_my_turn:
            print("Your Turn!")

    def send_game_over(self, winner, loser):
        self.network_manager.send_reliable(constants.MSG_GAME_OVER, {
            constants.KEY_WINNER: winner,
            constants.KEY_LOSER: loser
        })
        print(f"GAME OVER. {winner} wins!")
        self.state = constants.STATE_GAME_OVER