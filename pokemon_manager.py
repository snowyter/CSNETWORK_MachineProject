import csv
import random
import math
import os

class PokemonManager:
    def __init__(self, pokemon_csv='pokemon.csv', moves_csv='moves.csv'):
        self.pokedex = {}
        self.moves = {} 
        
        # Load Pokemon Stats
        self.load_pokemon_data(pokemon_csv)
        
        # Try to load moves from CSV, otherwise use default
        if os.path.exists(moves_csv):
            self.load_moves_from_csv(moves_csv)
        else:
            print("Moves CSV not found. Using default hardcoded moves.")
            self.initialize_default_moves()
        
        # Simple Type Effectiveness Chart (Attacker -> Defender)
        self.type_chart = {
            "Fire": {"Grass": 2.0, "Water": 0.5, "Fire": 0.5, "Ice": 2.0, "Bug": 2.0, "Steel": 2.0},
            "Water": {"Fire": 2.0, "Grass": 0.5, "Water": 0.5, "Ground": 2.0, "Rock": 2.0},
            "Grass": {"Water": 2.0, "Fire": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Flying": 0.5, "Bug": 0.5},
            "Electric": {"Water": 2.0, "Grass": 0.5, "Ground": 0.0, "Flying": 2.0},
            "Normal": {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
            "Ice": {"Grass": 2.0, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Fire": 0.5, "Water": 0.5, "Ice": 0.5},
            "Fighting": {"Normal": 2.0, "Ice": 2.0, "Rock": 2.0, "Dark": 2.0, "Steel": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5},
            "Poison": {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0},
            "Ground": {"Fire": 2.0, "Electric": 2.0, "Poison": 2.0, "Rock": 2.0, "Steel": 2.0, "Grass": 0.5, "Bug": 0.5, "Flying": 0.0},
            "Flying": {"Grass": 2.0, "Fighting": 2.0, "Bug": 2.0, "Electric": 0.5, "Rock": 0.5, "Steel": 0.5},
            "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Steel": 0.5, "Dark": 0.0},
            "Bug": {"Grass": 2.0, "Psychic": 2.0, "Dark": 2.0, "Fire": 0.5, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Ghost": 0.5, "Steel": 0.5, "Fairy": 0.5},
            "Rock": {"Fire": 2.0, "Ice": 2.0, "Flying": 2.0, "Bug": 2.0, "Fighting": 0.5, "Ground": 0.5, "Steel": 0.5},
            "Ghost": {"Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Normal": 0.0},
            "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
            "Steel": {"Ice": 2.0, "Rock": 2.0, "Fairy": 2.0, "Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Steel": 0.5},
            "Dark": {"Psychic": 2.0, "Ghost": 2.0, "Fighting": 0.5, "Dark": 0.5, "Fairy": 0.5},
            "Fairy": {"Fighting": 2.0, "Dragon": 2.0, "Dark": 2.0, "Fire": 0.5, "Poison": 0.5, "Steel": 0.5}
        }

    def load_pokemon_data(self, csv_path):
        """Loads Pokemon stats from the provided CSV file."""
        try:
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # [cite_start]Mapping the actual columns from your file [cite: 34]
                    name = row['name'].strip()
                    
                    # Handle Type 2 being empty
                    type2 = row.get('type2', '').strip()
                    if not type2:
                        type2 = None

                    self.pokedex[name] = {
                        "type1": row['type1'].strip(),
                        "type2": type2,
                        "hp": int(row['hp']),
                        "attack": int(row['attack']),
                        "defense": int(row['defense']),
                        # Note: CSV uses 'sp_attack' not 'Sp. Atk'
                        "sp_atk": int(row['sp_attack']),
                        "sp_def": int(row['sp_defense']),
                        "speed": int(row['speed'])
                    }
            print(f"PokemonManager: Loaded {len(self.pokedex)} Pokemon.")
        except FileNotFoundError:
            print(f"ERROR: Could not find {csv_path}!")
        except Exception as e:
            print(f"ERROR loading Pokemon CSV: {e}")

    def initialize_default_moves(self):
        """Hardcoded moves."""
        self.moves = {
            "Thunderbolt": {"type": "Electric", "power": 90, "category": "Special"},
            "Flamethrower": {"type": "Fire", "power": 90, "category": "Special"},
            "Surf": {"type": "Water", "power": 90, "category": "Special"},
            "Earthquake": {"type": "Ground", "power": 100, "category": "Physical"},
            "Slash": {"type": "Normal", "power": 70, "category": "Physical"},
            "Tackle": {"type": "Normal", "power": 40, "category": "Physical"},
            "Ice Beam": {"type": "Ice", "power": 90, "category": "Special"},
            "Psychic": {"type": "Psychic", "power": 90, "category": "Special"}
        }

    def get_pokemon(self, name):
        """Returns the stats dictionary for a specific Pokemon."""
        # Case insensitive lookup
        for key in self.pokedex:
            if key.lower() == name.lower():
                return self.pokedex[key]
        return None

    def get_move(self, move_name):
        return self.moves.get(move_name)

    def get_type_effectiveness(self, move_type, defender_type1, defender_type2=None):
        """Calculates type multiplier."""
        multiplier = 1.0
        
        # Check against Type 1
        if move_type in self.type_chart:
            if defender_type1 in self.type_chart[move_type]:
                multiplier *= self.type_chart[move_type][defender_type1]
        
        # Check against Type 2 (if it exists)
        if defender_type2 and move_type in self.type_chart:
             if defender_type2 in self.type_chart[move_type]:
                multiplier *= self.type_chart[move_type][defender_type2]
                
        return multiplier

    def calculate_damage(self, attacker_name, defender_name, move_name):
        attacker = self.get_pokemon(attacker_name)
        defender = self.get_pokemon(defender_name)
        move = self.get_move(move_name)

        if not attacker:
            print(f"Error: Pokemon {attacker_name} not found.")
            return None
        if not defender:
            print(f"Error: Pokemon {defender_name} not found.")
            return None
        if not move:
            print(f"Error: Move {move_name} not found.")
            return None

        # Determine Stats (Physical vs Special)
        level = 50
        power = move['power']
        
        if move['category'] == "Physical":
            a_stat = attacker['attack']
            d_stat = defender['defense']
        else:
            a_stat = attacker['sp_atk']
            d_stat = defender['sp_def']

        # Base Damage Calculations
        # Formula: ((2 * Level / 5 + 2) * Power * A / D) / 50 + 2
        base_damage = ((2 * level / 5 + 2) * power * (a_stat / d_stat)) / 50 + 2

        # Modifiers
        # STAB
        stab = 1.5 if move['type'] in [attacker['type1'], attacker['type2']] else 1.0
        
        # Type Effectiveness
        type_mult = self.get_type_effectiveness(move['type'], defender['type1'], defender['type2'])
        
        # Random Factor (0.85 to 1.0)
        random_factor = random.uniform(0.85, 1.0)

        final_damage = math.floor(base_damage * stab * type_mult * random_factor)

        return {
            "damage": int(final_damage),
            "attack_stat_used": a_stat,
            "defense_stat_used": d_stat,
            "type_effectiveness": type_mult
        }