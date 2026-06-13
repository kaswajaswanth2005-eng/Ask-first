"""
database.py
-----------
SQLAlchemy setup, declarative models, and session management for the AI Chat App.

Tables:
  - Thread   : Represents a chat conversation thread.
  - Message  : Stores individual messages belonging to a thread.
  - Memory   : Stores universal facts extracted from user messages.

Database:
  - Local development : SQLite  (automatic, no setup needed)
  - Production        : Any SQLAlchemy-supported DB (PostgreSQL, MySQL, etc.)
                        Set DATABASE_URL in your .env file.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from datetime import datetime, timezone
from typing import Generator

load_dotenv()  # Load variables from .env file

# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------

# Reads DATABASE_URL from .env.
# - Local default  : SQLite  (chat_app.db in project folder)
# - Production     : Set DATABASE_URL=postgresql://user:pass@host:5432/dbname
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chat_app.db")

# SQLite needs check_same_thread=False; other DBs don't need it but it's harmless.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,  # Set True to log every SQL query (useful for debugging)
    pool_pre_ping=True,  # Verify connections before using them (important for PostgreSQL)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Thread(Base):
    """A named chat conversation thread."""
    __tablename__ = "threads"

    id: int = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title: str = Column(String(255), nullable=False, default="New Thread")
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # One thread → many messages
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Thread id={self.id} title='{self.title}'>"


class Message(Base):
    """A single chat message (user or assistant) within a thread."""
    __tablename__ = "messages"

    id: int = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thread_id: int = Column(Integer, ForeignKey("threads.id"), nullable=False, index=True)
    role: str = Column(String(20), nullable=False)     # "user" | "assistant" | "system"
    content: str = Column(Text, nullable=False)
    timestamp: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    thread = relationship("Thread", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role='{self.role}' thread={self.thread_id}>"


class Memory(Base):
    """A universal fact about the user, extracted from any thread."""
    __tablename__ = "memories"

    id: int = Column(Integer, primary_key=True, index=True, autoincrement=True)
    memory_text: str = Column(Text, nullable=False, unique=True)   # Unique prevents duplicates
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Memory id={self.id} text='{self.memory_text[:40]}'>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a SQLAlchemy session.
    Ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
