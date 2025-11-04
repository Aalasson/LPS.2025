
import os
from sqlmodel import SQLModel, create_engine, Session
SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/orders.db")
engine = create_engine(f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
