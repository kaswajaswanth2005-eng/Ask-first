"""
app.py
------
Streamlit frontend for the AI Chat Application.

Features:
  - Dark glassmorphism UI with gradient accents
  - Sidebar: all threads with message counts, create / rename / delete threads
  - Universal Memory panel with per-memory delete + clear all
  - Full conversation history loaded from DB on thread select
  - st.chat_message / st.chat_input interface
  - New-memory toast notification after each message
  - Backend connection status indicator

Configuration:
  BACKEND_URL : URL of the FastAPI backend (default: http://localhost:8000)
                Set this in your .env file or Streamlit Cloud Secrets.
"""

import os
import requests
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load .env locally; Streamlit Cloud uses its Secrets manager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Local: http://localhost:8000  |  Production: set BACKEND_URL in .env / Streamlit Secrets
API_BASE: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# ---------------------------------------------------------------------------
# Page Config (must be the very first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Chat — GPT-4o mini",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — Dark glassmorphism, Inter font, gradient accents
# ---------------------------------------------------------------------------

st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
}

/* ── Global background ── */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(15, 12, 41, 0.85) !important;
    backdrop-filter: blur(24px);
    border-right: 1px solid rgba(167, 139, 250, 0.12);
}
[data-testid="stSidebar"] * { color: #d4d4d8 !important; }

/* ── All text inputs ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(167,139,250,0.35) !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    font-size: 0.85rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #a78bfa !important;
    box-shadow: 0 0 0 2px rgba(167,139,250,0.2) !important;
}

/* ── All buttons ── */
.stButton > button {
    background: rgba(167, 139, 250, 0.12) !important;
    border: 1px solid rgba(167, 139, 250, 0.35) !important;
    border-radius: 10px !important;
    color: #d4d4d8 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 1rem !important;
    transition: all 0.18s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: rgba(167, 139, 250, 0.28) !important;
    border-color: #a78bfa !important;
    color: #fff !important;
    transform: translateX(3px);
    box-shadow: 0 0 14px rgba(167,139,250,0.25) !important;
}

/* ── New Thread button ── */
.btn-new > div > button, .btn-new button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 15px rgba(124,58,237,0.4) !important;
}
.btn-new > div > button:hover, .btn-new button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(124,58,237,0.6) !important;
}

/* ── Delete / danger button ── */
.btn-danger > div > button, .btn-danger button {
    background: rgba(239, 68, 68, 0.15) !important;
    border-color: rgba(239,68,68,0.4) !important;
    color: #fca5a5 !important;
}
.btn-danger > div > button:hover, .btn-danger button:hover {
    background: rgba(239,68,68,0.3) !important;
    border-color: #ef4444 !important;
    color: #fff !important;
}

/* ── Active thread highlight ── */
.thread-active > div > button, .thread-active button {
    background: rgba(167,139,250,0.25) !important;
    border-color: #a78bfa !important;
    color: #fff !important;
    font-weight: 600 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.035) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    margin-bottom: 0.6rem !important;
    backdrop-filter: blur(8px);
    padding: 0.8rem !important;
}

/* ── Chat input container ── */
[data-testid="stBottom"] {
    background: rgba(15,12,41,0.9) !important;
    backdrop-filter: blur(20px);
    border-top: 1px solid rgba(167,139,250,0.15);
    padding: 0.75rem 1rem !important;
}
[data-testid="stChatInput"] textarea {
    background: rgba(255,255,255,0.07) !important;
    border: 1.5px solid rgba(167,139,250,0.4) !important;
    border-radius: 14px !important;
    color: #e0e0e0 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #a78bfa !important;
    box-shadow: 0 0 0 2px rgba(167,139,250,0.2) !important;
}

/* ── Main title ── */
.main-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    padding: 0.8rem 0 0.3rem;
    letter-spacing: -0.5px;
}
.subtitle {
    text-align: center;
    color: rgba(255,255,255,0.35);
    font-size: 0.82rem;
    margin-bottom: 1.2rem;
    letter-spacing: 0.5px;
}

/* ── Status dot ── */
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-online  { background: #34d399; box-shadow: 0 0 6px #34d399; }
.status-offline { background: #ef4444; box-shadow: 0 0 6px #ef4444; }

/* ── Memory pill ── */
.memory-pill {
    display: inline-block;
    background: rgba(52, 211, 153, 0.12);
    border: 1px solid rgba(52, 211, 153, 0.35);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.74rem;
    color: #6ee7b7;
    margin: 3px 2px;
    word-break: break-word;
}

/* ── New memory toast ── */
.new-memory-toast {
    background: rgba(52, 211, 153, 0.12);
    border: 1px solid rgba(52, 211, 153, 0.4);
    border-radius: 10px;
    padding: 0.5rem 0.9rem;
    font-size: 0.8rem;
    color: #6ee7b7;
    margin-top: 0.5rem;
}

/* ── Thread badge ── */
.thread-badge {
    display: inline-block;
    background: rgba(167,139,250,0.2);
    color: #a78bfa;
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-left: 6px;
    vertical-align: middle;
}

/* ── Section header ── */
.section-header {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: rgba(255,255,255,0.3) !important;
    margin: 0.6rem 0 0.4rem;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    color: rgba(255,255,255,0.25);
    padding: 5rem 2rem 3rem;
}
.empty-icon { font-size: 3.5rem; margin-bottom: 1rem; }
.empty-title {
    font-weight: 700;
    font-size: 1.1rem;
    color: rgba(255,255,255,0.4);
    margin-bottom: 0.5rem;
}
.empty-sub { font-size: 0.83rem; color: rgba(255,255,255,0.22); }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #a78bfa !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(167,139,250,0.35); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(167,139,250,0.6); }

/* ── Caption / small text ── */
.stChatMessage small, .stCaption, [data-testid="stCaptionContainer"] {
    color: rgba(255,255,255,0.3) !important;
    font-size: 0.72rem !important;
}

/* ── Toast / success message ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.83rem !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(path: str) -> dict | list | None:
    """GET request to the FastAPI backend. Returns None on failure."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None


def api_post(path: str, payload: dict) -> dict | None:
    """POST request to the FastAPI backend."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the FastAPI backend. Run: `uvicorn main:app --reload`")
        return None
    except requests.exceptions.HTTPError:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        st.error(f"⚠️ Backend error: {detail}")
        return None
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")
        return None


def api_patch(path: str, payload: dict) -> dict | None:
    """PATCH request to the FastAPI backend."""
    try:
        r = requests.patch(f"{API_BASE}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return None


def api_delete(path: str) -> dict | None:
    """DELETE request to the FastAPI backend."""
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return None


def check_backend() -> bool:
    """Returns True if the FastAPI backend is reachable."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def format_time(iso_str: str) -> str:
    """Convert ISO timestamp to a friendly human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return iso_str


# ---------------------------------------------------------------------------
# Session State Initialisation
# ---------------------------------------------------------------------------

defaults = {
    "selected_thread_id": None,
    "selected_thread_title": None,
    "renaming_thread_id": None,
    "confirm_delete_thread_id": None,
    "last_new_memories": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:

    # ── Brand header ──
    st.markdown('<div class="main-title" style="font-size:1.3rem; padding:0.4rem 0 0.2rem;">🤖 AI Chat</div>', unsafe_allow_html=True)

    # ── Backend status ──
    is_online = check_backend()
    dot_class = "status-online" if is_online else "status-offline"
    status_text = "Backend online" if is_online else "Backend offline"
    st.markdown(
        f'<div style="text-align:center; font-size:0.73rem; color:rgba(255,255,255,0.4); margin-bottom:0.8rem;">'
        f'<span class="status-dot {dot_class}"></span>{status_text}</div>',
        unsafe_allow_html=True,
    )

    if not is_online:
        st.warning("Start FastAPI: `uvicorn main:app --reload`")

    st.markdown("---")

    # ── Create new thread ──
    st.markdown('<div class="section-header">New Thread</div>', unsafe_allow_html=True)
    new_thread_name = st.text_input(
        "name",
        placeholder="Thread name (optional)…",
        label_visibility="collapsed",
        key="new_thread_name_input",
    )
    st.markdown('<div class="btn-new">', unsafe_allow_html=True)
    if st.button("＋  Create New Thread", key="btn_new_thread", use_container_width=True):
        title = new_thread_name.strip() or f"Thread {datetime.now().strftime('%b %d %H:%M')}"
        result = api_post("/threads", {"title": title})
        if result:
            st.session_state.selected_thread_id = result["id"]
            st.session_state.selected_thread_title = result["title"]
            st.session_state.last_new_memories = []
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Thread list ──
    st.markdown('<div class="section-header">Your Threads</div>', unsafe_allow_html=True)
    threads = api_get("/threads") or []

    if not threads:
        st.caption("No threads yet. Create one above ☝️")
    else:
        for thread in threads:
            tid = thread["id"]
            t_title = thread["title"]
            t_count = thread.get("message_count", 0)
            is_active = tid == st.session_state.selected_thread_id

            # Thread select button
            label = f"{'▶' if is_active else '💬'}  {t_title}"
            count_badge = f'<span class="thread-badge">{t_count}</span>' if t_count > 0 else ""

            btn_class = "thread-active" if is_active else ""
            st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
            if st.button(label, key=f"thread_select_{tid}", use_container_width=True):
                st.session_state.selected_thread_id = tid
                st.session_state.selected_thread_title = t_title
                st.session_state.renaming_thread_id = None
                st.session_state.confirm_delete_thread_id = None
                st.session_state.last_new_memories = []
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            # Rename / Delete controls for the active thread
            if is_active:
                col_r, col_d = st.columns(2)
                with col_r:
                    if st.button("✏️ Rename", key=f"rename_btn_{tid}", use_container_width=True):
                        st.session_state.renaming_thread_id = tid if st.session_state.renaming_thread_id != tid else None
                        st.rerun()
                with col_d:
                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button("🗑 Delete", key=f"delete_btn_{tid}", use_container_width=True):
                        st.session_state.confirm_delete_thread_id = tid if st.session_state.confirm_delete_thread_id != tid else None
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                # Inline rename form
                if st.session_state.renaming_thread_id == tid:
                    new_title = st.text_input(
                        "New name",
                        value=t_title,
                        key=f"rename_input_{tid}",
                        label_visibility="collapsed",
                    )
                    if st.button("✔ Save name", key=f"rename_save_{tid}", use_container_width=True):
                        result = api_patch(f"/threads/{tid}", {"title": new_title})
                        if result:
                            st.session_state.selected_thread_title = result["title"]
                            st.session_state.renaming_thread_id = None
                            st.rerun()

                # Inline delete confirmation
                if st.session_state.confirm_delete_thread_id == tid:
                    st.warning(f"Delete **{t_title}** and all its messages?")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                        if st.button("Yes, delete", key=f"confirm_del_{tid}", use_container_width=True):
                            api_delete(f"/threads/{tid}")
                            st.session_state.selected_thread_id = None
                            st.session_state.selected_thread_title = None
                            st.session_state.confirm_delete_thread_id = None
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    with col_n:
                        if st.button("Cancel", key=f"cancel_del_{tid}", use_container_width=True):
                            st.session_state.confirm_delete_thread_id = None
                            st.rerun()

            st.markdown("<div style='margin-bottom:2px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Universal Memory panel ──
    memories_data = api_get("/memories") or []
    mem_count = len(memories_data)
    with st.expander(f"🧠 Universal Memory  ({mem_count})", expanded=False):
        if not memories_data:
            st.caption("No memories yet. Tell me about yourself!")
        else:
            for mem in memories_data:
                col_m, col_x = st.columns([5, 1])
                with col_m:
                    st.markdown(
                        f'<div class="memory-pill">📌 {mem["memory_text"]}</div>',
                        unsafe_allow_html=True,
                    )
                with col_x:
                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button("✕", key=f"del_mem_{mem['id']}", help="Delete this memory"):
                        api_delete(f"/memories/{mem['id']}")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🗑 Clear all memories", key="clear_all_memories", use_container_width=True):
                api_delete("/memories")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main Chat Area
# ---------------------------------------------------------------------------

st.markdown('<div class="main-title">AI Chat Application</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Multi-thread conversations · Universal memory · GPT-4o mini</div>',
    unsafe_allow_html=True,
)

# ── No thread selected: landing screen ──
if st.session_state.selected_thread_id is None:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">💬</div>
        <div class="empty-title">Select or create a thread to start chatting</div>
        <div class="empty-sub">Use the sidebar on the left to manage your conversations.<br>
        Your messages and memories are saved automatically.</div>
    </div>
    """, unsafe_allow_html=True)

    # Feature highlights
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    cards = [
        ("💬", "Multi-Thread", "Create separate conversations for different topics"),
        ("🧠", "Universal Memory", "Facts you share are remembered across all threads"),
        ("⚡", "GPT-4o mini", "Fast, smart responses powered by OpenAI"),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], cards):
        with col:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
                        border-radius:14px; padding:1.2rem; text-align:center; height:120px;">
                <div style="font-size:1.8rem">{icon}</div>
                <div style="font-weight:700; color:#a78bfa; font-size:0.9rem; margin:0.3rem 0;">{title}</div>
                <div style="font-size:0.75rem; color:rgba(255,255,255,0.35);">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

# ── Thread selected: full chat UI ──
else:
    thread_id = st.session_state.selected_thread_id
    thread_title = st.session_state.selected_thread_title or f"Thread #{thread_id}"

    # ── Thread header bar ──
    col_title, col_mem = st.columns([5, 1])
    with col_title:
        st.markdown(
            f"<h3 style='color:#a78bfa; margin:0; font-weight:700;'>💬 {thread_title}</h3>",
            unsafe_allow_html=True,
        )
    with col_mem:
        mem_count = len(api_get("/memories") or [])
        st.markdown(
            f"<div style='text-align:right; color:rgba(255,255,255,0.35); "
            f"font-size:0.78rem; padding-top:0.9rem;'>🧠 {mem_count} memories</div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    # ── New memory notification ──
    if st.session_state.last_new_memories:
        new_mem_list = "  ·  ".join(f"📌 {m}" for m in st.session_state.last_new_memories)
        st.markdown(
            f'<div class="new-memory-toast">✨ New memory saved: {new_mem_list}</div>',
            unsafe_allow_html=True,
        )

    # ── Fetch and render message history ──
    messages = api_get(f"/messages/{thread_id}") or []

    if not messages:
        st.markdown("""
        <div style='text-align:center; color:rgba(255,255,255,0.25); padding:3rem 2rem;'>
            <div style='font-size:2rem; margin-bottom:0.5rem;'>👋</div>
            <div>No messages yet. Send the first one!</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            ts = format_time(msg["timestamp"])

            if role == "user":
                with st.chat_message("user", avatar="🧑"):
                    st.markdown(content)
                    st.caption(f"You  ·  {ts}")
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)
                    st.caption(f"AI  ·  {ts}")

    # ── Chat input ──
    user_input = st.chat_input(
        "Type your message… (e.g. 'My name is John')",
        key="chat_input_main",
    )

    if user_input:
        # Optimistic UI: show user message immediately
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        # Send to backend & get AI response
        with st.spinner("Thinking…"):
            result = api_post("/chat", {"thread_id": thread_id, "message": user_input})

        if result:
            # Show assistant response
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(result["assistant_message"])

            # Store any newly extracted memories for the toast notification
            st.session_state.last_new_memories = result.get("new_memories", [])

            # Rerun to reload full history from DB (cleans up optimistic messages)
            st.rerun()
