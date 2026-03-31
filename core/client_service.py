import sys
import os
import threading
import queue
import time
import json
import builtins
import socket
import types

# Ensure core is in path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

import client.tcp_client as tcp_client

# ==========================================
# 1. Monkey-Patching for Dual-Interface
# ==========================================

# Queues for command input
command_queue = queue.Queue()

# Thread to read from real stdin so terminal overrides still work
def stdin_reader():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            command_queue.put(line.strip('\n'))
        except EOFError:
            break

threading.Thread(target=stdin_reader, daemon=True).start()

original_input = builtins.input
original_print = builtins.print

def custom_input(prompt=""):
    original_print(prompt, end="", flush=True)
    return command_queue.get()

builtins.input = custom_input

# ==========================================
# 2. Intercepting Socket for Command Injection
# ==========================================

original_socket = tcp_client.socket
global_client_socket = None

def custom_socket(family=-1, type_=-1, proto=-1, fileno=None):
    s = original_socket(family, type_, proto, fileno)
    global global_client_socket
    
    # We duck-punch the connect method to grab the socket when it connects to the server
    original_connect = s.connect
    def custom_connect(addr):
        global global_client_socket
        # SERVER_PORT is 12001
        if isinstance(addr, tuple) and len(addr) >= 2 and addr[1] == 12001:
            global_client_socket = s
        return original_connect(addr)
    s.connect = custom_connect
    return s

tcp_client.socket = custom_socket

# ==========================================
# 3. Web & Socket.IO Server Setup
# ==========================================

app = Flask(__name__)
CORS(app)
sio = SocketIO(app, cors_allowed_origins="*")

# ==========================================
# 4. Monkey-Patching Packet Receivers
# ==========================================

original_receive_packet = tcp_client.receive_packet

def custom_receive_packet(sock):
    seq, msg_type, body = original_receive_packet(sock)
    # Emit structured data directly to React
    if msg_type is not None:
        sio.emit('packet_received', {
            'seq': seq,
            'type': msg_type,
            'body': body
        })
    return seq, msg_type, body

tcp_client.receive_packet = custom_receive_packet

# Patch the UDP online sensor to also emit statuses
try:
    original_recvfrom = tcp_client.udp_client.recvfrom
    def custom_recvfrom(self, *args, **kwargs):
        data, addr = original_recvfrom(*args, **kwargs)
        sio.emit('status_update', {'message': data.decode()})
        return data, addr

    # Bind the custom method to the existing udp_client instance
    tcp_client.udp_client.recvfrom = types.MethodType(custom_recvfrom, tcp_client.udp_client)
except Exception as e:
    original_print(f"Failed to patch udp_client: {e}")

# ==========================================
# 5. REST Endpoints for Database Passthrough
# ==========================================
from database.database import get_user_chats, get_recent_messages, get_user_by_username

@app.route('/api/chats/<user_id>', methods=['GET'])
def api_get_chats(user_id):
    try:
        chats = get_user_chats(int(user_id))
        chat_list = []
        for c in chats:
            chat_dict = dict(c)
            recent = get_recent_messages(chat_dict['chat_id'], limit=30)
            
            # Safe member fetch without importing get_chat_members to avoid circular if any
            from database.database import get_chat_members
            members = get_chat_members(chat_dict["chat_id"])
            
            chat_list.append({
                "chat_id": chat_dict["chat_id"],
                "chat_type": chat_dict["chat_type"],
                "name": chat_dict.get("name"),
                "recent_messages": [dict(m) for m in recent],
                "members": [dict(m)["username"] for m in members]
            })
        return jsonify({"status": "SUCCESS", "chats": chat_list})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==========================================
# 6. WebSocket Command Pipe
# ==========================================

@sio.on('command')
def handle_command(data):
    """
    Handle commands originating from the React Frontend.
    Converts JSON to protocol.py format and injects into client_socket OR
    pushes terminal commands via the command_queue.
    """
    action = data.get('action')
    
    if action == "login":
        # Push to the terminal input queue to authenticate!
        command_queue.put("1") # select 1. Login
        command_queue.put(data.get('username'))
        command_queue.put(data.get('password'))
        return
        
    if action == "signup":
        command_queue.put("2") # select 2. Sign-up
        command_queue.put(data.get('username'))
        command_queue.put(data.get('password'))
        return

    # If the socket is connected, forward data commands
    if global_client_socket:
        try:
            if action == "pm":
                target = data.get("target")
                msg = data.get("msg")
                cmd_str = f"/pm <{target}> <{msg}>"
                global_client_socket.sendall(tcp_client.encode_packet(0, "DATA", cmd_str))
                
            elif action == "group":
                target = data.get("target")
                msg = data.get("msg")
                cmd_str = f"/group <{target}> <{msg}>"
                global_client_socket.sendall(tcp_client.encode_packet(0, "DATA", cmd_str))
                
            elif action == "create":
                target = data.get("target")
                cmd_str = f"/create <{target}>"
                global_client_socket.sendall(tcp_client.encode_packet(0, "DATA", cmd_str))
                
            elif action == "join":
                target = data.get("target")
                cmd_str = f"/join <{target}>"
                global_client_socket.sendall(tcp_client.encode_packet(0, "DATA", cmd_str))
                
        except Exception as e:
            original_print(f"Error injecting command: {e}")

# ==========================================
# 7. Start the System
# ==========================================

def run_legacy_client():
    try:
        # Start the legacy tcp_client. It will loop infinitely 
        # but now use our monkey-patched socket, input, and receive_packet
        tcp_client.start_client()
    except Exception as e:
        original_print(f"Legacy client exited: {e}")

if __name__ == "__main__":
    original_print("[Bridge] Starting Legacy Client thread...")
    threading.Thread(target=run_legacy_client, daemon=True).start()
    
    original_print("[Bridge] Starting WebSocket UI Server on port 5001...")
    # Run the socketio app
    sio.run(app, host="0.0.0.0", port=5001, allow_unsafe_werkzeug=True)
