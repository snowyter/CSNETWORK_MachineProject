# Network Config
BUFFER_SIZE = 4096 
DEFAULT_PORT = 12345
BROADCAST_ADDR = "255.255.255.255"

# For reliability layer
TIMEOUT_SECONDS = 0.5  # 500 milliseconds
MAX_RETRIES = 3

# Message types
MSG_HANDSHAKE_REQUEST  = "HANDSHAKE_REQUEST"
MSG_HANDSHAKE_RESPONSE = "HANDSHAKE_RESPONSE"
MSG_SPECTATOR_REQUEST  = "SPECTATOR_REQUEST" 
MSG_BATTLE_SETUP       = "BATTLE_SETUP"      
MSG_ATTACK_ANNOUNCE    = "ATTACK_ANNOUNCE"    
MSG_DEFENSE_ANNOUNCE   = "DEFENSE_ANNOUNCE"   
MSG_CALCULATION_REPORT = "CALCULATION_REPORT" 
MSG_CALCULATION_CONFIRM= "CALCULATION_CONFIRM"  
MSG_RESOLUTION_REQUEST = "RESOLUTION_REQUEST" 
MSG_GAME_OVER          = "GAME_OVER"          
MSG_CHAT_MESSAGE       = "CHAT_MESSAGE"       
MSG_ACK                = "ACK"               

# Game states
STATE_SETUP            = "SETUP"            # Initial handshake phase
STATE_WAITING_FOR_MOVE = "WAITING_FOR_MOVE" # Waiting for player to pick a move
STATE_PROCESSING_TURN  = "PROCESSING_TURN"  # Calculating damage/Comparing results
STATE_GAME_OVER        = "GAME_OVER"        # Battle finished

# Communication Modes
MODE_P2P = "P2P"
MODE_BROADCAST = "BROADCAST"

# Chat content types
CONTENT_TYPE_TEXT      = "TEXT"
CONTENT_TYPE_STICKER   = "STICKER"

# Protocol keys
KEY_MSG_TYPE       = "message_type"
KEY_SEQ_NUM        = "sequence_number"
KEY_ACK_NUM        = "ack_number"
KEY_SENDER         = "sender_name"
KEY_CONTENT_TYPE   = "content_type"
KEY_MSG_TEXT       = "message_text"
KEY_STICKER_DATA   = "sticker_data"
KEY_SEED           = "seed"
KEY_COMM_MODE      = "communication_mode"
KEY_POKEMON_NAME   = "pokemon_name"
KEY_POKEMON_DATA   = "pokemon"
KEY_STAT_BOOSTS    = "stat_boosts"
KEY_MOVE_NAME      = "move_name"
KEY_ATTACKER       = "attacker"
KEY_MOVE_USED      = "move_used"
KEY_REMAINING_HEALTH = "remaining_health"
KEY_DMG_DEALT      = "damage_dealt"
KEY_HP_REMAINING   = "defender_hp_remaining"
KEY_STATUS_MSG     = "status_message"
KEY_WINNER         = "winner"
KEY_LOSER          = "loser"

# Stat keys for Pokemon Data
KEY_HP             = "hp"
KEY_MAX_HP         = "max_hp"
KEY_ATTACK         = "attack"
KEY_DEFENSE        = "defense"
KEY_SP_ATTACK      = "sp_attack"
KEY_SP_DEFENSE     = "sp_defense"
KEY_SPEED          = "speed"
KEY_TYPE1          = "type1"
KEY_TYPE2          = "type2"