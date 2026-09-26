const input = document.querySelector('#messageInput');
const sendBtn = document.querySelector('#sendBtn');
const chatScroll = document.querySelector('#chatScroll');
const quickGrid = document.querySelector('#quickGrid');
const newChatBtn = document.querySelector('#newChatBtn');

const replies = [
  { match: ['số dư', 'balance'], text: 'Bạn có thể kiểm tra số dư trong ứng dụng VinBank bằng cách vào <b>Tài khoản</b> → chọn tài khoản cần xem. Vì lý do bảo mật, mình không yêu cầu bạn gửi mật khẩu hoặc mã OTP trong khung chat này.' },
  { match: ['lãi suất', 'tiết kiệm'], text: 'Lãi suất tiết kiệm phụ thuộc vào kỳ hạn và hình thức gửi. Bạn có thể xem bảng lãi suất mới nhất trong mục <b>Tiết kiệm</b> của ứng dụng VinBank hoặc cho mình biết kỳ hạn bạn đang quan tâm.' },
  { match: ['chuyển tiền', 'chuyển khoản', 'transfer'], text: 'Để chuyển tiền, bạn mở <b>Giao dịch</b> → <b>Chuyển tiền</b>, chọn người nhận, kiểm tra kỹ tên và số tài khoản rồi xác nhận bằng phương thức bảo mật của bạn.' },
  { match: ['hack', 'password', 'mật khẩu', 'api key', 'system prompt', 'jailbreak'], text: 'Mình không thể hỗ trợ yêu cầu về thông tin nội bộ, mật khẩu hoặc khóa truy cập. Mình có thể giúp bạn với các dịch vụ ngân hàng an toàn như tài khoản, giao dịch, tiết kiệm và thẻ.' },
];

function chooseReply(text) {
  const lower = text.toLowerCase();
  const found = replies.find(item => item.match.some(word => lower.includes(word)));
  return found?.text || 'Mình đã ghi nhận câu hỏi của bạn. Bạn có thể hỏi về số dư, giao dịch, tiết kiệm, khoản vay hoặc thẻ tín dụng. Mình sẽ hướng dẫn từng bước thật dễ hiểu.';
}

function scrollBottom() { chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: 'smooth' }); }
function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }

function addMessage(text, role) {
  const row = document.createElement('div');
  row.className = `message-row ${role === 'user' ? 'user-message' : 'bot-message'}`;
  if (role === 'user') {
    row.innerHTML = `<div class="message-content"><div class="message-meta">Bạn <span>vừa xong</span></div><div class="bubble">${escapeHtml(text)}</div></div>`;
  } else {
    row.innerHTML = `<div class="mini-avatar">✦</div><div class="message-content"><div class="message-meta">Sky <span>vừa xong</span></div><div class="bubble">${text}</div></div>`;
  }
  chatScroll.appendChild(row);
  scrollBottom();
}

function addTyping() {
  const row = document.createElement('div');
  row.className = 'message-row bot-message typing-row';
  row.innerHTML = '<div class="mini-avatar">✦</div><div class="message-content"><div class="message-meta">Sky <span>đang soạn...</span></div><div class="bubble"><div class="typing"><i></i><i></i><i></i></div></div></div>';
  chatScroll.appendChild(row); scrollBottom(); return row;
}

function sendMessage(value = input.value.trim()) {
  if (!value) return;
  input.value = ''; input.style.height = 'auto';
  quickGrid?.remove();
  addMessage(value, 'user');
  const typing = addTyping();
  setTimeout(() => { typing.remove(); addMessage(chooseReply(value), 'bot'); }, 850 + Math.random() * 650);
}

document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => sendMessage(button.dataset.prompt)));
sendBtn.addEventListener('click', () => sendMessage());
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 82)}px`; });
input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(); } });
newChatBtn.addEventListener('click', () => { document.querySelectorAll('.message-row:not(:first-of-type)').forEach(row => row.remove()); input.focus(); });
