import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from socket import *
import threading
from protocol import receive_packet, encode_packet
from client_handler import handle_client

SERVER_PORT = 12001
SERVER_HOST = ''

# Shared list for broadcasting
authenticated_clients = {}

# Starts up the TCP server
def start_server():
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)

    print(f"TCP Server is ready to receive connections on port {SERVER_PORT}...")

    # Start UDP handler in a separate thread
    threading.Thread(target=udp_server_handler, daemon=True).start()

    while True:
        connection_socket, addr = server_socket.accept()
        print(f"New connection from {addr}")

        threading.Thread(
            target=handle_client,
            args=(connection_socket, addr, authenticated_clients)
        ).start()

# Runs the UDP server
def udp_server_handler():
    udp_port = 13000
    udp_server = socket(AF_INET, SOCK_DGRAM)
    udp_server.bind(('', udp_port))
    udp_clients = []
    print(f"UDP Status Server ready on port {udp_port}...")
    while True:
        try:
            message, addr = udp_server.recvfrom(1024)
            if addr not in udp_clients:
                udp_clients.append(addr)
            for client in udp_clients:
                if client != addr:
                    udp_server.sendto(message, client)
        except Exception as e:
            print(f"UDP server error: {e}")
            break


    print(f"Connection closed: {addr}")
    connection_socket.close()

if __name__ == "__main__":
    start_server()