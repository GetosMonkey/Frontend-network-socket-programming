import sqlite3
from pathlib import Path

# Path to the SQLite database file
DB_PATH = Path(__file__).resolve().parent / "chat_app.db"


# Creates and returns a database connection
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    # Makes rows behave like dictionaries
    conn.row_factory = sqlite3.Row

    # Turns on foreign key support
    conn.execute("PRAGMA foreign_keys = ON;")

    # Enables Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA journal_mode = WAL;")

    return conn