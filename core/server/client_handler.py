from protocol import receive_packet, encode_packet
from database.database import (
    append_message, 
    get_or_create_private_chat, get_chat_members, 
    get_chat_by_id, get_or_create_global_chat,
    get_user_by_username, add_user_to_chat, create_chat,
    get_chat_by_name, handle_login, handle_register
)

import json

# Sends a packet to all members of a chat
# If include_sender is True, the sender will also receive the packet
def send_to_members(packet, member_usernames, sender_socket, authenticated_clients, include_sender=False):
    delivered_count = 0
    for client_socket, username in list(authenticated_clients.items()):
        if username in member_usernames:
            if not include_sender and client_socket == sender_socket:
                continue
            try:
                client_socket.sendall(packet)
                delivered_count += 1
            except:
                print(f"[INFO] Removing ghost client: {username}")
                if client_socket in authenticated_clients:
                    del authenticated_clients[client_socket]
                try:
                    client_socket.close()
                except:
                    pass
    return delivered_count

# Handles a client connection and manages the lifecycle of the client
def handle_client(connection_socket, addr, authenticated_clients):
    current_user = None
    print(f"[INFO] New client handler started for {addr}")
    
    try:
        while True:
            sequence_number, message_type, body = receive_packet(connection_socket)
            if sequence_number is None: 
                print(f"[INFO] Client {addr} disconnected.")
                break

            try:
                target_members = []
                display_msg = ""
                response_body = ""
                include_sender_in_broadcast = False
                
                # 1. Authentication & Registration
                if body.startswith("Authenticate/"):
                    parts = body.split("/")
                    if len(parts) == 3:
                        _, username, password = parts
                        result = handle_login(username, password)
                        if result["status"] == "SUCCESS":
                            db_user = result.get("user")
                            current_user = db_user["username"] if db_user else username
                            authenticated_clients[connection_socket] = current_user
                            print(f"[AUTH] User {current_user} authenticated.")
                            
                            user_info = get_user_by_username(current_user)
                            if user_info:
                                add_user_to_chat(1, dict(user_info)["user_id"])
                            
                            response_body = "SUCCESS|" + json.dumps(result)
                        else:
                            response_body = f"FAILURE|{result['message']}"
                    else:
                        response_body = "FAILURE|Invalid format"

                elif body.startswith("NewUser/"):
                    parts = body.split("/")
                    if len(parts) == 3:
                        _, username, password = parts
                        result = handle_register(username, password)
                        if result["status"] == "SUCCESS":
                            db_user = result.get("user")
                            current_user = db_user["username"] if db_user else username
                            authenticated_clients[connection_socket] = current_user
                            print(f"[AUTH] User {current_user} registered.")
                            response_body = "SUCCESS|" + json.dumps(result)
                        else:
                            response_body = f"FAILURE|{result['message']}"
                    else:
                        response_body = "FAILURE|Invalid format"

                # 2. Command Parsing
                elif current_user:
                    if body.startswith("/"):
                        parts = body.split(" ", 2)
                        cmd = parts[0].lower()
                        print(f"[CMD] {current_user} sent command: {cmd}")

                        if cmd == "/pm" and len(parts) >= 2:
                            cmd_line = body[len(cmd):].strip()
                            if cmd_line.startswith("<"):
                                target_user_raw = cmd_line[1:cmd_line.find(">")].strip()
                                content = cmd_line[cmd_line.find(">")+1:].strip()
                            else:
                                pm_parts = cmd_line.split(" ", 1)
                                target_user_raw = pm_parts[0]
                                content = pm_parts[1] if len(pm_parts) > 1 else ""
                            
                            # Normalize username to database casing
                            target_user = target_user_raw
                            db_user = get_user_by_username(target_user_raw)
                            if db_user:
                                target_user = dict(db_user)["username"]

                            chat_id = get_or_create_private_chat(current_user, target_user)
                            if chat_id:
                                # Capture the real sequence number from the DB queue
                                msg_seq = append_message(chat_id, current_user, content)
                                target_members = [target_user]
                                display_msg = f"[RECEIVED] PM from {current_user}: {content}"
                                response_body = f"[PM to {target_user}]: {content}"
                                include_sender_in_broadcast = False
                                sequence_number = msg_seq 
                            else:
                                response_body = f"User {target_user_raw} not found."

                        elif cmd == "/group" and len(parts) >= 2:
                            cmd_line = body[len(cmd):].strip()
                            if cmd_line.startswith("<"):
                                group_target_raw = cmd_line[1:cmd_line.find(">")].strip()
                                content = cmd_line[cmd_line.find(">")+1:].strip()
                            else:
                                group_parts = cmd_line.split(" ", 1)
                                group_target_raw = group_parts[0]
                                content = group_parts[1] if len(group_parts) > 1 else ""
                            
                            chat = None
                            group_target = group_target_raw
                            try:
                                gid = int(group_target_raw)
                                chat = get_chat_by_id(gid)
                            except ValueError:
                                chat = get_chat_by_name(group_target_raw)
                                if chat:
                                    group_target = dict(chat)["name"]

                            if chat:
                                chat_dict = dict(chat)
                                if chat_dict["chat_type"] == "group":
                                    gid = chat_dict["chat_id"]
                                    members = [m["username"] for m in get_chat_members(gid)]
                                    if current_user in members:
                                        msg_seq = append_message(gid, current_user, content)
                                        target_members = members
                                        name_str = chat_dict['name'] or f"ID {gid}"
                                        display_msg = f"[RECEIVED] Group {name_str} from {current_user}: {content}"
                                        response_body = "" # Broadcast is confirmation
                                        include_sender_in_broadcast = True
                                        sequence_number = msg_seq
                                    else:
                                        response_body = "You are not a member of this group."
                                else:
                                    response_body = "Target chat is not a group."
                            else:
                                response_body = f"Group '{group_target}' does not exist."

                        elif cmd == "/create" and len(parts) >= 2:
                            group_name = body[len(cmd):].strip().strip("<> ")
                            chat_id = create_chat("group", name=group_name)
                            user = get_user_by_username(current_user)
                            if user:
                                add_user_to_chat(chat_id, dict(user)["user_id"])
                                response_body = f"CONFIRM: Group '{group_name}' created successfully!"
                            else:
                                response_body = "ERROR: User identity missing."

                        elif cmd == "/join" and len(parts) >= 2:
                            group_target = body[len(cmd):].strip().strip("<> ")
                            chat = None
                            try:
                                gid = int(group_target)
                                chat = get_chat_by_id(gid)
                            except ValueError:
                                chat = get_chat_by_name(group_target)
                            
                            if chat:
                                chat_dict = dict(chat)
                                user = get_user_by_username(current_user)
                                if user:
                                    user_dict = dict(user)
                                    success = add_user_to_chat(chat_dict["chat_id"], user_dict["user_id"])
                                    if success:
                                        name_display = chat_dict['name'] if chat_dict['name'] else f"ID {chat_dict['chat_id']}"
                                        response_body = f"CONFIRM: Joined group '{name_display}'."
                                    else:
                                        response_body = f"ERROR: Could not join group '{group_target}'."
                                else:
                                    response_body = "ERROR: User identity missing."
                            else:
                                response_body = f"Group '{group_target}' not found."

                        elif cmd == "/members" and len(parts) >= 2:
                            group_target = body[len(cmd):].strip().strip("<> ")
                            chat = None
                            try:
                                gid = int(group_target)
                                chat = get_chat_by_id(gid)
                            except ValueError:
                                chat = get_chat_by_name(group_target)
                            
                            if chat:
                                chat_id = dict(chat)["chat_id"]
                                members = [m["username"] for m in get_chat_members(chat_id)]
                                response_body = f"CONFIRM: Members of {group_target}: " + ", ".join(members)
                            else:
                                response_body = f"Group '{group_target}' not found."

                        elif cmd == "/broadcast":
                            content = body[len(cmd):].strip().strip("<> ")
                            target_members = list(authenticated_clients.values())
                            display_msg = f"[BROADCAST from {current_user}]: {content}"
                            response_body = "" 
                            include_sender_in_broadcast = True

                        else:
                            response_body = f"Unknown command: {cmd}"

                    else:
                        # Global Chat
                        global_id = get_or_create_global_chat()
                        msg_seq = append_message(global_id, current_user, body)
                        target_members = list(authenticated_clients.values())
                        display_msg = f"[RECEIVED] Global from {current_user}: {body}"
                        response_body = "" 
                        include_sender_in_broadcast = True
                        sequence_number = msg_seq

                else:
                    response_body = "Please login first."

                # Transmission
                if display_msg and target_members:
                    packet = encode_packet(sequence_number or 0, "DATA", display_msg)
                    count = send_to_members(packet, target_members, connection_socket, authenticated_clients, include_sender=include_sender_in_broadcast)
                    print(f"[BROADCAST] Target: {target_members}, Delivered to: {count} users.")
                
                if response_body:
                    connection_socket.sendall(encode_packet(sequence_number or 0, "ACK", response_body))

            except Exception as e:
                print(f"[ERROR] Error handling message from {addr}: {e}")
                err_msg = f"ERROR: Internal server error ({type(e).__name__})"
                try:
                    connection_socket.sendall(encode_packet(sequence_number, "ACK", err_msg))
                except:
                    pass

    finally:
        if connection_socket in authenticated_clients:
            del authenticated_clients[connection_socket]
        connection_socket.close()