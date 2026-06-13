const API_BASE = '/api';
let currentThreadId = null;
let sidebarOpen = true;

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadThreads();
    loadMemories();
});

// ── Health Check ──────────────────────────────────────────────────────────
async function checkHealth() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    dot.className = 'dot connecting';
    text.textContent = 'Connecting...';

    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            dot.className = 'dot';
            text.textContent = 'Backend online';
        } else {
            throw new Error('Not OK');
        }
    } catch (e) {
        dot.className = 'dot offline';
        text.textContent = 'Backend offline';
    }
}

// ── Threads ───────────────────────────────────────────────────────────────
async function loadThreads() {
    try {
        const res = await fetch(`${API_BASE}/threads`);
        if (!res.ok) throw new Error('Failed to fetch threads');
        const threads = await res.json();
        renderThreads(threads);
    } catch (e) {
        console.error('Failed to load threads:', e);
    }
}

function renderThreads(threads) {
    const container = document.getElementById('threads-container');
    container.innerHTML = '';

    if (threads.length === 0) {
        container.innerHTML = `
            <div class="empty-threads">
                <div class="empty-threads-icon">💬</div>
                <div>No threads yet</div>
            </div>`;
        return;
    }

    threads.forEach(t => {
        const div = document.createElement('div');
        div.className = `thread-item ${t.id === currentThreadId ? 'active' : ''}`;
        div.id = `thread-${t.id}`;
        div.onclick = () => selectThread(t.id, t.title);

        div.innerHTML = `
            <div class="thread-name">💬 ${escapeHtml(t.title)}</div>
            <span class="thread-count">${t.message_count}</span>
            <button class="thread-delete-btn" onclick="event.stopPropagation(); deleteThread(${t.id})" title="Delete thread">✕</button>
        `;
        container.appendChild(div);
    });
}

async function createNewThread() {
    try {
        const res = await fetch(`${API_BASE}/threads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Thread' })
        });
        if (!res.ok) throw new Error('Failed to create thread');
        const thread = await res.json();
        await loadThreads();
        selectThread(thread.id, thread.title);
    } catch (e) {
        showToast('Failed to create thread', 'error');
        console.error(e);
    }
}

async function deleteThread(id) {
    if (!confirm('Delete this thread and all its messages?')) return;
    try {
        await fetch(`${API_BASE}/threads/${id}`, { method: 'DELETE' });
        if (currentThreadId === id) {
            currentThreadId = null;
            resetChatUI();
        }
        await loadThreads();
        showToast('Thread deleted');
    } catch (e) {
        showToast('Failed to delete thread', 'error');
    }
}

async function deleteCurrentThread() {
    if (currentThreadId) deleteThread(currentThreadId);
}

async function renameThread() {
    if (!currentThreadId) return;
    const title = prompt('Enter new thread name:');
    if (!title || !title.trim()) return;

    try {
        const res = await fetch(`${API_BASE}/threads/${currentThreadId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title.trim() })
        });
        if (!res.ok) throw new Error('Failed to rename');
        const thread = await res.json();
        document.getElementById('chat-title').textContent = thread.title;
        await loadThreads();
        showToast('Thread renamed');
    } catch (e) {
        showToast('Failed to rename thread', 'error');
    }
}

async function selectThread(id, title) {
    currentThreadId = id;

    // Update header
    document.getElementById('chat-title').textContent = title;
    document.getElementById('chat-subtitle').textContent = 'Loading messages...';

    // Show header action buttons
    document.getElementById('btn-rename').style.display = 'flex';
    document.getElementById('btn-delete-thread').style.display = 'flex';

    // Enable input
    document.getElementById('chat-input').disabled = false;
    document.getElementById('btn-send').disabled = false;

    // Update sidebar active state
    document.querySelectorAll('.thread-item').forEach(el => el.classList.remove('active'));
    const threadEl = document.getElementById(`thread-${id}`);
    if (threadEl) threadEl.classList.add('active');

    // Load messages
    const container = document.getElementById('chat-container');
    container.innerHTML = `<div style="margin:auto;"><div class="loader">
        <div class="loader-dot"></div><div class="loader-dot"></div><div class="loader-dot"></div>
    </div></div>`;

    try {
        const res = await fetch(`${API_BASE}/messages/${id}`);
        if (!res.ok) throw new Error('Failed to fetch messages');
        const messages = await res.json();

        container.innerHTML = '';

        if (messages.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">👋</div>
                    <div>No messages yet — say hello!</div>
                </div>`;
        } else {
            messages.forEach(m => appendMessage(m.role, m.content, m.timestamp, false));
        }

        document.getElementById('chat-subtitle').textContent = `${messages.length} message${messages.length !== 1 ? 's' : ''}`;
        scrollToBottom();
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div>Failed to load messages. Please try again.</div></div>`;
        console.error(e);
    }
}

function resetChatUI() {
    document.getElementById('chat-title').textContent = 'Select a Thread';
    document.getElementById('chat-subtitle').textContent = 'Ask-first AI Assistant';
    document.getElementById('btn-rename').style.display = 'none';
    document.getElementById('btn-delete-thread').style.display = 'none';
    document.getElementById('chat-input').disabled = true;
    document.getElementById('btn-send').disabled = true;
    document.getElementById('chat-container').innerHTML = `
        <div class="welcome-state">
            <div class="welcome-logo">✦</div>
            <h1 class="welcome-title">Welcome to Ask-first</h1>
            <p class="welcome-subtitle">Your AI assistant that remembers you across all conversations.</p>
            <div class="welcome-features">
                <div class="feature-chip">🧠 Persistent Memory</div>
                <div class="feature-chip">💬 Multi-thread Chat</div>
                <div class="feature-chip">⚡ Fast AI Responses</div>
            </div>
            <button class="btn-welcome-start" onclick="createNewThread()">Start Chatting →</button>
        </div>`;
}

// ── Messages ──────────────────────────────────────────────────────────────
function appendMessage(role, content, timestamp, animate = true) {
    const container = document.getElementById('chat-container');
    const empty = container.querySelector('.empty-state, .welcome-state');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = `message ${role}`;
    if (!animate) div.style.animation = 'none';

    const formattedContent = formatMarkdown(content);
    const timeString = timestamp
        ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : '';

    const roleLabel = role === 'user' ? '👤 You' : '✦ Assistant';

    div.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        <div class="message-meta">
            <span>${roleLabel}</span>
            ${timeString ? `<span>·</span><span>${timeString}</span>` : ''}
        </div>
    `;
    container.appendChild(div);
    return div;
}

function formatMarkdown(text) {
    return escapeHtml(text)
        // Code blocks (must come before inline code)
        .replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Newlines
        .replace(/\n/g, '<br>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function scrollToBottom() {
    const container = document.getElementById('chat-container');
    container.scrollTop = container.scrollHeight;
}

// ── Send Message ──────────────────────────────────────────────────────────
function handleEnter(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

async function sendMessage() {
    if (!currentThreadId) return;

    const input = document.getElementById('chat-input');
    const btn = document.getElementById('btn-send');
    const text = input.value.trim();
    if (!text) return;

    // Optimistic UI
    input.value = '';
    input.style.height = 'auto';
    input.disabled = true;
    btn.disabled = true;

    appendMessage('user', text, new Date().toISOString());
    scrollToBottom();

    // Loading indicator
    const container = document.getElementById('chat-container');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = `<div class="loader">
        <div class="loader-dot"></div><div class="loader-dot"></div><div class="loader-dot"></div>
    </div>`;
    container.appendChild(loadingDiv);
    scrollToBottom();

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: currentThreadId, message: text })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        loadingDiv.remove();
        appendMessage('assistant', data.assistant_message, new Date().toISOString());
        scrollToBottom();

        // Update message count in sidebar
        const threadEl = document.getElementById(`thread-${currentThreadId}`);
        if (threadEl) {
            const countEl = threadEl.querySelector('.thread-count');
            if (countEl) countEl.textContent = parseInt(countEl.textContent || '0') + 2;
        }

        if (data.new_memories && data.new_memories.length > 0) {
            showToast(`✨ Memory saved: ${data.new_memories.join(', ')}`);
            loadMemories();
        }

    } catch (e) {
        loadingDiv.remove();
        appendMessage('assistant', `⚠️ Error: ${e.message || 'Failed to send message. Please try again.'}`);
        scrollToBottom();
        console.error(e);
    } finally {
        input.disabled = false;
        btn.disabled = false;
        input.focus();
    }
}

// ── Memories ──────────────────────────────────────────────────────────────
async function loadMemories() {
    try {
        const res = await fetch(`${API_BASE}/memories`);
        if (!res.ok) throw new Error('Failed to fetch memories');
        const memories = await res.json();
        renderMemories(memories);
    } catch (e) {
        console.error('Failed to load memories:', e);
    }
}

function renderMemories(memories) {
    const container = document.getElementById('memory-container');
    const badge = document.getElementById('memory-count');
    const clearBtn = document.getElementById('btn-clear-memory');

    badge.textContent = memories.length;
    clearBtn.style.display = memories.length > 0 ? 'block' : 'none';

    container.innerHTML = '';

    if (memories.length === 0) {
        const empty = document.createElement('div');
        empty.style.cssText = 'font-size:0.75rem;color:var(--text-muted);text-align:center;padding:0.5rem 0;';
        empty.textContent = 'No memories yet';
        container.appendChild(empty);
        return;
    }

    memories.forEach(m => {
        const div = document.createElement('div');
        div.className = 'memory-pill';
        div.innerHTML = `
            <span>📌 ${escapeHtml(m.memory_text)}</span>
            <button class="memory-delete-btn" onclick="deleteMemory(${m.id})" title="Forget this">✕</button>
        `;
        container.appendChild(div);
    });
}

function toggleMemory() {
    const list = document.getElementById('memory-container');
    const chevron = document.getElementById('memory-chevron');
    const toggle = document.getElementById('memory-toggle');
    const isOpen = list.classList.toggle('open');
    chevron.classList.toggle('open', isOpen);
    toggle.setAttribute('aria-expanded', isOpen);
}

async function deleteMemory(id) {
    try {
        await fetch(`${API_BASE}/memories/${id}`, { method: 'DELETE' });
        await loadMemories();
    } catch (e) {
        showToast('Failed to delete memory', 'error');
    }
}

async function clearAllMemories() {
    if (!confirm('Clear all memories? The AI will forget everything about you.')) return;
    try {
        await fetch(`${API_BASE}/memories`, { method: 'DELETE' });
        await loadMemories();
        showToast('All memories cleared');
    } catch (e) {
        showToast('Failed to clear memories', 'error');
    }
}

// ── Sidebar ───────────────────────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}
