from src.db.session import db_session
from sqlalchemy import text

def run_migration():
    print("Running migration to add 'is_reviewed' to 'extractions' table...")
    try:
        # Check if column exists first to be idempotent
        with db_session.get_bind().connect() as connection:
            result = connection.execute(text("PRAGMA table_info(extractions)"))
            columns = [row[1] for row in result]
            
            if 'is_reviewed' not in columns:
                connection.execute(text("ALTER TABLE extractions ADD COLUMN is_reviewed BOOLEAN DEFAULT 0"))
                print("Added 'is_reviewed' column.")
            else:
                print("'is_reviewed' column already exists.")
            
            connection.commit()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
