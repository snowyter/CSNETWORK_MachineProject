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