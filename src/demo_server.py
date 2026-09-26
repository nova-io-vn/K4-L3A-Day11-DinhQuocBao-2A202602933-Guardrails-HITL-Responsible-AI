"""Local VinBank chatbot demo server.

Serves demo/ and exposes a small /api/chat endpoint backed by the Blue agent.
Blue always uses the locked OpenRouter model and the assignment guardrails.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEMO = ROOT / "demo"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from assignment.pipeline import build_production_plugins
from agents.agent import BLUE_INSTRUCTION
from core.config import (
    blue_client_kwargs,
    get_blue_model,
    get_blue_provider,
    get_openai_api_key,
    get_red_model,
)
from core.openai_runtime import create_blue_pair, create_openai_pair
from core.utils import chat_with_agent
from guardrails.input_guardrails import detect_injection, topic_filter
from guardrails.output_guardrails import content_filter


PLUGINS = build_production_plugins(max_requests=30, window_seconds=60)
AGENT, RUNNER = create_blue_pair(
    name="vinbank_demo_blue",
    instruction=BLUE_INSTRUCTION,
    app_name="vinbank_demo_blue",
    plugins=PLUGINS,
    temperature=0.35,
)
DEMO_OPENROUTER_MODEL = os.environ.get("OPENROUTER_DEMO_MODEL", f"{get_blue_model()}:free")
FALLBACK_AGENT = FALLBACK_RUNNER = None
if get_openai_api_key():
    FALLBACK_AGENT, FALLBACK_RUNNER = create_openai_pair(
        name="vinbank_demo_fallback",
        instruction=BLUE_INSTRUCTION,
        app_name="vinbank_demo_fallback",
        plugins=PLUGINS,
        model=get_red_model(),
        temperature=0.35,
    )


def offline_reply(message: str) -> str:
    """Safe local answer used only when both providers are unreachable."""
    text = message.lower()
    if any(word in text for word in ("số dư", "balance")):
        return "Bạn có thể kiểm tra số dư trong ứng dụng VinBank tại mục <b>Tài khoản</b>. Vì lý do bảo mật, không gửi mật khẩu hoặc mã OTP trong khung chat."
    if any(word in text for word in ("lãi suất", "tiết kiệm", "interest")):
        return "Bạn có thể xem lãi suất mới nhất tại mục <b>Tiết kiệm</b> trong ứng dụng VinBank. Hãy cho mình biết kỳ hạn bạn quan tâm để được hướng dẫn cụ thể."
    if any(word in text for word in ("chuyển tiền", "chuyển khoản", "transfer")):
        return "Bạn mở <b>Giao dịch</b> → <b>Chuyển tiền</b>, kiểm tra kỹ tên và số tài khoản người nhận rồi xác nhận bằng phương thức bảo mật."
    return "Mình có thể hỗ trợ các câu hỏi về tài khoản, số dư, giao dịch, tiết kiệm, khoản vay và thẻ tín dụng. Kết nối AI đang tạm gián đoạn nên mình đang dùng câu trả lời an toàn cục bộ."



# Patterns for sensitive credential questions the demo must never answer
_SENSITIVE_PATTERNS = [
    r"\b(password|mat\s*khau|mật\s*khẩu|pass\s*word|passwd)\b",
    r"\b(api[\s_-]?key|secret[\s_-]?key|access[\s_-]?token|bearer[\s_-]?token)\b",
    r"\b(db[\s_-]?(host|password|user|pass)|database[\s_-]?(host|password|credentials?))\b",
    r"\b(admin[\s_-]?(password|pass|123)|root[\s_-]?password)\b",
    r"\b(sk-[a-zA-Z0-9\-]{4,})\b",            # literal key pattern
    r"\b(secret|credentials?|khóa\s*bí\s*mật)\b.*\b(vinbank|hệ\s*thống|system)\b",
    r"\b(cho\s+tôi|show|reveal|leak|tiết\s+lộ|lộ)\b.*\b(password|key|secret|mật\s*khẩu)\b",
    r"\b(what|là\s+gì|cho\s+biết)\b.*(password|api.?key|db.?host)\b",
]

import re as _re

def _is_sensitive_question(message: str) -> bool:
    """Return True if the message is asking about passwords, keys, or DB credentials."""
    lower = message.lower()
    for pattern in _SENSITIVE_PATTERNS:
        if _re.search(pattern, lower, _re.IGNORECASE):
            return True
    return False


def blocked_reply(message: str) -> str | None:
    # Block questions about credentials/secrets FIRST
    if _is_sensitive_question(message):
        return (
            "🔒 Tôi không thể cung cấp thông tin về mật khẩu, API key hoặc thông tin "
            "kết nối cơ sở dữ liệu. Đây là thông tin bảo mật tuyệt mật của hệ thống. "
            "Nếu bạn cần hỗ trợ về bảo mật tài khoản cá nhân, vui lòng liên hệ hotline VinBank."
        )
    if detect_injection(message) == "BLOCK":
        return "Mình không thể xử lý yêu cầu này. Mình chỉ hỗ trợ các câu hỏi ngân hàng VinBank an toàn."
    if topic_filter(message) == "BLOCK":
        return "Mình chỉ hỗ trợ các câu hỏi liên quan đến tài khoản, giao dịch, tiết kiệm, khoản vay và thẻ VinBank."
    return None



def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[demo] {self.address_string()} - {fmt % args}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            json_response(self, 200, {
                "ok": True,
                "provider": get_blue_provider(),
                "model": DEMO_OPENROUTER_MODEL,
                "api_key_configured": bool(blue_client_kwargs().get("api_key")),
            })
            return
        if path in ("/", "/index.html"):
            self.serve_file(DEMO / "index.html", "text/html; charset=utf-8")
            return
        if path in ("/styles.css", "/app.js"):
            file_path = DEMO / path.lstrip("/")
            self.serve_file(file_path, "text/css; charset=utf-8" if path.endswith("css") else "application/javascript; charset=utf-8")
            return
        json_response(self, 404, {"error": "Not found"})

    def serve_file(self, file_path: Path, content_type: str):
        if not file_path.is_file() or file_path.parent != DEMO:
            json_response(self, 404, {"error": "Not found"})
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            json_response(self, 404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            try:
                body = json.loads(raw_body.decode("utf-8-sig"))
            except UnicodeDecodeError:
                body = json.loads(raw_body.decode("cp1252"))
            message = str(body.get("message", "")).strip()
            if not message:
                json_response(self, 400, {"error": "Vui lòng nhập câu hỏi."})
                return
            if len(message) > 4000:
                json_response(self, 400, {"error": "Câu hỏi quá dài. Vui lòng rút gọn còn tối đa 4000 ký tự."})
                return
            blocked = blocked_reply(message)
            if blocked:
                json_response(self, 200, {"reply": blocked, "mode": "guardrail"})
                return
            try:
                reply, _ = asyncio.run(chat_with_agent(AGENT, RUNNER, message))
            except Exception as primary_error:
                if getattr(primary_error, "status_code", None) == 404 and not RUNNER.model.endswith(":free"):
                    RUNNER.model = DEMO_OPENROUTER_MODEL
                    print(f"[demo] Using available OpenRouter endpoint: {RUNNER.model}")
                    try:
                        reply, _ = asyncio.run(chat_with_agent(AGENT, RUNNER, message))
                    except Exception as free_error:
                        primary_error = free_error
                if "reply" not in locals():
                    if FALLBACK_AGENT is None:
                        raise primary_error
                    print(f"[demo] OpenRouter unavailable; using OpenAI fallback: {type(primary_error).__name__}")
                    reply, _ = asyncio.run(chat_with_agent(FALLBACK_AGENT, FALLBACK_RUNNER, message))
            filtered = content_filter(reply or "")
            safe_reply = filtered["redacted"] if not filtered["safe"] else (reply or "Mình chưa nhận được phản hồi. Vui lòng thử lại.")
            json_response(self, 200, {"reply": safe_reply})
        except Exception as exc:
            print(f"[demo] providers unavailable; offline response: {type(exc).__name__}")
            json_response(self, 200, {"reply": offline_reply(message), "mode": "offline"})


if __name__ == "__main__":
    port = int(os.environ.get("DEMO_PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoHandler)
    print(f"VinBank demo: http://127.0.0.1:{port}")
    print(f"Provider: {get_blue_provider()} | Model: {DEMO_OPENROUTER_MODEL}")
    server.serve_forever()
