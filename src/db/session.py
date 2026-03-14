import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from src.models.schema import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///packages.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Enable WAL mode for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

def init_db():
    Base.metadata.create_all(bind=engine)
