"""MemoryHub Proxy Server — stdlib-only, runs inside Open WebUI container.

Intercepts /api/chat requests, searches MemoryHub for memories,
prepends them to user messages, then forwards to Ollama.
"""
import json
import logging
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MEMORYHUB_URL = "http://memory-hub-app:8000"
WORKSPACE_ID = "5266d746-d1bd-4834-9c3a-3be0f92fe0b0"
OLLAMA_URL = "http://host.docker.internal:11434"


def search_memories(query: str, limit: int = 5) -> list[str]:
    """Search MemoryHub for relevant memories."""
    try:
        data = json.dumps({
            "workspace_id": WORKSPACE_ID,
            "query": query,
            "limit": limit,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{MEMORYHUB_URL}/memories/search",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        if result.get("status") != "success":
            logger.warning(f"Search API status not success: {result.get('error')}")
            return []

        items = []
        for item in result.get("data", {}).get("items", []):
            c = item.get("content", "")
            if c and len(c.strip()) > 10:
                items.append(c.strip())
        logger.info(f"[MemoryHub] Search returned {len(items)} memories for: {query[:60]}...")
        return items[:limit]
    except Exception as e:
        logger.error(f"[MemoryHub] Search error: {e}", exc_info=True)
        return []


def build_context(memories: list[str]) -> str:
    """Build context string from retrieved memories."""
    if not memories:
        return ""
    ctx = "\n\n[Relevant Personal Memories]\n"
    for i, m in enumerate(memories, 1):
        ctx += f"[{i}] {m}\n"
    ctx += "[End Memories]\nUse these as your personal knowledge base when answering."
    return ctx


def inject_memories(body: dict, memories: list[str]) -> dict:
    """Inject memory context into the last user message."""
    messages = body.get("messages", [])
    user_msgs = [m for m in messages if m.get("role") == "user"]
    if not user_msgs:
        return body
    latest_user_msg = user_msgs[-1].get("content", "")
    if not memories:
        return body
    context = build_context(memories)
    modified_messages = list(messages)
    modified_messages[-1]["content"] = latest_user_msg + context
    body["messages"] = modified_messages
    logger.info(f"[MemoryHub] Injected {len(memories)} memories for: {latest_user_msg[:80]}...")
    return body


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(format % args)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "memoryhub-proxy"})
        elif self.path.startswith("/api/"):
            self._proxy_to_ollama()
        else:
            self._send_json({"detail": "Not Found"}, 404)

    def do_POST(self):
        if self.path == "/api/chat":
            self._handle_chat()
        elif self.path.startswith("/v1/chat/completions"):
            self._handle_chat_v1()
        elif self.path.startswith("/api/generate") or self.path.startswith("/api/embed"):
            self._proxy_to_ollama()
        else:
            self._proxy_to_ollama()

    def _handle_chat(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(raw_body.decode("utf-8"))

            messages = body.get("messages", [])
            user_msgs = [m for m in messages if m.get("role") == "user"]
            if user_msgs:
                query = user_msgs[-1].get("content", "")
                memories = search_memories(query)
                body = inject_memories(body, memories)

            self._forward_to_ollama(body)
        except Exception as e:
            logger.error(f"Chat handler error: {e}", exc_info=True)
            self._send_json({"error": str(e)}, 500)

    def _handle_chat_v1(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(raw_body.decode("utf-8"))

            messages = body.get("messages", [])
            user_msgs = [m for m in messages if m.get("role") == "user"]
            if user_msgs:
                query = user_msgs[-1].get("content", "")
                memories = search_memories(query)
                body = inject_memories(body, memories)

            self._forward_to_ollama(body)
        except Exception as e:
            logger.error(f"V1 chat handler error: {e}", exc_info=True)
            self._send_json({"error": str(e)}, 500)

    def _forward_to_ollama(self, body: dict):
        url = f"{OLLAMA_URL}{self.path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": self.headers.get("Accept", "application/json"),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(key, value)
                self.end_headers()
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except urllib.error.HTTPError as e:
            body_bytes = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body_bytes)
        except Exception as e:
            logger.error(f"Forward error: {e}", exc_info=True)
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, obj, status=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _proxy_to_ollama(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length > 0 else None
            url = f"{OLLAMA_URL}{self.path}"
            req = urllib.request.Request(url, data=raw_body, method=self.command)
            with urllib.request.urlopen(req, timeout=120) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers()
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except Exception as e:
            logger.error(f"Proxy error: {e}", exc_info=True)
            self._send_json({"error": str(e)}, 500)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    port = 8765
    server = ThreadedHTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"MemoryHub Proxy running on port {port}")
    print(f"  MemoryHub: {MEMORYHUB_URL}")
    print(f"  Ollama: {OLLAMA_URL}")
    server.serve_forever()
