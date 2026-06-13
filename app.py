import streamlit as st
import requests

API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="Memory Chat", page_icon="🧠", layout="wide")

custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #12100E 0%, #2B4162 100%) !important;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Force inner containers to be transparent so gradient shows everywhere */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottomBlock"], .stApp > header, .stAppBottomBlock, .stChatFloatingInputContainer {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background: rgba(20, 20, 30, 0.6) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Chat Bubbles Container */
    [data-testid="stChatMessage"] {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 15px;
        backdrop-filter: blur(5px);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    
    /* User Message Bubble */
    [data-testid="stChatMessage"]:nth-child(even) {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: #000;
        border: none;
    }

    /* Assistant Message Bubble */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: #000;
        border: none;
    }
    
    /* Input Box */
    [data-testid="stChatInput"] {
        background-color: transparent !important;
        border: none !important;
    }
    
    [data-testid="stChatInput"] > div {
        background-color: #FFFFFF !important;
        border-radius: 30px !important;
        border: 1px solid #E0E0E0 !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        padding-right: 5px;
    }
    
    [data-testid="stChatInput"] textarea {
        color: #000000 !important;
        background-color: transparent !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
        font-size: 16px;
    }
    
    [data-testid="stChatInput"] textarea::placeholder {
        color: #888888 !important;
        -webkit-text-fill-color: #888888 !important;
    }
    
    [data-testid="stChatInput"] button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 50% !important;
        width: 38px !important;
        height: 38px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }
    
    [data-testid="stChatInput"] button:hover {
        background-color: #333333 !important;
        transform: scale(1.05);
    }
    
    [data-testid="stChatInput"] button svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #FF512F 0%, #DD2476 100%);
        color: white;
        border: none;
        border-radius: 8px;
        transition: all 0.3s ease;
        font-weight: 600;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(221, 36, 118, 0.4);
        color: white;
        border: none;
    }
    
    /* Titles */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar text fix */
    .css-17lntkn, p {
        color: #e0e0e0;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# User Profile Header
col1, col2 = st.columns([0.8, 0.2])
with col2:
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 12px;">
        <div style="text-align: right; line-height: 1.2;">
            <span style="font-size: 0.8em; color: #bbb;">Welcome back,</span><br>
            <strong style="color: white; font-size: 1.1em;">Akash</strong>
        </div>
        <div style="width: 45px; height: 45px; border-radius: 50%; background: linear-gradient(135deg, #4facfe, #00f2fe); display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: bold; color: #12100E; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
            AG
        </div>
    </div>
    """, unsafe_allow_html=True)

def get_threads():
    try:
        response = requests.get(f"{API_URL}/threads")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
    return []

def create_thread(title="New Chat"):
    response = requests.post(f"{API_URL}/threads", json={"title": title})
    if response.status_code == 200:
        return response.json()
    return None

def delete_thread(thread_id):
    response = requests.delete(f"{API_URL}/threads/{thread_id}")
    return response.status_code == 200

def get_thread_messages(thread_id):
    response = requests.get(f"{API_URL}/threads/{thread_id}")
    if response.status_code == 200:
        return response.json().get("messages", [])
    return []

def send_chat_message(thread_id, message):
    response = requests.post(f"{API_URL}/chat", json={"thread_id": thread_id, "message": message})
    if response.status_code == 200:
        return response.json().get("response")
    else:
        st.error(f"Error: {response.text}")
        return None

# State Initialization
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# Sidebar
with st.sidebar:
    st.title("🧠 Memory Chat")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_thread = create_thread()
        if new_thread:
            st.session_state.current_thread_id = new_thread["id"]
            st.rerun()

    st.divider()
    st.subheader("Chats")
    
    threads = get_threads()
    for thread in threads:
        col1, col2 = st.columns([0.85, 0.15])
        
        # Thread Select Button
        with col1:
            is_active = (st.session_state.current_thread_id == thread["id"])
            button_label = f"**{thread['title']}**" if is_active else thread['title']
            if st.button(button_label, key=f"select_{thread['id']}", use_container_width=True):
                st.session_state.current_thread_id = thread["id"]
                st.rerun()
                
        # Thread Delete Button
        with col2:
            if st.button("🗑️", key=f"delete_{thread['id']}"):
                delete_thread(thread["id"])
                if st.session_state.current_thread_id == thread["id"]:
                    st.session_state.current_thread_id = None
                st.rerun()

# Main Chat Window
if st.session_state.current_thread_id:
    messages = get_thread_messages(st.session_state.current_thread_id)
    
    if not messages:
        with st.chat_message("assistant"):
            st.markdown("👋 **Hi there! How can I help you today?** \n\nI'm your personalized AI assistant. I will remember your skills, preferences, and goals across all our conversations. Let's get started!")

    # Display message history
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input
    if prompt := st.chat_input("Message Memory Chat..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Get AI response
        with st.spinner("Thinking..."):
            response_text = send_chat_message(st.session_state.current_thread_id, prompt)
            
        # Display AI response
        if response_text:
            with st.chat_message("assistant"):
                st.markdown(response_text)
            st.rerun() # Refresh to fetch history with accurate ID logic if needed, though we already displayed it. 
            # We rerun to make sure everything is in sync with backend (and memory generation happened).
else:
    st.markdown("<div style='text-align: center; margin-top: 10vh;'>", unsafe_allow_html=True)
    st.title("Welcome to Memory Chat 🧠")
    st.markdown("### Your personalized AI that *Remembers*.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.info("💡 **Tip:** Tell me about your skills, projects, or goals. I will remember them in future threads!")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Start a New Conversation Now", use_container_width=True):
            new_thread = create_thread()
            if new_thread:
                st.session_state.current_thread_id = new_thread["id"]
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
