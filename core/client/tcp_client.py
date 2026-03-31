import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from socket import *
import threading
import json
from protocol import receive_packet, encode_packet
from database.database import get_user_by_username, get_chat_members, update_user_port, get_user_port

SERVER_HOST = "localhost"
SERVER_PORT = 12001

current_user = None
file_server_socket = None #file server used for P2P file sharing
file_server_running = False
file_server_port = None
UDP_PORT = 13000 # UDP used for broadcasting online and offline status
udp_client = socket(AF_INET, SOCK_DGRAM)
udp_client.bind(("localhost", 0)) #0 allows for random port to be assigned

def authenticate(username, password, client_socket): #sends user credentials to server for authentication
    message_string = "Authenticate/" + username + "/" + password
    client_socket.sendall(encode_packet(0, "AUTH", message_string))

def display_history(data_json): #This method formats the users recents chats that are retrieved from the database by the server and is displayed when the user logs in
    try:
        data = json.loads(data_json)
        print("\n" + "="*40)
        print("       RECENT CHAT HISTORY")
        print("="*40)
        
        chats = data.get("chats", [])
        if not chats:
            print("  No recent activity.")
        
        for chat in chats:
            chat_name = f"Group {chat['chat_id']}"
            if chat['chat_type'] == 'private':
                members = chat.get('members', [])
                other_user = next((m for m in members if m != data['user']['username']), "Unknown")
                chat_name = f"PM with {other_user}"
            elif chat['chat_id'] == 1:
                chat_name = "Global Chat"
            
            print(f"\n>>> {chat_name} <<<")
            msgs = chat.get("recent_messages", [])
            if not msgs:
                print("  (Empty)")
            for msg in msgs:
                # database saves messages with sender_id. 
                # Since we don't have a full user mapping here, we show what we have.
                # In the future, we could include sender_name in the message object.
                print(f"  - {msg['content']}")
        print("\n" + "="*40 + "\n")
    except Exception as e:
        print(f"Error displaying history: {e}")

# Checks to see if the user is authenticated
def login(client_socket):
    username = input("Enter username: ")
    password = input("Enter password:  ")
    authenticate(username, password, client_socket)
    
    _, _, response = receive_packet(client_socket)
    if response and response.startswith("SUCCESS"):
        global current_user
        if "|" in response:
            header, data_json = response.split("|", 1)
            display_history(data_json)
            # The data_json contains user info
            user_data = json.loads(data_json).get("user")
            if user_data:
                current_user = user_data["username"]
        
        start_p2p_listener() #start the file sharing server to receive incoming files from other clients
        send_online(current_user) #share UDP update that the user is now online
        return True
    else:
        msg = response.split("|")[1] if response and "|" in response else (response or "Connection lost")
        print(f"Login failed! (Server said: {msg})")
        return False

# Captures the new user's details and sends it to the server for a SUCCESS-ful account creation
def sign_up(client_socket):
    username = input("Enter a new username: ")
    password = input("Enter a new password: ")
    message_string = "NewUser" + "/" + username + "/" + password
    client_socket.sendall(encode_packet(0, "AUTH", message_string)) #send user credentials to server to check if the username is available etc
    
    _, _, response = receive_packet(client_socket)
    if response and response.startswith("SUCCESS"):
        global current_user
        print("Sign-up successful!")
        if "|" in response:
            _, data_json = response.split("|", 1)
            display_history(data_json)
            user_data = json.loads(data_json).get("user")
            if user_data:
                current_user = user_data["username"]

        start_p2p_listener() #start file sharing server
        send_online(current_user) #send online update
        return True
    else:
        msg = response.split("|")[1] if response and "|" in response else (response or "Connection lost")
        print(f"Sign-up failed: {msg}")
        return False

#Prompts the user to login or sign-up, with options of logging in for existing users or a sign-up for new users
def show_menu():
    print("\n-- Welcome to WhatsUp --")
    print("1. Login")
    print("2. Sign-up")
    print("q. Quit")
    reply = input("Select an option by number or q to quit: ")
    return reply

# Gives user the outline for the expected format of a valid input string depending on what type of operation they want to execute
def show_commands():
    print("\n-- Command Pallete --")
    print("Follow the syntax for each command to execute automatically:")
    print("1. Private Message (Syntax: /pm <user> <message>)")
    print("2. Message Group (Syntax: /group <group_id> <message>)")
    print("3. Send File (Syntax: /file <user> <filename> OR /file <group_name> <filename> )")
    print("4. Create New Group (Syntax: /create <group_name>)")
    print("5. Join Group (Syntax: /join <group_id>)")
    print("Type 'logout' to return to menu.")
    print("Type 'quit' to exit.")

def start_p2p_listener():
    global file_server_running
    if not file_server_running:
        file_server_running = True
        threading.Thread(target=p2p_client, daemon=True).start() #start thread to receive file sharing from other clients

def stop_p2p_listener():
    global file_server_socket, file_server_running, file_server_port, current_user
    if current_user is not None:
        update_user_port(current_user, None) #set the user port to none so that when the user logs in again a new port can be assigned
    if file_server_socket is not None:
        try:
            file_server_socket.close()
        except:
            pass
    file_server_socket = None
    file_server_running = False
    file_server_port = None

def p2p_client():
    global file_server_socket, file_server_port, current_user, file_server_running
    try:
        file_server_socket = socket(AF_INET, SOCK_STREAM) 
        file_server_socket.bind(("localhost", 0))   
        file_server_socket.listen() #start the file server to listen for incoming connections
        file_server_port = file_server_socket.getsockname()[1]
        update_user_port(current_user, file_server_port) #set the port number in the database to the assigned one
        print("File server running on port:", file_server_port)
        while True:
            try:
                conn, addr = file_server_socket.accept()
                threading.Thread(target=handle_incoming_file, args=(conn,), daemon=True).start() #start thread 
            except OSError:
                break
    except Exception as e:
        file_server_running = False
        print("Error starting P2P file server:", e)

def handle_incoming_file(conn):
    try:
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(1024) #receive data from file server connection
            if not chunk:
                return
            data += chunk
        header_bytes, remaining_data = data.split(b"\n", 1)
        header = header_bytes.decode()
        if not header.startswith("FILE|"):
            return
        _, filename, filesize = header.split("|", 2) 
        filesize = int(filesize) #obtain the filesize to use a while loop to write the file until the full file has been written
        os.makedirs("received_files", exist_ok=True) #make a directory to receive file transfers
        save_path = os.path.join("received_files", f"received_{filename}")
        with open(save_path, "wb") as f:
            if remaining_data:
                f.write(remaining_data) #write the file in packets
            remaining = filesize - len(remaining_data) #calculate how much of the file is left
            while remaining > 0:
                chunk = conn.recv(min(4096, remaining)) 
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        print(f"\nReceived file: {filename}, saved as {save_path}")
    except Exception as e:
        print("Error receiving file:", e)
    finally:
        conn.close()

def fileshare(message): #method to determine analyse file share command and differentiate between sending to group or individual
    parts = message.split(" ")
    if len(parts) < 3:
        print("Incorrect syntax used for file sharing, please specify all required arguments.")
        return
    # Support both bracketed and unbracketed targets/filenames
    target = parts[1].strip("<>")
    filename = parts[2].strip("<>")
    
    if not os.path.exists(filename):
        print(f"File '{filename}' does not exist!")
        return

    # If target is a username
    if get_user_by_username(target) is not None:
        send_file_to_user(target, filename)
        return

    # Otherwise try target as a numeric group id
    try:
        group_id = int(target)
        if get_chat_members(group_id):
            send_file_to_group(group_id, filename)
        else:
            print("Receiver provided is not valid.")
    except ValueError:
        print("Receiver provided is not valid.")

def send_file_to_user(username, filename):
    file_socket = None
    try:
        file_socket = socket(AF_INET, SOCK_STREAM) #create socket
        port = get_user_port(username) #get the port number of target from database
        if not port:
            print(f"User {username} is not online.")
            return
        file_socket.connect(("localhost", int(port))) #connect to the other users port
        filesize = os.path.getsize(filename)
        safe_filename = os.path.basename(filename)
        header = f"FILE|{safe_filename}|{filesize}\n"
        file_socket.sendall(header.encode()) #send header to other user
        with open(filename, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                file_socket.sendall(chunk) #send the file in packets
        print("File sent successfully.")
    except Exception as e:
        print("Error sending file:", e)
    finally:
        if file_socket is not None:
            file_socket.close()

def send_file_to_group(group_id, filename):
    members = get_chat_members(group_id) #get members of the groupchat
    if not members:
        print("Group not found or has no members.")
        return
    for member in members:
        username = member["username"]
        if username != current_user:
            send_file_to_user(username, filename) #send the file to everyone in the groupchat

def online_sensor():
    while True:
        try:
            message, _ = udp_client.recvfrom(1024) #method receives UDP updates from the UDP server when a new user is online
            print("\n[STATUS]", message.decode())
        except:
            break

def send_online(username):
    udp_client.sendto(f"{username} is online".encode(), ("localhost", 13000))  #send a UDP message to the server to broadcast that the user is online

def send_offline(username):
    udp_client.sendto(f"{username} is offline".encode(), ("localhost", 13000)) 

# Continuously listens for messages from the server and prints them to the terminal
def receive_messages(client_socket, stop_event):
    while not stop_event.is_set():
        try:
            client_socket.settimeout(1.0) 
            _, _, message = receive_packet(client_socket)
            if message is None:
                # receive_packet returns None when connection is closed
                break
            if not message:
                continue
            
            # Only print newlines if it doesn't look like a direct confirmation
            prefix = "\n" if not (message.startswith("CONFIRM:") or message.startswith("[PM to")) else ""
            print(f"{prefix}{message}")
        except timeout:
            continue
        except Exception as e:
            print(f"\nDisconnected from server: {e}")
            break

# Starts the client and handles the orchestration of our frontend, equivalent to a main class
def start_client():
    client_socket = socket(AF_INET, SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT)) #establish connection with server
        print(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")
    except Exception as e:
        print(f"Could not connect to server: {e}")
        return

    stop_listener = threading.Event()

    while True: 
        authenticated = False
        
        while not authenticated: # Looping on the login menu until a user is successully authenticated
            choice = show_menu()
            if choice == "1":
                authenticated = login(client_socket)
            elif choice == "2":
                authenticated = sign_up(client_socket)
            elif choice.lower() == "q":
                client_socket.close()
                return
            else:
                print("Invalid Input!")

        stop_listener.clear()
        listener_thread = threading.Thread(target=receive_messages, args=(client_socket, stop_listener))
        listener_thread.daemon = True # Ensure thread closes when main program exits
        listener_thread.start()

        # Start UDP sensor to hear about others going online
        threading.Thread(target=online_sensor, daemon=True).start()

        print("\nAuthenticated successfully!")
        show_commands()

        while True: #this code checks if the users command can be handled client side if not it is sent to the server
            message = input("> ")
            if message.lower() == "quit":
                stop_p2p_listener()
                client_socket.close()
                return
            
            if message.lower() == "logout":
                print("Logging out...")
                stop_p2p_listener()
                send_offline(current_user)
                stop_listener.set() # Stop the background thread
                listener_thread.join() # Wait for it to exit
                client_socket.settimeout(None)
                break # Return to login menu
            
            if message.startswith("/file"):
                fileshare(message)
                continue

            if message.startswith("/"):
                # Pass message as is to let server handle bracket parsing
                pass
            
            client_socket.sendall(encode_packet(0, "DATA", message))

if __name__ == "__main__":
    start_client()
