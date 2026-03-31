import hashlib
from .db_connection import get_connection

# --- User Functions ---

# Hashes a plain text password using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Creates a new user in the database
def create_user(username, password_hash):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",  # ← Fixed: removed email
            (username, password_hash)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        # Prints database error for debugging
        print(f"Error creating user: {e}")  # ← Add this for debugging
        return None
    finally:
        conn.close()

# Gets a user row by username
def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

# Verifies login by matching username and password hash
def verify_login(username, password_hash):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
    row = cur.fetchone()
    conn.close()
    return row


# Deletes a user by user_id
def delete_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted > 0


# Handles registration and automatically adds the user to the global chat
def handle_register(username, password):
    """Handle user registration and auto-join global chat (Consolidated from db_handler)"""
    # Check if username exists
    existing_user = get_user_by_username(username)
    if existing_user:
        return {
            "status": "USERNAME_EXISTS",
            "message": "Username already exists. Please choose another."
        }
    
    # Create user
    password_hash = hash_password(password)
    user_id = create_user(username, password_hash)
    
    if user_id:
        # Auto-join global chat
        global_chat_id = get_or_create_global_chat()
        add_user_to_chat(global_chat_id, user_id)
        
        return {
            "status": "SUCCESS",
            "user": {"user_id": user_id, "username": username},
            "message": "Registration successful!"
        }
    else:
        return {
            "status": "FAILURE",
            "message": "Registration failed due to server error."
        }

# Handles login and loads the user's chats and recent messages
def handle_login(username, password):
    """Handle user login and aggregate their chat data (Consolidated from db_handler)"""
    password_hash = hash_password(password)
    user = verify_login(username, password_hash)
    
    if not user:
        return {
            "status": "FAILURE",
            "message": "Invalid username or password."
        }
    
    # Get user's chats for loading initial data
    chats = get_user_chats(dict(user)["user_id"])
    chat_list = []
    
    for chat in chats:
        recent_msgs = get_recent_messages(chat["chat_id"], limit=20)
        members = get_chat_members(chat["chat_id"])
        
        chat_list.append({
            "chat_id": chat["chat_id"],
            "chat_type": chat["chat_type"],
            "recent_messages": [dict(msg) for msg in recent_msgs],
            "members": [dict(m)["username"] for m in members]
        })
    
    return {
        "status": "SUCCESS",
        "user": dict(user),
        "chats": chat_list,
        "message": "Login successful!"
    }

# --- Chat Functions ---

# Creates a new chat and returns its ID
def create_chat(chat_type, name=None):
    """Creates a new chat (private or group) and returns its ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO chats (chat_type, name) VALUES (?, ?)", (chat_type, name))
    chat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return chat_id

# Adds a user to a chat
def add_user_to_chat(chat_id, user_id):
    """Links a user to a specific chat."""
    import sqlite3
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO chat_members (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # User is already a member, which is fine
        return True
    except Exception as e:
        # Prints database error for debugging
        print(f"[DB ERROR] add_user_to_chat error: {e}")
        return False
    finally:
        conn.close()

# Gets all chats that a user belongs to
def get_user_chats(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.* FROM chats c
        JOIN chat_members cm ON c.chat_id = cm.chat_id
        WHERE cm.user_id = ?
        ORDER BY c.chat_id ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# Gets usernames of all members in a chat
def get_chat_members(chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.username FROM users u
        JOIN chat_members cm ON u.user_id = cm.user_id
        WHERE cm.chat_id = ?
    """, (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# Gets one chat by its ID
def get_chat_by_id(chat_id):
    """Fetches details of a specific chat."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row

# Gets a group chat by its name
def get_chat_by_name(name):
    """Fetches details of a specific chat by its name."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chats WHERE name = ? AND chat_type = 'group'", (name,))
    row = cur.fetchone()
    conn.close()
    return row

# Gets the global chat if it exists, otherwise creates it
def get_or_create_global_chat():
    """Simple helper for the global channel (Assuming ID 1 is Global)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM chats WHERE chat_id = 1")
    row = cur.fetchone()
    if not row:
        # Initial creation of global chat if DB is empty
        cur.execute("INSERT INTO chats (chat_id, chat_type, name) VALUES (1, 'group', 'Global')")
        conn.commit()
    conn.close()
    return 1

# --- Message Functions ---

# Saves a message into the messages table
def save_message(chat_id, sender_id, content, sequence_number, message_type="text"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (chat_id, sender_id, message_type, content, sequence_number)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, sender_id, message_type, content, sequence_number))
    conn.commit()
    conn.close()
    return sequence_number

# Gets the highest sequence number currently in a chat
def get_last_sequence(chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(sequence_number), 0) FROM messages WHERE chat_id = ?", (chat_id,))
    result = cur.fetchone()[0]
    conn.close()
    return result

# Gets all messages from a chat in order
def get_messages(chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY sequence_number ASC", (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# Gets the most recent messages from a chat
def get_recent_messages(chat_id, limit=20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM messages WHERE chat_id = ?
        ORDER BY sequence_number DESC LIMIT ?
    """, (chat_id, limit))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))

# Adds a message to the queue manager for proper sequencing
def append_message(chat_id, sender, message):
    user = get_user_by_username(sender)
    if user is None:
        return False
    sender_id = user["user_id"]
    if str(chat_id).lower() == "global":
        actual_chat_id = get_or_create_global_chat()
    else:
        actual_chat_id = int(chat_id)
    
    # Local import to avoid circular dependency
    from .message_queue import manager as queue_manager
    seq = queue_manager.queue_message(actual_chat_id, sender_id, message)
    return seq

# Gets an existing private chat between two users or creates a new one
def get_or_create_private_chat(username1, username2):
    """Finds an existing DM between two users or creates one."""
    user1 = get_user_by_username(username1)
    user2 = get_user_by_username(username2)
    if not user1 or not user2: return None

    conn = get_connection()
    cur = conn.cursor()
    # Check for existing private chat between these two
    cur.execute("""
        SELECT cm1.chat_id FROM chat_members cm1
        JOIN chat_members cm2 ON cm1.chat_id = cm2.chat_id
        JOIN chats c ON cm1.chat_id = c.chat_id
        WHERE c.chat_type = 'private' AND cm1.user_id = ? AND cm2.user_id = ?
    """, (user1['user_id'], user2['user_id']))
    
    row = cur.fetchone()
    conn.close()

    if row:
        return row['chat_id']
    else:
        # Create new private chat
        # Set name to target user's username as per request
        new_id = create_chat('private', name=username2)
        add_user_to_chat(new_id, user1['user_id'])
        add_user_to_chat(new_id, user2['user_id'])
        return new_id

# Gets all group chats
def get_all_groups():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id, name FROM chats WHERE chat_type = 'group'")
    rows = cur.fetchall()
    conn.close()
    return rows

# Updates the saved port number for a user
def update_user_port(username, port):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET port_number = ? WHERE username = ?",
        (port, username)
    )
    conn.commit()
    conn.close()

# Gets the saved port number for a user
def get_user_port(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT port_number FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row["port_number"] if row else None