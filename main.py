"""
main.py
-------
FastAPI backend for the AI Chat Application.
LLM: Groq API (llama-3.3-70b-versatile) — fast, free tier available
DB:  SQLAlchemy — works with SQLite locally, PostgreSQL (Supabase) in production

Endpoints:
  POST   /threads                  - Create a new chat thread
  GET    /threads                  - List all threads (newest first)
  PATCH  /threads/{thread_id}      - Rename a thread
  DELETE /threads/{thread_id}      - Delete thread + all its messages
  GET    /messages/{thread_id}     - Get all messages for a thread
  DELETE /messages/{message_id}    - Delete a single message
  POST   /chat                     - Send a message, get AI response
  GET    /memories                 - List all stored memories
  DELETE /memories/{memory_id}     - Delete a specific memory
  DELETE /memories                 - Clear all memories
  GET    /health                   - Health check

Memory extraction runs automatically on every user message.
All memories are injected into the system prompt before each LLM call.
"""

import os
import re
from typing import List, Optional

import groq
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import create_tables, get_db, Thread, Message, Memory

# ---------------------------------------------------------------------------
# Environment & Groq client
# ---------------------------------------------------------------------------

load_dotenv()  # Load GROQ_API_KEY from .env

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Please add it to your .env file."
    )

client = groq.Groq(api_key=GROQ_API_KEY)
# Fast, capable, free-tier Groq model
MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Chat Application",
    description="Multi-thread chat with universal memory, powered by OpenAI GPT-4o mini.",
    version="2.0.0",
)

# Allow Streamlit (running on a different port) to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# Create DB tables on startup (safe: skips if tables already exist)
create_tables()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ThreadCreate(BaseModel):
    title: Optional[str] = "New Thread"


class ThreadRename(BaseModel):
    title: str


class ThreadResponse(BaseModel):
    id: int
    title: str
    created_at: str
    message_count: int = 0

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    timestamp: str

    class Config:
        from_attributes = True


class MemoryResponse(BaseModel):
    id: int
    memory_text: str
    created_at: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    thread_id: int
    message: str


class ChatResponse(BaseModel):
    assistant_message: str
    thread_id: int
    memories_used: List[str]
    new_memories: List[str]


class DeleteResponse(BaseModel):
    success: bool
    detail: str


# ---------------------------------------------------------------------------
# Memory Extraction
# ---------------------------------------------------------------------------

# Ordered from most specific to least specific to avoid over-matching
MEMORY_PATTERNS: List[re.Pattern] = [
    re.compile(r"my name is (.+)",          re.IGNORECASE),
    re.compile(r"my full name is (.+)",     re.IGNORECASE),
    re.compile(r"call me (.+)",             re.IGNORECASE),
    re.compile(r"i live in (.+)",           re.IGNORECASE),
    re.compile(r"i'm from (.+)",            re.IGNORECASE),
    re.compile(r"i am from (.+)",           re.IGNORECASE),
    re.compile(r"i work at (.+)",           re.IGNORECASE),
    re.compile(r"i work for (.+)",          re.IGNORECASE),
    re.compile(r"i work as (.+)",           re.IGNORECASE),
    re.compile(r"i am a (.+)",              re.IGNORECASE),
    re.compile(r"i'm a (.+)",               re.IGNORECASE),
    re.compile(r"i study at (.+)",          re.IGNORECASE),
    re.compile(r"i study (.+)",             re.IGNORECASE),
    re.compile(r"my age is (.+)",           re.IGNORECASE),
    re.compile(r"i am (\d+ years old)",     re.IGNORECASE),
    re.compile(r"my favorite (.+?) is (.+)",re.IGNORECASE),
    re.compile(r"i like (.+)",              re.IGNORECASE),
    re.compile(r"i love (.+)",              re.IGNORECASE),
    re.compile(r"my hobby is (.+)",         re.IGNORECASE),
    re.compile(r"my hobbies are (.+)",      re.IGNORECASE),
    re.compile(r"my email is (.+)",         re.IGNORECASE),
    re.compile(r"my phone is (.+)",         re.IGNORECASE),
]


def extract_memories(text: str) -> List[str]:
    """
    Scan a user message for personal facts using regex patterns.
    Returns a list of clean memory strings (deduped within this call).
    """
    found: List[str] = []
    seen: set = set()

    for pattern in MEMORY_PATTERNS:
        match = pattern.search(text)
        if match:
            raw = match.group(0).strip().rstrip(".!?,;")
            normalized = raw.lower()
            if normalized not in seen:
                seen.add(normalized)
                found.append(raw)

    return found


def save_new_memories(memories: List[str], db: Session) -> List[str]:
    """
    Persist extracted memories, skipping exact duplicates.
    Returns the list of newly saved memories (not already stored).
    """
    newly_saved: List[str] = []

    for mem_text in memories:
        existing = (
            db.query(Memory)
            .filter(Memory.memory_text.ilike(mem_text))
            .first()
        )
        if not existing:
            db.add(Memory(memory_text=mem_text))
            newly_saved.append(mem_text)

    if newly_saved:
        try:
            db.commit()
        except Exception:
            db.rollback()
            newly_saved = []

    return newly_saved


def get_all_memories(db: Session) -> List[str]:
    """Return all stored memory texts ordered by creation time."""
    memories = db.query(Memory).order_by(Memory.created_at).all()
    return [m.memory_text for m in memories]


# ---------------------------------------------------------------------------
# System Prompt Builder
# ---------------------------------------------------------------------------

def build_system_prompt(memories: List[str]) -> str:
    """
    Construct the system prompt injecting all known user facts.
    """
    base = (
        "You are a helpful, friendly, and intelligent AI assistant. "
        "You remember personal facts about the user and use them naturally in conversation. "
        "Always be concise, accurate, and context-aware.\n\n"
    )
    if memories:
        facts = "\n".join(f"- {m}" for m in memories)
        base += f"Known facts about the user:\n{facts}\n\n"
    base += (
        "Use these facts naturally — don't repeat them back robotically unless asked. "
        "If the user asks about something you know, answer confidently."
    )
    return base


# ---------------------------------------------------------------------------
# Thread Endpoints
# ---------------------------------------------------------------------------

@api_router.post("/threads", response_model=ThreadResponse, status_code=201)
def create_thread(payload: ThreadCreate, db: Session = Depends(get_db)):
    """Create a new chat thread with an optional title."""
    thread = Thread(title=payload.title.strip() if payload.title else "New Thread")
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return ThreadResponse(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        message_count=0,
    )


@api_router.get("/threads", response_model=List[ThreadResponse])
def list_threads(db: Session = Depends(get_db)):
    """Return all threads ordered by creation time (newest first), with message counts."""
    threads = db.query(Thread).order_by(Thread.created_at.desc()).all()
    result = []
    for t in threads:
        count = db.query(Message).filter(Message.thread_id == t.id).count()
        result.append(
            ThreadResponse(
                id=t.id,
                title=t.title,
                created_at=t.created_at.isoformat(),
                message_count=count,
            )
        )
    return result


@api_router.patch("/threads/{thread_id}", response_model=ThreadResponse)
def rename_thread(thread_id: int, payload: ThreadRename, db: Session = Depends(get_db)):
    """Rename an existing thread."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found.")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")

    thread.title = payload.title.strip()
    db.commit()
    db.refresh(thread)
    count = db.query(Message).filter(Message.thread_id == thread_id).count()
    return ThreadResponse(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        message_count=count,
    )


@api_router.delete("/threads/{thread_id}", response_model=DeleteResponse)
def delete_thread(thread_id: int, db: Session = Depends(get_db)):
    """Delete a thread and all its messages (cascade)."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found.")
    db.delete(thread)
    db.commit()
    return DeleteResponse(success=True, detail=f"Thread {thread_id} deleted.")


# ---------------------------------------------------------------------------
# Message Endpoints
# ---------------------------------------------------------------------------

@api_router.get("/messages/{thread_id}", response_model=List[MessageResponse])
def get_messages(thread_id: int, db: Session = Depends(get_db)):
    """Return all messages in a given thread, ordered by timestamp."""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found.")

    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.timestamp)
        .all()
    )
    return [
        MessageResponse(
            id=m.id,
            thread_id=m.thread_id,
            role=m.role,
            content=m.content,
            timestamp=m.timestamp.isoformat(),
        )
        for m in messages
    ]


@api_router.delete("/messages/{message_id}", response_model=DeleteResponse)
def delete_message(message_id: int, db: Session = Depends(get_db)):
    """Delete a single message by ID."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found.")
    db.delete(message)
    db.commit()
    return DeleteResponse(success=True, detail=f"Message {message_id} deleted.")


# ---------------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------------

@api_router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Main chat endpoint:
      1. Validate thread exists.
      2. Save user message to DB.
      3. Extract and store any new memories from the message.
      4. Load full thread history for context.
      5. Load all memories and build system prompt.
      6. Call OpenAI GPT-4o-mini.
      7. Save assistant response to DB.
      8. Return assistant response + metadata.
    """
    # --- Validate thread ---
    thread = db.query(Thread).filter(Thread.id == payload.thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {payload.thread_id} not found.")

    user_text = payload.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # --- Step 1: Save user message ---
    user_msg = Message(thread_id=payload.thread_id, role="user", content=user_text)
    db.add(user_msg)
    db.commit()

    # --- Step 2: Extract & store memories ---
    extracted = extract_memories(user_text)
    new_memories = save_new_memories(extracted, db)

    # --- Step 3: Load full thread history ---
    history = (
        db.query(Message)
        .filter(Message.thread_id == payload.thread_id)
        .order_by(Message.timestamp)
        .all()
    )

    # --- Step 4: Load all memories & build system prompt ---
    all_memories = get_all_memories(db)
    system_prompt = build_system_prompt(all_memories)

    # --- Step 5: Build OpenAI messages payload ---
    openai_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        openai_messages.append({"role": msg.role, "content": msg.content})

    # --- Step 6: Call Groq ---
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=openai_messages,
            temperature=0.7,
            max_tokens=1024,
        )
        assistant_text = response.choices[0].message.content.strip()
    except groq.APIConnectionError:
        raise HTTPException(status_code=502, detail="Cannot reach Groq API. Check your internet connection.")
    except groq.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid GROQ_API_KEY. Check your .env file.")
    except groq.RateLimitError:
        raise HTTPException(status_code=429, detail="Groq rate limit exceeded. Please wait and try again.")
    except groq.APIError as e:
        raise HTTPException(status_code=502, detail=f"Groq API error: {str(e)}")

    # --- Step 7: Save assistant message ---
    assistant_msg = Message(
        thread_id=payload.thread_id,
        role="assistant",
        content=assistant_text,
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        assistant_message=assistant_text,
        thread_id=payload.thread_id,
        memories_used=all_memories,
        new_memories=new_memories,
    )


# ---------------------------------------------------------------------------
# Memory Endpoints
# ---------------------------------------------------------------------------

@api_router.get("/memories", response_model=List[MemoryResponse])
def list_memories(db: Session = Depends(get_db)):
    """Return all stored memories with full details (id, text, created_at)."""
    memories = db.query(Memory).order_by(Memory.created_at).all()
    return [
        MemoryResponse(
            id=m.id,
            memory_text=m.memory_text,
            created_at=m.created_at.isoformat(),
        )
        for m in memories
    ]


@api_router.delete("/memories/{memory_id}", response_model=DeleteResponse)
def delete_memory(memory_id: int, db: Session = Depends(get_db)):
    """Delete a specific memory by ID."""
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found.")
    db.delete(memory)
    db.commit()
    return DeleteResponse(success=True, detail=f"Memory {memory_id} deleted.")


@api_router.delete("/memories", response_model=DeleteResponse)
def clear_all_memories(db: Session = Depends(get_db)):
    """Delete ALL stored memories. Use with caution."""
    count = db.query(Memory).count()
    db.query(Memory).delete()
    db.commit()
    return DeleteResponse(success=True, detail=f"Cleared {count} memories.")


# ---------------------------------------------------------------------------
# Utility Endpoints
# ---------------------------------------------------------------------------

@api_router.get("/health")
def health_check():
    """Simple health check — used by Render's uptime monitoring."""
    return {
        "status": "ok",
        "llm_provider": "Groq",
        "model": MODEL,
        "version": "2.0.0",
    }

app.include_router(api_router)

# Serve the frontend locally (Vercel will serve it natively via vercel.json)
if os.path.isdir("public"):
    app.mount("/", StaticFiles(directory="public", html=True), name="public")
