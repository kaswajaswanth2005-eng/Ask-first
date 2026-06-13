import os
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Session
from pydantic import BaseModel
from dotenv import load_dotenv

from database import engine, Base, get_db

load_dotenv()

# ==========================================
# MODELS
# ==========================================
class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    memory = relationship("Memory", back_populates="thread", uselist=False, cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("Thread", back_populates="messages")

class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, unique=True)
    memory_summary = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("Thread", back_populates="memory")

# Create tables
Base.metadata.create_all(bind=engine)

# ==========================================
# SCHEMAS
# ==========================================
class ThreadCreate(BaseModel):
    title: str

class ThreadResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class ThreadWithMessagesResponse(ThreadResponse):
    messages: List[MessageResponse] = []

class ChatRequest(BaseModel):
    thread_id: int
    message: str

class ChatResponse(BaseModel):
    response: str

# ==========================================
# SERVICES
# ==========================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
API_KEY = os.getenv("GROQ_API_KEY", os.getenv("API_KEY"))
MODEL = os.getenv("MODEL", "llama-3.1-8b-instant")

if LLM_PROVIDER == "openai":
    import openai
    openai.api_key = API_KEY
    default_model = "gpt-4o-mini"
elif LLM_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
    default_model = "gemini-1.5-flash"
elif LLM_PROVIDER == "groq":
    from groq import Groq
    groq_client = Groq(api_key=API_KEY)
    default_model = "llama-3.1-8b-instant"

def get_model_name():
    return MODEL if MODEL else default_model

def generate_chat_response(system_prompt: str, history: list, user_message: str) -> str:
    model_name = get_model_name()
    if LLM_PROVIDER == "openai":
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        response = openai.chat.completions.create(model=model_name, messages=messages)
        return response.choices[0].message.content
    elif LLM_PROVIDER == "gemini":
        model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_message)
        return response.text
    elif LLM_PROVIDER == "groq":
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        response = groq_client.chat.completions.create(model=model_name, messages=messages)
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

def generate_memory_summary(history: list) -> str:
    conversation_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
    
    prompt = (
        "Extract long-term user information from this conversation.\n"
        "Keep under 100 words.\n"
        "Include:\n- skills\n- interests\n- preferences\n- goals\n- personal context\n\n"
        "Ignore temporary details. Return concise bullet points only.\n\n"
        f"Conversation:\n{conversation_text}"
    )
    
    model_name = get_model_name()
    
    try:
        if LLM_PROVIDER == "openai":
            response = openai.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        elif LLM_PROVIDER == "gemini":
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        elif LLM_PROVIDER == "groq":
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")
    except Exception as e:
        print(f"Failed to generate memory summary: {e}")
        return ""

def generate_thread_title(first_message: str) -> str:
    prompt = (
        "Generate a very short, concise title (max 4 words) for a chat based on this first message. "
        "Do not use quotes or periods.\n\n"
        f"Message: {first_message}"
    )
    
    model_name = get_model_name()
    try:
        if LLM_PROVIDER == "openai":
            response = openai.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip('".')
        elif LLM_PROVIDER == "gemini":
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text.strip('".')
        elif LLM_PROVIDER == "groq":
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip('".')
        else:
            return "New Chat"
    except Exception as e:
        print(f"Failed to generate title: {e}")
        return "New Chat"

def extract_and_store_memory(db: Session, thread_id: int):
    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at).all()
    if not messages:
        return
    history = [{"role": msg.role, "content": msg.content} for msg in messages]
    summary = generate_memory_summary(history)
    memory = db.query(Memory).filter(Memory.thread_id == thread_id).first()
    if memory:
        memory.memory_summary = summary
    else:
        memory = Memory(thread_id=thread_id, memory_summary=summary)
        db.add(memory)
    db.commit()

def get_active_memories(db: Session, exclude_thread_id: int) -> str:
    recent_memories = (
        db.query(Memory)
        .join(Thread, Thread.id == Memory.thread_id)
        .filter(Thread.id != exclude_thread_id)
        .order_by(Thread.created_at.desc())
        .limit(5)
        .all()
    )
    if not recent_memories:
        return ""
    summaries = [mem.memory_summary for mem in recent_memories]
    return "\n\n".join(summaries)

# ==========================================
# APP & ROUTERS
# ==========================================
app = FastAPI(
    title="Memory Chat API",
    description="A full-stack AI chat application with custom shared-memory across threads."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/threads", response_model=ThreadResponse)
def create_thread(thread_data: ThreadCreate, db: Session = Depends(get_db)):
    new_thread = Thread(title=thread_data.title)
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    return new_thread

@app.get("/api/threads", response_model=List[ThreadResponse])
def get_all_threads(db: Session = Depends(get_db)):
    threads = db.query(Thread).order_by(Thread.created_at.desc()).all()
    return threads

@app.get("/api/threads/{thread_id}", response_model=ThreadWithMessagesResponse)
def get_thread_messages(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

@app.delete("/api/threads/{thread_id}")
def delete_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    db.delete(thread)
    db.commit()
    return {"message": "Thread and associated data deleted"}

SYSTEM_PROMPT_TEMPLATE = """
You are a helpful AI assistant.
You have access to the user's long-term memory.

MEMORIES:
{memories}

This memory should influence your current conversation. Focus on answering the current user message using this context if it's relevant.
"""

@app.post("/api/chat", response_model=ChatResponse)
def chat(chat_req: ChatRequest, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.id == chat_req.thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_msg = Message(thread_id=chat_req.thread_id, role="user", content=chat_req.message)
    db.add(user_msg)
    db.commit()

    messages = db.query(Message).filter(Message.thread_id == chat_req.thread_id).order_by(Message.created_at).all()
    
    if len(messages) == 1 and thread.title == "New Chat":
        new_title = generate_thread_title(chat_req.message)
        thread.title = new_title
        db.commit()
        
    history = [{"role": msg.role, "content": msg.content} for msg in messages[:-1]]

    memories_text = get_active_memories(db, exclude_thread_id=chat_req.thread_id)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(memories=memories_text if memories_text else "No previous memories.")

    try:
        assistant_text = generate_chat_response(system_prompt=system_prompt, history=history, user_message=chat_req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    assistant_msg = Message(thread_id=chat_req.thread_id, role="assistant", content=assistant_text)
    db.add(assistant_msg)
    db.commit()

    extract_and_store_memory(db, chat_req.thread_id)
    return ChatResponse(response=assistant_text)

@app.get("/")
def read_root():
    return {"message": "Welcome to Memory Chat API. Go to /docs for Swagger UI."}
