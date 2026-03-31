-- Turn on foreign key support in SQLite
PRAGMA foreign_keys = ON;

-- Table for storing user accounts
CREATE TABLE IF NOT EXISTS users (
    -- Unique ID for each user
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Username must be unique and cannot be empty
    username TEXT NOT NULL UNIQUE,

    -- Stores the hashed password
    password_hash TEXT NOT NULL,

    -- Date and time the user was created
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Port number linked to the user
    port_number INTEGER
);

-- Table for storing chats
CREATE TABLE IF NOT EXISTS chats (
    -- Unique ID for each chat
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Chat name, mainly useful for group chats
    name TEXT,

    -- Chat type can only be private or group
    chat_type TEXT NOT NULL CHECK(chat_type IN ('private', 'group')),

    -- Date and time the chat was created
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table linking users to chats they belong to
CREATE TABLE IF NOT EXISTS chat_members (
    -- Chat ID the user belongs to
    chat_id INTEGER NOT NULL,

    -- User ID of the member
    user_id INTEGER NOT NULL,

    -- Date and time the user joined the chat
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Prevents duplicate membership entries
    PRIMARY KEY (chat_id, user_id),

    -- Deletes membership if the chat is deleted
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,

    -- Deletes membership if the user is deleted
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Table for storing messages sent in chats
CREATE TABLE IF NOT EXISTS messages (
    -- Unique ID for each message
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Chat where the message was sent
    chat_id INTEGER NOT NULL,

    -- User who sent the message
    sender_id INTEGER NOT NULL,

    -- Type of message, default is text
    message_type TEXT NOT NULL DEFAULT 'text',

    -- Actual message content
    content TEXT NOT NULL,

    -- Date and time the message was sent
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Sequence number to keep message order inside a chat
    sequence_number INTEGER NOT NULL,

    -- Deletes messages if the chat is deleted
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,

    -- Deletes messages if the sender is deleted
    FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE,

    -- Ensures sequence numbers are unique within each chat
    UNIQUE(chat_id, sequence_number)
);

-- Index to speed up message lookups by chat and sequence number
CREATE INDEX IF NOT EXISTS idx_messages_chat_seq
ON messages(chat_id, sequence_number);

-- Index to speed up finding chats for a specific user
CREATE INDEX IF NOT EXISTS idx_chat_members_user
ON chat_members(user_id);