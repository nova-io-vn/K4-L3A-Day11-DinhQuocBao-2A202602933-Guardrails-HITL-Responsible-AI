/* VinBank AI Demo — app.js */

const input       = document.getElementById('messageInput');
const sendBtn     = document.getElementById('sendBtn');
const chatScroll  = document.getElementById('chatScroll');
const newChatBtn  = document.getElementById('newChatBtn');
const quickSection = document.getElementById('quickSection');

const statTotal   = document.getElementById('statTotal');
const statBlocked = document.getElementById('statBlocked');
const statRate    = document.getElementById('statRate');

let totalCount   = 0;
let blockedCount = 0;

function updateStats(blocked = false) {
  totalCount++;
  if (blocked) blockedCount++;
  statTotal.textContent   = totalCount;
  statBlocked.textContent = blockedCount;
  const pct = totalCount > 0 ? Math.round(((totalCount - blockedCount) / totalCount) * 100) : 100;
  statRate.textContent    = `${pct}%`;
  statRate.style.color    = pct >= 80 ? '' : '#f87171';
}

function now() {
  return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function escape(v) {
  const n = document.createElement('div'); n.textContent = v ?? ''; return n.innerHTML;
}

function safeHtml(v) {
  return escape(String(v ?? ''))
    .replace(/&lt;b&gt;/gi, '<b>').replace(/&lt;\/b&gt;/gi, '</b>')
    .replace(/&lt;em&gt;/gi, '<em>').replace(/&lt;\/em&gt;/gi, '</em>')
    .replace(/&lt;strong&gt;/gi, '<strong>').replace(/&lt;\/strong&gt;/gi, '</strong>');
}

function appendMessage(text, role, kind = 'bot') {
  const row = document.createElement('div');
  if (role === 'user') {
    row.className = 'message-row user-row';
    row.innerHTML = `
      <div class="msg-av user-av">●</div>
      <div class="msg-wrap">
        <div class="msg-meta">Bạn <span>${now()}</span></div>
        <div class="msg-bubble user-bubble">${escape(text)}</div>
      </div>`;
  } else {
    const bubbleClass = kind === 'blocked' ? 'blocked-bubble'
                      : kind === 'warning' ? 'warning-bubble'
                      : 'bot-bubble';
    row.className = 'message-row bot-row';
    row.innerHTML = `
      <div class="msg-av bot-av">✦</div>
      <div class="msg-wrap">
        <div class="msg-meta">Sky Assistant <span>${now()}</span></div>
        <div class="msg-bubble ${bubbleClass}">${safeHtml(text)}</div>
      </div>`;
  }
  chatScroll.appendChild(row);
  chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: 'smooth' });
}

function appendTyping() {
  const row = document.createElement('div');
  row.className = 'message-row bot-row typing-row';
  row.innerHTML = `
    <div class="msg-av bot-av">✦</div>
    <div class="msg-wrap">
      <div class="msg-meta">Sky Assistant <span>đang soạn...</span></div>
      <div class="msg-bubble bot-bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>`;
  chatScroll.appendChild(row);
  chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: 'smooth' });
  return row;
}

async function sendMessage(text = input.value.trim()) {
  if (!text) return;
  input.value = '';
  input.style.height = 'auto';
  quickSection?.remove();

  appendMessage(text, 'user');
  const typing = appendTyping();

  try {
    const res  = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    typing.remove();
    const kind = data.mode === 'guardrail' ? 'blocked'
               : data.mode === 'offline'   ? 'warning'
               : 'bot';
    const reply = res.ok ? safeHtml(data.reply) : escape(data.error || 'Mình chưa thể trả lời lúc này.');
    appendMessage(reply, 'bot', kind);
    updateStats(kind === 'blocked');
  } catch {
    typing.remove();
    appendMessage(
      'Không kết nối được tới máy chủ demo. Hãy chạy <b>python src/demo_server.py</b> rồi tải lại trang.',
      'bot', 'warning'
    );
    updateStats(false);
  }
}

/* ── Event wiring ── */
document.querySelectorAll('[data-prompt]').forEach(btn =>
  btn.addEventListener('click', () => sendMessage(btn.dataset.prompt))
);

sendBtn.addEventListener('click', () => sendMessage());

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 100)}px`;
});

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

newChatBtn.addEventListener('click', () => {
  document.querySelectorAll('#chatScroll .message-row:not(:first-of-type)').forEach(r => r.remove());
  document.querySelector('#chatScroll .quick-section')?.remove();
  totalCount = blockedCount = 0;
  statTotal.textContent = statBlocked.textContent = '0';
  statRate.textContent = '—';
  input.focus();
});

