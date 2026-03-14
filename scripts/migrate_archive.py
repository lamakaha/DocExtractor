import sqlite3
import os

DB_PATH = "packages.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(packages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_archived' not in columns:
            print("Adding 'is_archived' column to 'packages' table...")
            cursor.execute("ALTER TABLE packages ADD COLUMN is_archived BOOLEAN DEFAULT 0")
            conn.commit()
            print("Successfully added 'is_archived' column.")
        else:
            print("'is_archived' column already exists in 'packages' table.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()