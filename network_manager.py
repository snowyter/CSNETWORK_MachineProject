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