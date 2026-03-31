import sqlite3
from pathlib import Path

project_root = Path(__file__).resolve().parent
db_path = project_root / "database" / "chat_app.db"
schema_path = project_root / "database" / "schema.sql"

# Deletes the existing chat_app.db file and reinitializes it with the schema.sql file
def reinitialize():
    # 1. Ensure the server is stopped before running this!
    if db_path.exists():
        try:
            db_path.unlink()
            print(f"Deleted: {db_path}")
        except PermissionError:
            print("ERROR: Cannot delete the file. Is the server still running?")
            return
    
    # 2. Create the new file
    conn = sqlite3.connect(db_path)
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    
    # 3. Seed Global Chat
    conn.execute("INSERT INTO chats (chat_id, chat_type, name) VALUES (1, 'group', 'Global')")
    conn.commit()
    conn.close()
    print("Database reinitialized successfully.")

if __name__ == "__main__":
    reinitialize()