import constants
import socket
import threading
import queue
import time

class NetworkManager:
    def __init__(self, port = constants.DEFAULT_PORT):

        # Creating UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Enable Broadcast
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Binding the socket to the port
        self.sock.bind(('0.0.0.0', port))

        # Storage reliability
        self.sequence_number = 0  # To track message order 
        self.peer_address = None  # To remember who we are playing against
        self.spectators = [] # List of spectator addresses
        
        self.incoming_messages = queue.Queue()
        self.pending_acks = {} # seq_num -> {packet, timestamp, retries}
        self.received_history = set() # (addr, seq_num)

        self.message_callback = None #store the function we cal when msg arrives

        # Start the listener thread immediately
        # daemon=True means this thread dies automatically when the main program closes
        self.listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.listener_thread.start()

        print(f"NetworkManager: Listening on port {port}")

    def set_peer(self, ip_address):
        self.peer_address = (ip_address, constants.DEFAULT_PORT)

    def add_spectator(self, address):
        if address not in self.spectators:
            self.spectators.append(address)
            print(f"Added spectator: {address}")

    def reset_connection(self):
        """Resets connection state for a new game."""
        self.peer_address = None
        self.sequence_number = 0
        self.pending_acks.clear()
        self.received_history.clear()
        self.spectators.clear()
        print("NetworkManager connection state reset.")

    def construct_message(self, message_type, data=None):
        """
        Takes a message type and a dictionary of data, 
        and turns it into a key:value string.
        """
        if data is None:
            data = {}
            
        # Start with the mandatory message_type 
        msg_str = f"{constants.KEY_MSG_TYPE}: {message_type}\n"
        
        # Add the sequence number (for reliability), SKIP for ACKs
        if message_type != constants.MSG_ACK:
            self.sequence_number += 1
            msg_str += f"{constants.KEY_SEQ_NUM}: {self.sequence_number}\n"
        
        # Add all other data fields
        for key, value in data.items():
            msg_str += f"{key}: {value}\n"
            
        # Convert to bytes
        return msg_str.encode('utf-8')
    
    def send_message(self, message_type, data=None):
        """
        Constructs and sends a UDP packet to the peer.
        """
        if not self.peer_address:
            print("Error: No peer address set! Cannot send.")
            return

        # Build the packet using our helper from Segment 2
        packet = self.construct_message(message_type, data)
        
        # Send
        try:
            self.sock.sendto(packet, self.peer_address)
            print(f"Sent {message_type} to {self.peer_address}")
        except Exception as e:
            print(f"Error sending message: {e}")

    def send_broadcast(self, message_type, data=None):
        """
        Sends a message to the broadcast address.
        """
        packet = self.construct_message(message_type, data)
        try:
            self.sock.sendto(packet, (constants.BROADCAST_ADDR, constants.DEFAULT_PORT))
            print(f"Sent Broadcast {message_type}")
        except Exception as e:
            print(f"Error sending broadcast: {e}")

    def parse_packet(self, data_bytes):
        """
        Decodes received bytes and converts "key: value" lines into a dictionary.
        """
        try:
            # Decode bytes to string
            message_str = data_bytes.decode('utf-8').strip()
            
            # Split into lines
            lines = message_str.split('\n')
            
            parsed_data = {}
            for line in lines:
                if ": " in line:
                    # Split only on the first colon (in case the message text contains colons)
                    key, value = line.split(": ", 1)
                    parsed_data[key] = value
            
            return parsed_data
        except Exception as e:
            print(f"Error parsing packet: {e}")
            return None
        
    def listen_for_messages(self):
        """
        Runs in a separate thread. Continuously waits for incoming UDP packets.
        """
        while True:
            try:
                # Wait for a packet (Blocking call)
                data, addr = self.sock.recvfrom(constants.BUFFER_SIZE)
                
                # Parse the packet
                message = self.parse_packet(data)
                if not message:
                    continue # Skip malformed packets

                # Ignore own broadcasts (basic check)
                # Note: getting own IP is tricky, so we might receive our own broadcast.
                # The game engine should handle ignoring own messages if sender_name matches.

                # If we don't have a peer yet, and this is a valid message, set it (Host logic)
                # BUT only if it's a handshake or we are in a mode that accepts new peers
                # For now, we leave this logic here, but Main might override peer_address
                if self.peer_address is None and message.get(constants.KEY_MSG_TYPE) == constants.MSG_HANDSHAKE_REQUEST:
                    # We don't auto-set peer_address here anymore for security/logic reasons, 
                    # but we pass it to callback so Main can decide.
                    pass

                # Handle ACK
                if message.get(constants.KEY_MSG_TYPE) == constants.MSG_ACK:
                    self.handle_ack(message)
                    continue

                # RELIABILITY: Send ACK immediately if the message has a sequence number
                if constants.KEY_SEQ_NUM in message:
                    seq_num = message[constants.KEY_SEQ_NUM]
                    self.send_ack(seq_num, addr)
                    
                    # DUPLICATE CHECK
                    if (addr, seq_num) in self.received_history:
                        # print(f"Ignoring duplicate message {seq_num} from {addr}")
                        continue
                    
                    # Mark as seen
                    self.received_history.add((addr, seq_num))

                # Add to queue for main thread to process
                # We attach the address to the message so logic knows who sent it
                message['source_addr'] = addr
                self.incoming_messages.put(message)

                # Pass the message to the Main Game Loop (Legacy callback support)
                if self.message_callback:
                    self.message_callback(message, addr)

            except OSError as e:
                # Windows Error 10054: Remote host closed connection (Port Unreachable)
                # We should IGNORE this and keep listening.
                if e.winerror == 10054:
                    continue 
                else:
                    print(f"Socket error: {e}")
                    break
                    
            except Exception as e:
                print(f"Listener error: {e}")
                break

    def send_ack(self, seq_number, target_addr):
        """Helper to send an ACK for a specific sequence number."""
        ack_data = {
            constants.KEY_ACK_NUM: seq_number
        }
        # We use construct_message manually here to avoid recursive ACKs
        # construct_message now handles skipping SEQ_NUM for ACKs
        packet = self.construct_message(constants.MSG_ACK, ack_data)
        self.sock.sendto(packet, target_addr)

    def start_listening(self, callback_function):
        """
        Main.py calls this to say: "When you get a message, call this function!"
        """
        self.message_callback = callback_function

    def receive_message(self):
        """
        Non-blocking retrieval of the next message from the queue.
        Returns None if queue is empty.
        """
        try:
            return self.incoming_messages.get_nowait()
        except queue.Empty:
            return None

    def send_reliable(self, message_type, data=None):
        """
        Sends a message and tracks it for retransmission until ACKed.
        """
        if data is None:
            data = {}
            
        # Construct packet
        packet = self.construct_message(message_type, data)
        
        # Send immediately
        if self.peer_address:
            self.sock.sendto(packet, self.peer_address)
            print(f"Sent reliable {message_type} to {self.peer_address}")
        else:
            print("Error: No peer address set!")
            return
            
        # Also send to spectators (Best Effort)
        for spec_addr in self.spectators:
            try:
                self.sock.sendto(packet, spec_addr)
            except:
                pass

        # Store for retransmission
        # We need to extract the sequence number we just generated
        # construct_message increments self.sequence_number, so current value is the one used.
        seq_num = str(self.sequence_number)
        
        self.pending_acks[seq_num] = {
            "packet": packet,
            "timestamp": time.time(),
            "retries": 0
        }

    def handle_ack(self, message):
        """
        Called when we receive an ACK message.
        Removes the corresponding message from pending_acks.
        """
        ack_num = message.get(constants.KEY_ACK_NUM)
        if ack_num in self.pending_acks:
            # print(f"ACK received for {ack_num}")
            del self.pending_acks[ack_num]

    def check_resend(self):
        """
        Called periodically to resend lost packets.
        """
        current_time = time.time()
        to_remove = []

        # Create a list of items to iterate over to avoid "dictionary changed size" error
        for seq_num, info in list(self.pending_acks.items()):
            if current_time - info["timestamp"] > constants.TIMEOUT_SECONDS:
                if info["retries"] < constants.MAX_RETRIES:
                    # Resend
                    print(f"Resending packet {seq_num}...")
                    self.sock.sendto(info["packet"], self.peer_address)
                    info["timestamp"] = current_time
                    info["retries"] += 1
                else:
                    print(f"Max retries reached for packet {seq_num}. Giving up.")
                    to_remove.append(seq_num)
                    # Notify connection lost
                    self.incoming_messages.put({
                        constants.KEY_MSG_TYPE: "CONNECTION_LOST",
                        "reason": "Max retries reached"
                    })
        
        for seq_num in to_remove:
            if seq_num in self.pending_acks:
                del self.pending_acks[seq_num]