import constants
from pokemon_manager import PokemonManager

class GameEngine:
    def __init__(self, pokemon_manager, network_manager):
        # 1. Connect to the Data Source.
        self.pokemon_manager = pokemon_manager
        self.network_manager = network_manager
        
        # 2. Initialize State
        self.state = constants.STATE_SETUP
        
        # 3. Player Data (These will be dictionaries with HP, Name, etc.)
        self.my_pokemon = None
        self.opponent_pokemon = None
        
        # 4. Turn Management
        self.is_my_turn = False 
        self.battle_log = [] # To display what happened

    def set_my_pokemon(self, name):
        """Called when YOU pick a pokemon from the UI/Console."""
        data = self.pokemon_manager.get_pokemon(name)
        if data:
            # IMPORTANT: Make a copy()! We modify HP during battle, 
            # we don't want to modify the master pokedex.
            self.my_pokemon = data.copy()
            # Ensure max_hp is set for health bars later
            self.my_pokemon['max_hp'] = self.my_pokemon['hp'] 
            print(f"You selected {name}!")
            return True
        else:
            print(f"Error: Pokemon '{name}' not found.")
            return False

    def set_opponent_pokemon(self, name):
        """Called when we receive a BATTLE_SETUP message from the enemy."""
        data = self.pokemon_manager.get_pokemon(name)
        if data:
            self.opponent_pokemon = data.copy()
            self.opponent_pokemon['max_hp'] = self.opponent_pokemon['hp']
            print(f"Opponent selected {name}!")
            return True
        return False
    
    def start_battle(self, is_host):
        """
        Decides turn order based on Speed.
        """
        my_spd = self.my_pokemon['speed']
        opp_spd = self.opponent_pokemon['speed']
        
        if my_spd > opp_spd:
            self.is_my_turn = True
        elif my_spd < opp_spd:
            self.is_my_turn = False
        else:
            # Speed tie: Host goes first
            self.is_my_turn = is_host
            
        print(f"Battle Started! My Turn: {self.is_my_turn}")
        if self.is_my_turn:
            print("Use /attack [MoveName] to attack!")
        else:
            print("Waiting for opponent...")
        self.state = constants.STATE_WAITING_FOR_MOVE

    def select_move(self, move_name):
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

        self.current_move = move_name
        print(f"You chose {move_name}. Waiting for opponent to acknowledge...")
        
        # Send Announce
        self.network_manager.send_reliable(constants.MSG_ATTACK_ANNOUNCE, {
            constants.KEY_MOVE_NAME: move_name
        })

    def process_message(self, message):
        """
        The Main Brain. Decides what to do with a network message.
        """
        msg_type = message.get(constants.KEY_MSG_TYPE)
        
        print(f"[Engine] Processing {msg_type}...")

        # 1. SETUP PHASE: Exchanging Pokemon Info
        if msg_type == constants.MSG_BATTLE_SETUP:
            opp_name = message.get(constants.KEY_POKEMON_NAME)
            self.set_opponent_pokemon(opp_name)
            # If both have picked, the game is ready.
            if self.my_pokemon and self.opponent_pokemon:
                self.state = constants.STATE_WAITING_FOR_MOVE
                print("Battle Ready. Waiting for start_battle().")

        # 2. ATTACK PHASE: Opponent is attacking us
        elif msg_type == constants.MSG_ATTACK_ANNOUNCE:
            move_name = message.get(constants.KEY_MOVE_NAME)
            print(f"Opponent announced attack: {move_name}")
            
            # We must acknowledge this to move to calculation
            # Send Defense Announce
            self.network_manager.send_reliable(constants.MSG_DEFENSE_ANNOUNCE, {})

        # 3. DEFENSE PHASE: Opponent acknowledged OUR attack
        elif msg_type == constants.MSG_DEFENSE_ANNOUNCE:
            print("Opponent is ready. Calculating damage...")
            self.state = constants.STATE_PROCESSING_TURN
            # Trigger damage calculation
            report = self.execute_turn_logic()
            self.network_manager.send_reliable(constants.MSG_CALCULATION_REPORT, report)
            
            # End of my turn
            self.is_my_turn = False
            self.state = constants.STATE_WAITING_FOR_MOVE
            print("Turn ended. Waiting for opponent...")

        # 4. REPORT PHASE: Receiving damage report
        elif msg_type == constants.MSG_CALCULATION_REPORT:
            damage = int(message.get(constants.KEY_DMG_DEALT))
            move_name = message.get(constants.KEY_MOVE_NAME)
            
            # Apply damage to ME
            self.my_pokemon['hp'] -= damage
            print(f"Opponent used {move_name} and dealt {damage} damage!")
            print(f"My HP: {self.my_pokemon['hp']}")
            
            # It is now my turn
            self.is_my_turn = True
            self.state = constants.STATE_WAITING_FOR_MOVE
            print("Your Turn! Use /attack [MoveName]")

        return None
    
    def execute_turn_logic(self):
        """
        Calculates damage for the current turn and returns a REPORT message.
        """
        # For simplicity, let's assume we store the 'pending_move' somewhere 
        # when the user types it in.
        # You'll need to add `self.current_move = "Thunderbolt"` in your main loop later.
        
        move_name = getattr(self, 'current_move', 'Tackle') # Default to Tackle if bug
        
        # 1. Calculate Damage (Using your Manager code!)
        # Note: We need to know WHO is attacking. 
        # If it's my turn, I calculate my damage to them.
        if self.is_my_turn:
            attacker = self.my_pokemon['name']
            defender = self.opponent_pokemon['name']
        else:
            attacker = self.opponent_pokemon['name']
            defender = self.my_pokemon['name']

        # Call your PokemonManager
        result = self.pokemon_manager.calculate_damage(attacker, defender, move_name)
        
        damage = result['damage']
        
        # 2. Apply Damage (Locally)
        if self.is_my_turn:
            # I hit them
            self.opponent_pokemon['hp'] -= damage
            remaining_hp = self.opponent_pokemon['hp']
        else:
            # They hit me
            self.my_pokemon['hp'] -= damage
            remaining_hp = self.my_pokemon['hp']

        print(f"Turn Result: {attacker} used {move_name}! Dealt {damage} dmg.")

        # 3. Create the Report Message
        return {
            constants.KEY_MSG_TYPE: constants.MSG_CALCULATION_REPORT,
            constants.KEY_DMG_DEALT: damage,
            constants.KEY_HP_REMAINING: remaining_hp,
            constants.KEY_MOVE_NAME: move_name
        }