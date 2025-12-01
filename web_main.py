import sys
import io
import json
import time
import threading
import socket
import argparse
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit

# Import existing modules
import constants
from network_manager import NetworkManager
from pokemon_manager import PokemonManager
from game_engine import GameEngine

# ===================== HTML Template =====================
# Embedded HTML/CSS/JS as requested (Single file style)
HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Pokemon P2P Web GUI</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #e8e8e8; height: 100vh; display: flex; flex-direction: column; }
    
    /* Layout */
    .container { display: flex; flex: 1; padding: 10px; gap: 10px; overflow: hidden; }
    .col-left { width: 250px; display: flex; flex-direction: column; gap: 10px; }
    .col-center { flex: 1; display: flex; flex-direction: column; gap: 10px; }
    .col-right { width: 300px; display: flex; flex-direction: column; gap: 10px; }
    
    .card { background: #f5f5f5; border-radius: 8px; padding: 12px; border: 1px solid #d0d0d0; display: flex; flex-direction: column; }
    .card h2 { margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; border-bottom: 2px solid #aaa; padding-bottom: 5px; }
    .card.grow { flex: 1; overflow: hidden; }
    
    /* Components */
    input, select, button { width: 100%; padding: 8px; margin-bottom: 5px; border-radius: 4px; border: 1px solid #ccc; }
    button { cursor: pointer; background: #ddd; font-weight: bold; }
    button:hover { background: #ccc; }
    button.primary { background: #6aa3d5; color: white; border: none; }
    button.primary:hover { background: #5890c0; }
    button.danger { background: #e57373; color: white; border: none; }
    
    .log-box { flex: 1; overflow-y: auto; background: #1a1a1a; color: #d0d0d0; font-family: monospace; font-size: 11px; padding: 5px; border-radius: 4px; }
    .log-line { margin-bottom: 2px; border-bottom: 1px solid #333; }
    
    .pokemon-list { flex: 1; overflow-y: auto; background: white; border: 1px solid #ccc; border-radius: 4px; }
    .pokemon-item { padding: 5px; cursor: pointer; border-bottom: 1px solid #eee; font-size: 12px; }
    .pokemon-item:hover { background: #e8f4f8; }
    .pokemon-item.selected { background: #6aa3d5; color: white; }
    
    .status-bar { background: #333; color: white; padding: 5px 10px; font-size: 12px; display: flex; justify-content: space-between; }
    
    .hidden { display: none !important; }
    
    /* Battle Display */
    .battle-display { background: white; padding: 10px; border-radius: 4px; border: 1px solid #ccc; text-align: center; }
    .hp-bar { width: 100%; height: 15px; background: #ddd; border-radius: 3px; overflow: hidden; margin: 5px 0; }
    .hp-fill { height: 100%; background: #5cb85c; transition: width 0.3s; }
    .vs-badge { font-weight: bold; color: #e57373; margin: 10px 0; }

    .controls-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
    
    /* Modal */
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); justify-content: center; align-items: center; z-index: 1000; }
    .modal-content { background: white; padding: 20px; border-radius: 8px; text-align: center; min-width: 300px; }
    .modal.show { display: flex; }
  </style>
</head>
<body>
  <div id="game-over-modal" class="modal">
    <div class="modal-content">
        <h2 id="winner-text">Game Over</h2>
        <p>Thanks for playing!</p>
    </div>
  </div>
  <div class="status-bar">
    <span id="connection-status">Disconnected</span>
    <span id="role-display">Role: None</span>
  </div>

  <div class="container">
    <!-- LEFT: Setup & Pokemon -->
    <div class="col-left">
      <!-- Connection Panel -->
      <div class="card" id="card-conn">
        <h2>Connection</h2>
        <input id="player-name" placeholder="Name" value="Player">
        <input id="player-port" type="number" placeholder="My Port" value="5000">
        <button onclick="initGame()" class="primary">Initialize</button>
        
        <div id="menu-actions" class="hidden">
            <hr>
            <button onclick="hostGame()">Host Game</button>
            <div style="display:flex; gap:5px;">
                <input id="target-ip" placeholder="Target IP" value="127.0.0.1">
                <input id="target-port" placeholder="Port" value="5000" style="width: 60px;">
            </div>
            <button onclick="joinGame()">Join Game</button>
            <button onclick="spectateGame()">Spectate</button>
        </div>
      </div>

      <!-- Pokemon Selection -->
      <div class="card grow" id="card-pokemon">
        <h2>Pokemon</h2>
        <input id="search" placeholder="Search..." oninput="filterPokemon()">
        <div class="pokemon-list" id="pokemon-list"></div>
        <div style="margin-top: 5px;">
            <label><small>Sp.Atk Boosts:</small> <input type="number" id="boost-atk" value="0" min="0" max="10" style="width: 40px;"></label>
            <label><small>Sp.Def Boosts:</small> <input type="number" id="boost-def" value="0" min="0" max="10" style="width: 40px;"></label>
        </div>
        <button onclick="selectPokemon()" class="primary" id="btn-select" disabled>Select Pokemon</button>
      </div>
    </div>

    <!-- CENTER: Battle -->
    <div class="col-center">
      <div class="card grow">
        <h2>Battle Arena</h2>
        <div id="battle-area" class="hidden">
            <div class="battle-display">
                <h3>You</h3>
                <div id="my-poke-name">???</div>
                <div class="hp-bar"><div id="my-hp" class="hp-fill" style="width: 100%;"></div></div>
                <div id="my-hp-text">0/0</div>
            </div>
            
            <div class="vs-badge">VS</div>
            
            <div class="battle-display">
                <h3>Opponent</h3>
                <div id="opp-poke-name">???</div>
                <div class="hp-bar"><div id="opp-hp" class="hp-fill" style="width: 100%;"></div></div>
                <div id="opp-hp-text">0/0</div>
            </div>
        </div>
        <div id="waiting-msg" style="text-align: center; padding: 20px; color: #888;">
            Waiting for game to start...
        </div>
      </div>

      <div class="card">
        <h2>Actions</h2>
        <div class="controls-grid">
            <button onclick="attack('Thunderbolt')">Thunderbolt</button>
            <button onclick="attack('Flamethrower')">Flamethrower</button>
            <button onclick="attack('Surf')">Surf</button>
            <button onclick="attack('Earthquake')">Earthquake</button>
            <button onclick="attack('Slash')">Slash</button>
            <button onclick="attack('Tackle')">Tackle</button>
            <button onclick="attack('Ice Beam')">Ice Beam</button>
            <button onclick="attack('Psychic')">Psychic</button>
        </div>
        <label style="margin-top: 5px;"><input type="checkbox" id="use-boost"> Use Boost</label>
      </div>
    </div>

    <!-- RIGHT: Logs & Chat -->
    <div class="col-right">
      <div class="card grow">
        <h2>Game Log</h2>
        <div id="game-log" class="log-box"></div>
      </div>
      <div class="card">
        <h2>Chat & Stickers</h2>
        <div style="display:flex; gap:5px; margin-bottom: 5px;">
            <input id="chat-msg" placeholder="Message...">
            <button onclick="sendChat()" style="width: auto;">Send</button>
        </div>
        <div style="display:flex; gap:5px; align-items: center;">
            <input type="file" id="sticker-input" accept="image/*" style="font-size: 11px;">
            <button onclick="sendSticker()" class="secondary" style="width: auto;">Sticker</button>
        </div>
        <small style="color: #666; font-size: 10px;">Max 10MB, 320x320px</small>
      </div>
    </div>
  </div>

  <script>
    const socket = io();
    let pokemonList = [];
    let selectedPokemon = null;

    // --- Socket Events ---
    socket.on('connect', () => {
        log("Connected to Web GUI.");
        socket.emit('check_init'); // Ask server if we are already initialized
    });
    socket.on('game_log', (data) => log(data.message));
    
    socket.on('init_success', (data) => {
        document.getElementById('connection-status').innerText = `Online (${data.name}:${data.port})`;
        document.getElementById('menu-actions').classList.remove('hidden');
        document.getElementById('card-conn').querySelector('input').disabled = true;
        document.getElementById('card-conn').querySelector('button').disabled = true;
        
        // Update fields if provided
        if(data.name) document.getElementById('player-name').value = data.name;
        if(data.port) document.getElementById('player-port').value = data.port;
        
        loadPokemon();
    });

    socket.on('battle_update', (data) => {
        document.getElementById('waiting-msg').classList.add('hidden');
        document.getElementById('battle-area').classList.remove('hidden');
        
        document.getElementById('my-poke-name').innerText = data.my_name || '???';
        document.getElementById('opp-poke-name').innerText = data.opp_name || '???';
        
        updateHp('my-hp', 'my-hp-text', data.my_hp, data.my_max_hp);
        updateHp('opp-hp', 'opp-hp-text', data.opp_hp, data.opp_max_hp);
        
        if (data.state === 'GAME_OVER') {
            document.getElementById('game-over-modal').classList.add('show');
            document.getElementById('winner-text').innerText = `Game Over! Winner: ${data.winner || 'Unknown'}`;
            // Disable controls
            document.querySelectorAll('.controls-grid button').forEach(b => b.disabled = true);
        }
    });

    // --- Functions ---
    function log(msg, isSticker=false, stickerData=null) {
        const box = document.getElementById('game-log');
        const div = document.createElement('div');
        div.className = 'log-line';
        if (isSticker) {
            div.innerHTML = `${msg}<br><img src="data:image/png;base64,${stickerData}" style="max-width:100px; border-radius:4px;">`;
        } else {
            div.innerText = msg;
        }
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    }

    socket.on('chat_sticker', (data) => {
        log(`[${data.sender}]: sent a sticker`, true, data.data);
    });

    function updateHp(barId, textId, current, max) {
        if (max <= 0) return;
        const pct = Math.max(0, Math.min(100, (current / max) * 100));
        document.getElementById(barId).style.width = pct + '%';
        document.getElementById(textId).innerText = `${current}/${max}`;
    }

    function initGame() {
        const name = document.getElementById('player-name').value;
        const port = document.getElementById('player-port').value;
        socket.emit('init_game', { name, port });
    }

    function hostGame() {
        socket.emit('host_game');
        document.getElementById('role-display').innerText = "Role: HOST";
    }

    function joinGame() {
        const ip = document.getElementById('target-ip').value;
        const port = document.getElementById('target-port').value;
        socket.emit('join_game', { ip, port, spectator: false });
        document.getElementById('role-display').innerText = "Role: JOINER";
    }

    function spectateGame() {
        const ip = document.getElementById('target-ip').value;
        const port = document.getElementById('target-port').value;
        socket.emit('join_game', { ip, port, spectator: true });
        document.getElementById('role-display').innerText = "Role: SPECTATOR";
    }

    function loadPokemon() {
        fetch('/pokemon_list').then(r => r.json()).then(data => {
            pokemonList = data;
            filterPokemon();
        });
    }

    function filterPokemon() {
        const q = document.getElementById('search').value.toLowerCase();
        const list = document.getElementById('pokemon-list');
        list.innerHTML = '';
        pokemonList.filter(p => p.toLowerCase().includes(q)).forEach(p => {
            const div = document.createElement('div');
            div.className = 'pokemon-item';
            div.innerText = p;
            div.onclick = () => {
                selectedPokemon = p;
                document.querySelectorAll('.pokemon-item').forEach(el => el.classList.remove('selected'));
                div.classList.add('selected');
                document.getElementById('btn-select').disabled = false;
                document.getElementById('btn-select').innerText = `Select ${p}`;
            };
            list.appendChild(div);
        });
    }

    function selectPokemon() {
        if(!selectedPokemon) return;
        const atk = document.getElementById('boost-atk').value;
        const def = document.getElementById('boost-def').value;
        socket.emit('select_pokemon', { name: selectedPokemon, sp_atk: atk, sp_def: def });
    }

    function attack(move) {
        const boost = document.getElementById('use-boost').checked;
        socket.emit('attack', { move, boost });
        document.getElementById('use-boost').checked = false;
    }

    function sendChat() {
        const msg = document.getElementById('chat-msg').value;
        if(msg) {
            socket.emit('chat', { message: msg });
            document.getElementById('chat-msg').value = '';
        }
    }

    function sendSticker() {
        const input = document.getElementById('sticker-input');
        const file = input.files && input.files[0];
        if (!file) { alert('Choose an image first.'); return; }
        if (file.size >= 10 * 1024 * 1024) { alert('Sticker must be < 10MB.'); return; }
        
        const img = new Image();
        const reader = new FileReader();
        reader.onload = function(e) {
            img.onload = function() {
                if (img.width !== 320 || img.height !== 320) {
                    alert('Sticker must be exactly 320x320 pixels.');
                    return;
                }
                const base64 = e.target.result.split(',')[1];
                socket.emit('sticker', { data: base64 });
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
  </script>
</body>
</html>
"""

# ===================== Backend Logic =====================

class StreamLogger(io.StringIO):
    def __init__(self, callback, original_stdout):
        super().__init__()
        self.callback = callback
        self.original_stdout = original_stdout

    def write(self, message):
        self.original_stdout.write(message)
        if message.strip():
            self.callback(message.strip())

    def flush(self):
        self.original_stdout.flush()

class WebGameClient:
    def __init__(self, socketio):
        self.socketio = socketio
        self.net = None
        self.poke = PokemonManager("pokemon.csv")
        self.engine = None
        self.running = False
        self.player_name = "Player"
        self.is_spectator = False
        
        self.port = 0
        
        # Capture stdout
        sys.stdout = StreamLogger(self.log_emit, sys.stdout)
        
        # Background thread
        self.bg_thread = threading.Thread(target=self.game_loop, daemon=True)
        self.bg_thread.start()

    def log_emit(self, msg):
        self.socketio.emit('game_log', {'message': msg})

    def initialize(self, name, port):
        port = int(port)
        if self.net:
            if self.port == port:
                print(f"Already initialized on port {port}. Updating name to {name}.")
                self.player_name = name
                return
            else:
                print(f"Re-initializing on new port {port} (Old: {self.port})...")
                # Ideally we should close the old socket, but NetworkManager doesn't have a close method exposed cleanly.
                # We will just overwrite self.net, the old thread might persist but won't be referenced.
                # This is a hack for the prototype.
                try:
                    self.net.sock.close()
                except: pass

        self.player_name = name
        self.port = port
        try:
            self.net = NetworkManager(port=self.port)
            self.engine = GameEngine(self.poke, self.net)
            self.running = True
            print(f"Initialized {name} on port {port}")
        except OSError as e:
            print(f"Failed to bind port {port}: {e}")
            self.running = False
            self.net = None

    def host_game(self):
        print("Hosting game... Waiting for connections.")
        self.net.reset_connection()
        self.engine = GameEngine(self.poke, self.net)
        self.net.send_broadcast(constants.MSG_BATTLE_SETUP, {
            "communication_mode": "BROADCAST",
            "status": "OPEN",
            "host_name": self.player_name
        })
        self.engine.is_host = True

    def join_game(self, ip, port, spectator=False):
        self.is_spectator = spectator
        role = "Spectator" if spectator else "Challenger"
        print(f"Connecting to {ip}:{port} as {role}...")
        
        self.net.reset_connection()
        self.engine = GameEngine(self.poke, self.net)
        
        self.net.set_peer(ip)
        self.net.peer_address = (ip, int(port))
        
        msg_type = constants.MSG_SPECTATOR_REQUEST if spectator else constants.MSG_HANDSHAKE_REQUEST
        self.net.send_reliable(msg_type, {constants.KEY_SENDER: self.player_name})

    def select_pokemon(self, name, sp_atk, sp_def):
        if self.is_spectator: return
        
        data = self.poke.get_pokemon(name)
        if not data: return

        self.engine.set_my_pokemon(name, int(sp_atk), int(sp_def))
        
        # Send Setup
        boosts = {"special_attack_uses": int(sp_atk), "special_defense_uses": int(sp_def)}
        self.net.send_reliable(constants.MSG_BATTLE_SETUP, {
            constants.KEY_POKEMON_NAME: name,
            constants.KEY_STAT_BOOSTS: json.dumps(boosts),
            constants.KEY_POKEMON_DATA: json.dumps(data),
            constants.KEY_COMM_MODE: constants.MODE_P2P
        })
        
        self.check_start()

    def attack(self, move, boost):
        if self.is_spectator: return
        self.engine.select_move(move, boost)

    def send_chat(self, msg):
        self.net.send_reliable(constants.MSG_CHAT_MESSAGE, {
            constants.KEY_SENDER: self.player_name,
            constants.KEY_CONTENT_TYPE: constants.CONTENT_TYPE_TEXT,
            constants.KEY_MSG_TEXT: msg
        })
        print(f"[YOU]: {msg}")

    def send_sticker(self, b64_data):
        self.net.send_reliable(constants.MSG_CHAT_MESSAGE, {
            constants.KEY_SENDER: self.player_name,
            constants.KEY_CONTENT_TYPE: constants.CONTENT_TYPE_STICKER,
            "sticker_data": b64_data # Using custom key for simplicity, or could use MSG_TEXT if protocol allows
        })
        print(f"[YOU]: Sent a sticker.")
        # Self-echo
        self.socketio.emit('chat_sticker', {'sender': 'You', 'data': b64_data})

    def check_start(self):
        if self.engine.my_pokemon and self.engine.opponent_pokemon and self.engine.seed is not None:
             # Idempotency handled by engine state usually, but let's be safe
             if self.engine.state == constants.STATE_SETUP:
                 self.engine.start_battle(self.engine.is_host, self.engine.seed)

    def game_loop(self):
        while True:
            if self.running and self.net:
                # 1. Receive
                msg = self.net.receive_message()
                if msg:
                    self.handle_message(msg)
                
                # 2. Resend
                self.net.check_resend()
                
                # 3. Emit State Update
                self.emit_state()
                
            time.sleep(0.05)

    def handle_message(self, msg):
        msg_type = msg.get(constants.KEY_MSG_TYPE)
        
        # Handshake Logic (Simplified from main.py)
        if msg_type == constants.MSG_HANDSHAKE_REQUEST:
            if self.engine.is_host:
                self.net.peer_address = msg.get('source_addr')
                seed = 12345 # Fixed seed for simplicity or random
                self.engine.seed = seed
                self.net.send_reliable(constants.MSG_HANDSHAKE_RESPONSE, {
                    constants.KEY_SEED: seed, "status": "OK"
                })
                print(f"Client connected from {self.net.peer_address}")

        elif msg_type == constants.MSG_HANDSHAKE_RESPONSE:
            self.engine.seed = int(msg.get(constants.KEY_SEED))
            print("Connected to Host!")

        elif msg_type == constants.MSG_SPECTATOR_REQUEST:
            self.net.add_spectator(msg.get('source_addr'))
            print(f"Spectator added: {msg.get('source_addr')}")

        elif msg_type == constants.MSG_CHAT_MESSAGE:
            sender = msg.get(constants.KEY_SENDER)
            ctype = msg.get(constants.KEY_CONTENT_TYPE)
            
            if ctype == constants.CONTENT_TYPE_STICKER:
                print(f"[{sender}]: [Sticker]")
                self.socketio.emit('chat_sticker', {'sender': sender, 'data': msg.get('sticker_data')})
            else:
                print(f"[{sender}]: {msg.get(constants.KEY_MSG_TEXT)}")
            
            if self.engine.is_host: # Relay
                self.relay_chat(msg)

        # Relay Game Messages if Host
        if self.engine.is_host and msg_type in [
            constants.MSG_BATTLE_SETUP,
            constants.MSG_ATTACK_ANNOUNCE,
            constants.MSG_DEFENSE_ANNOUNCE,
            constants.MSG_CALCULATION_REPORT,
            constants.MSG_CALCULATION_CONFIRM,
            constants.MSG_GAME_OVER,
            constants.MSG_RESOLUTION_REQUEST
        ]:
            self.relay_chat(msg)

        # Engine Logic
        self.engine.process_message(msg)
        
        # Check start after setup
        if msg_type == constants.MSG_BATTLE_SETUP:
            self.check_start()

    def relay_chat(self, msg):
        # Simplified relay
        source = msg.get('source_addr')
        data = {k:v for k,v in msg.items() if k not in ['source_addr', constants.KEY_SEQ_NUM]}
        packet = self.net.construct_message(constants.MSG_CHAT_MESSAGE, data)
        
        # Send to peer if not source
        if self.net.peer_address and source != self.net.peer_address:
            self.net.sock.sendto(packet, self.net.peer_address)
        
        # Send to spectators
        for spec in self.net.spectators:
            if spec != source:
                self.net.sock.sendto(packet, spec)

    def emit_state(self):
        # Send vital stats to UI
        if self.engine and self.engine.my_pokemon:
            my_hp = self.engine.my_pokemon.get('hp', 0)
            my_max = self.engine.my_pokemon.get('max_hp', my_hp)
            my_name = self.engine.my_pokemon.get('name', '???')
        else:
            my_hp, my_max, my_name = 0, 0, '???'
            
        if self.engine and self.engine.opponent_pokemon:
            opp_hp = self.engine.opponent_pokemon.get('hp', 0)
            opp_max = self.engine.opponent_pokemon.get('max_hp', opp_hp)
            opp_name = self.engine.opponent_pokemon.get('name', '???')
        else:
            opp_hp, opp_max, opp_name = 0, 0, '???'

        winner = "???"
        if self.engine and self.engine.state == constants.STATE_GAME_OVER:
             # Try to determine winner from HP if not explicitly stored, 
             # but usually engine prints it. We'll check if we can get it from engine state if we stored it there.
             # For now, let's just infer from HP or check if engine has a winner field (it doesn't explicitly, but we can infer)
             if my_hp > 0 and opp_hp <= 0:
                 winner = my_name
             elif opp_hp > 0 and my_hp <= 0:
                 winner = opp_name
             else:
                 winner = "Draw/Unknown"

        self.socketio.emit('battle_update', {
            'my_hp': my_hp, 'my_max_hp': my_max, 'my_name': my_name,
            'opp_hp': opp_hp, 'opp_max_hp': opp_max, 'opp_name': opp_name,
            'state': self.engine.state if self.engine else 'SETUP',
            'winner': winner
        })

# ===================== Flask App =====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')
client = WebGameClient(socketio)

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/pokemon_list')
def get_pokemon():
    return jsonify(sorted(list(client.poke.pokedex.keys())))

@socketio.on('init_game')
def on_init(data):
    client.initialize(data['name'], data['port'])
    emit('init_success', data)

@socketio.on('check_init')
def on_check_init():
    if client.running and client.net:
        emit('init_success', {'name': client.player_name, 'port': client.port})

@socketio.on('host_game')
def on_host():
    client.host_game()

@socketio.on('join_game')
def on_join(data):
    client.join_game(data['ip'], data['port'], data['spectator'])

@socketio.on('select_pokemon')
def on_select(data):
    client.select_pokemon(data['name'], data['sp_atk'], data['sp_def'])

@socketio.on('attack')
def on_attack(data):
    client.attack(data['move'], data['boost'])

@socketio.on('chat')
def on_chat(data):
    client.send_chat(data['message'])

@socketio.on('sticker')
def on_sticker(data):
    client.send_sticker(data['data'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pokemon P2P Web GUI")
    parser.add_argument('--role', choices=['host', 'joiner', 'spectator'], help='Role to start as')
    parser.add_argument('--udp-port', type=int, default=5000, help='Local UDP port')
    parser.add_argument('--http-port', type=int, default=5000, help='Web GUI port')
    parser.add_argument('--host-ip', type=str, default='127.0.0.1', help='Target Host IP')
    parser.add_argument('--host-port', type=int, default=5000, help='Target Host UDP Port')
    parser.add_argument('--name', type=str, default='Player', help='Player Name')
    
    args = parser.parse_args()
    
    # Auto-initialize if role is set
    if args.role:
        print(f"Auto-starting as {args.role} on UDP {args.udp_port}...")
        client.initialize(args.name, args.udp_port)
        
        if args.role == 'host':
            client.host_game()
        elif args.role == 'joiner':
            client.join_game(args.host_ip, args.host_port, spectator=False)
        elif args.role == 'spectator':
            client.join_game(args.host_ip, args.host_port, spectator=True)
            
    socketio.run(app, host='0.0.0.0', port=args.http_port)
