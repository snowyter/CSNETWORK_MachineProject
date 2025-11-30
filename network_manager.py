import constants
import socket
import threading

class NetworkManager:
    def __init__(self, port = constants.DEFAULT_PORT):

        # Creating UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Binding the socket to the port
        self.sock.bind(('0.0.0.0', port))

        # Storage reliability
        self.sequence_number = 0  # To track message order 
        self.peer_address = None  # To remember who we are playing against

        self.message_callback = None #store the function we cal when msg arrives

        # Start the listener thread immediately
        # daemon=True means this thread dies automatically when the main program closes
        self.listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.listener_thread.start()

        print(f"NetworkManager: Listening on port {port}")

    def set_peer(self, ip_address):
        self.peer_address = (ip_address, constants.DEFAULT_PORT)

    def construct_message(self, message_type, data=None):
        """
        Takes a message type and a dictionary of data, 
        and turns it into a key:value string.
        """
        if data is None:
            data = {}
            
        # Start with the mandatory message_type 
        msg_str = f"{constants.KEY_MSG_TYPE}: {message_type}\n"
        
        # Add the sequence number (for reliability)
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

                # RELIABILITY: Send ACK immediately if the message has a sequence number
                if constants.KEY_SEQ_NUM in message and message.get(constants.KEY_MSG_TYPE) != constants.MSG_ACK:
                    seq_num = message[constants.KEY_SEQ_NUM]
                    self.send_ack(seq_num, addr)

                # Pass the message to the Main Game Loop
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
        packet = self.construct_message(constants.MSG_ACK, ack_data)
        self.sock.sendto(packet, target_addr)

    def start_listening(self, callback_function):
        """
        Main.py calls this to say: "When you get a message, call this function!"
        """
        self.message_callback = callback_function