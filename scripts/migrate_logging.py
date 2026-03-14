import sqlite3
import os

DB_PATH = "packages.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. No migration needed (will be created by init_db).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Checking for package_logs table...")
    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='package_logs'")
    if cursor.fetchone()[0] == 0:
        print("Creating package_logs table...")
        cursor.execute("""
            CREATE TABLE package_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id VARCHAR(36) NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level VARCHAR NOT NULL,
                stage VARCHAR NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY(package_id) REFERENCES packages(id)
            )
        """)
        conn.commit()
        print("Table package_logs created successfully.")
    else:
        print("Table package_logs already exists.")

    conn.close()

if __name__ == "__main__":
    migrate()
