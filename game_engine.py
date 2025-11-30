import constants
from pokemon_manager import PokemonManager

class GameEngine:
    def __init__(self):
        # 1. Connect to the Data Source.
        self.pokemon_manager = PokemonManager()
        
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
    
    def process_message(self, message):
        """
        The Main Brain. Decides what to do with a network message.
        Returns a response dictionary if we need to send something back, or None.
        """
        msg_type = message.get(constants.KEY_MSG_TYPE)
        
        print(f"[Engine] Processing {msg_type}...")

        # 1. SETUP PHASE: Exchanging Pokemon Info
        if msg_type == constants.MSG_BATTLE_SETUP:
            opp_name = message.get(constants.KEY_POKEMON_NAME)
            self.set_opponent_pokemon(opp_name)
            # If both have picked, the game is ready.
            # (In a real implementation, you'd check who goes first here based on speed/coin toss)
            if self.my_pokemon and self.opponent_pokemon:
                self.state = constants.STATE_WAITING_FOR_MOVE
                print("Battle Started! Waiting for moves.")
            return None

        # 2. ATTACK PHASE: Opponent is attacking us
        elif msg_type == constants.MSG_ATTACK_ANNOUNCE:
            move_name = message.get(constants.KEY_MOVE_NAME)
            print(f"Opponent announced attack: {move_name}")
            
            # We must acknowledge this to move to calculation
            # Return a Defense Announce message to be sent by NetworkManager
            return {
                constants.KEY_MSG_TYPE: constants.MSG_DEFENSE_ANNOUNCE
            }

        # 3. DEFENSE PHASE: Opponent acknowledged OUR attack
        elif msg_type == constants.MSG_DEFENSE_ANNOUNCE:
            print("Opponent is ready. Calculating damage...")
            self.state = constants.STATE_PROCESSING_TURN
            # Trigger damage calculation (See Segment 3)
            return self.execute_turn_logic()

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