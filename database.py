import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

if os.environ.get("VERCEL"):
    SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/chat.db"
else:
    os.makedirs("data", exist_ok=True)
    SQLALCHEMY_DATABASE_URL = "sqlite:///./data/chat.db"

# connect_args={"check_same_thread": False} is needed only for SQLite. 
# It's not needed for other databases.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()