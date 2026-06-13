# 🤖 AI Chat Application

A **production-ready, multi-thread AI chat application** built with FastAPI, Streamlit, SQLite/PostgreSQL (via SQLAlchemy), and OpenAI GPT-4o mini.

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI + Uvicorn |
| ORM | SQLAlchemy |
| Database (local) | SQLite (`chat_app.db`) |
| Database (production) | PostgreSQL (Railway / Render / Supabase) |
| AI Model | OpenAI GPT-4o mini |

---

## Features

| Feature | Description |
|---|---|
| 💬 Multi-thread Conversations | Create, rename, and delete chat threads |
| 📜 Persistent History | All messages saved to DB, reloaded on thread open |
| 🧠 Universal Memory | Personal facts extracted and injected into every conversation |
| ✏️ Memory Management | View, delete individual memories, or clear all |
| 🔗 Backend Status | Live online/offline indicator in the UI |
| 🎨 Premium Dark UI | Glassmorphism, Inter font, gradient accents, micro-animations |

---

## Project Structure

```
project/
├── main.py                  ← FastAPI backend (all API endpoints)
├── database.py              ← SQLAlchemy models & session management
├── app.py                   ← Streamlit frontend
├── requirements.txt         ← Python dependencies
├── Procfile                 ← For Railway / Render deployment
├── runtime.txt              ← Python version for hosting platforms
├── .env.example             ← Environment variable template
├── .gitignore               ← Protects secrets & DB from git
├── .streamlit/
│   ├── config.toml          ← Streamlit dark theme config
│   └── secrets.toml         ← Streamlit Cloud secrets (DO NOT commit)
└── README.md                ← This file
```

---

## Quick Start (Local)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
copy .env.example .env
# Open .env and set: OPENAI_API_KEY=sk-your-key-here
```

### 3. Start the FastAPI backend (Terminal 1)

```bash
uvicorn main:app --reload
```

→ API available at: http://localhost:8000  
→ Interactive docs: http://localhost:8000/docs

### 4. Start the Streamlit frontend (Terminal 2)

```bash
streamlit run app.py
```

→ UI opens at: http://localhost:8501

---

## API Endpoints

### Threads

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/threads` | Create a new thread |
| `GET` | `/threads` | List all threads (with message counts) |
| `PATCH` | `/threads/{id}` | Rename a thread |
| `DELETE` | `/threads/{id}` | Delete thread and all its messages |

### Messages

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/messages/{thread_id}` | Get all messages in a thread |
| `DELETE` | `/messages/{message_id}` | Delete a single message |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, receive AI response |

**Chat Request:**
```json
{
  "thread_id": 1,
  "message": "My name is John and I live in Hyderabad"
}
```

**Chat Response:**
```json
{
  "assistant_message": "Nice to meet you, John!",
  "thread_id": 1,
  "memories_used": ["my name is John", "i live in Hyderabad"],
  "new_memories": ["my name is John", "i live in Hyderabad"]
}
```

### Memories

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/memories` | List all memories (id, text, created_at) |
| `DELETE` | `/memories/{id}` | Delete a specific memory |
| `DELETE` | `/memories` | Clear ALL memories |

### Utility

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |

---

## Database Schema

```
threads
  id          INTEGER  PK  AUTO
  title       VARCHAR(255)
  created_at  DATETIME

messages
  id          INTEGER  PK  AUTO
  thread_id   INTEGER  FK → threads.id  (CASCADE DELETE)
  role        VARCHAR(20)   -- 'user' | 'assistant'
  content     TEXT
  timestamp   DATETIME

memories
  id           INTEGER  PK  AUTO
  memory_text  TEXT     UNIQUE
  created_at   DATETIME
```

---

## Universal Memory — Extraction Patterns

The app detects personal facts using regex on every user message:

| Pattern | Example Input | Stored Memory |
|---|---|---|
| `My name is ...` | "My name is Alice" | `my name is Alice` |
| `Call me ...` | "Call me Bob" | `call me Bob` |
| `I live in ...` | "I live in Mumbai" | `i live in Mumbai` |
| `I work at ...` | "I work at Google" | `i work at Google` |
| `I work as ...` | "I work as a teacher" | `i work as a teacher` |
| `My favorite X is ...` | "My favorite color is blue" | `my favorite color is blue` |
| `I am a ...` | "I am a developer" | `i am a developer` |
| `I study at ...` | "I study at IIT" | `i study at IIT` |
| `My hobby is ...` | "My hobby is painting" | `my hobby is painting` |
| `I like ...` | "I like Python" | `i like Python` |

Duplicates are automatically skipped (enforced at DB level with `UNIQUE` constraint).

---

## Deployment (Railway + Streamlit Cloud)

### Backend → Railway

1. Push to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add **Environment Variables**:
   ```
   OPENAI_API_KEY = sk-your-key
   ```
4. Add PostgreSQL plugin → Railway fills `DATABASE_URL` automatically
5. Copy your Railway public URL: `https://your-app.up.railway.app`

### Frontend → Streamlit Cloud

1. [share.streamlit.io](https://share.streamlit.io) → New App → your repo → `app.py`
2. Settings → Secrets:
   ```toml
   BACKEND_URL = "https://your-app.up.railway.app"
   ```
3. Deploy ✅

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Backend offline` indicator | Run `uvicorn main:app --reload` |
| `OPENAI_API_KEY is not set` | Add key to `.env` file |
| `OpenAI 401 error` | Invalid API key — check your `.env` |
| `OpenAI 429 error` | Rate limited — wait and retry |
| SQLite errors on cloud | Set `DATABASE_URL` to a PostgreSQL connection string |
| Streamlit can't reach backend | Set `BACKEND_URL` in Streamlit secrets |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | — | Your OpenAI API key |
| `DATABASE_URL` | Optional | `sqlite:///./chat_app.db` | SQLAlchemy DB connection URL |
| `BACKEND_URL` | Optional | `http://localhost:8000` | FastAPI backend URL (used by Streamlit) |
