import sqlite3
import pandas as pd

def check_db():
    conn = sqlite3.connect("packages.db")
    df = pd.read_sql_query("SELECT id, original_filename, status FROM packages", conn)
    print(df)
    conn.close()

if __name__ == "__main__":
    check_db()
