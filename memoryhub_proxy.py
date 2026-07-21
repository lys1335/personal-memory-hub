"""MemoryHub Proxy Server — stdlib-only HTTP proxy.

Intercepts /api/chat POST requests, searches MemoryHub for relevant memories,
prepends context to the request body, then forwards to Ollama.
All other requests are forwarded transparently.
"""
import json
import logging
import os
import re
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MEMORYHUB_URL = os.getenv("MEMORYHUB_URL", "http://memory-hub-app:8000")
WORKSPACE_ID = os.getenv("WORKSPACE_ID", "5266d746-d1bd-4834-9c3a-3be0f92fe0b0")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
PORT = int(os.getenv("PORT", "8765"))
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "5"))


def search_memories(query: str, limit: int = SEARCH_LIMIT) -> list[str]:
    """Search MemoryHub for relevant memories using vector + keyword fallback."""
    # Step 1: Try vector search first
    vector_results = _vector_search(query, limit)
    if vector_results:
        logger.info(f"[MemoryHub] Vector search returned {len(vector_results)} memories for: {query[:60]}...")
        return vector_results

    # Step 2: Fallback to keyword search across all memories
    logger.info(f"[MemoryHub] Vector search returned 0 for '{query[:60]}...', trying keyword fallback...")
    keyword_results = _keyword_search(query, limit)
    if keyword_results:
        logger.info(f"[MemoryHub] Keyword fallback returned {len(keyword_results)} memories")
        return keyword_results

    logger.info(f"[MemoryHub] Search returned 0 memories for: {query[:60]}...")
    return []


def _vector_search(query: str, limit: int) -> list[str]:
    """Try MemoryHub vector search API."""
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
        return items[:limit]
    except Exception as e:
        logger.error(f"[MemoryHub] Vector search error: {e}", exc_info=True)
        return []


def _keyword_search(query: str, limit: int) -> list[str]:
    """Fallback keyword search by fetching all memories and matching terms."""
    try:
        # Fetch ALL memories in workspace using a broad query like '%'
        data = json.dumps({
            "workspace_id": WORKSPACE_ID,
            "query": "%",
            "limit": 200,
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
            return []

        all_items = result.get("data", {}).get("items", [])
        if not all_items:
            return []

        # Extract meaningful keywords from query (remove common words, keep nouns/terms)
        keywords = _extract_keywords(query)
        if not keywords:
            return []

        scored = []
        for item in all_items:
            content = item.get("content", "")
            if not content or len(content.strip()) <= 10:
                continue

            # Count keyword matches in content
            hits = sum(1 for kw in keywords if kw.lower() in content.lower())
            if hits > 0:
                scored.append((hits, content.strip()))

        # Sort by hit count descending, return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]

    except Exception as e:
        logger.error(f"[MemoryHub] Keyword search error: {e}", exc_info=True)
        return []


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from query for fallback text search.

    Handles mixed Chinese/ASCII queries by splitting into CJK runs and
    ASCII runs separately, so "儿童NISA的投资额度是多少？" yields
    ["儿童", "nisa", "投资额度", "多少"] instead of one huge token.
    """
    # Split into runs of CJK, runs of ASCII+digit, and punctuation
    chunks = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', query)

    stop_words = {
        "的", "了", "是", "在", "有", "和", "就", "不", "都",
        "也", "很", "吗", "呢", "吧", "什么", "怎么", "如何",
        "多少", "能", "可以", "请", "帮我", "我想", "请问",
        "the", "is", "are", "was", "were", "have", "has",
        "a", "an", "and", "or", "but", "if", "of", "in", "on", "at",
        "to", "for", "with", "about", "this", "that", "my", "your",
        "what", "which", "who", "when", "where", "why", "how",
    }

    keywords = []
    for chunk in chunks:
        lower = chunk.lower()
        if lower in stop_words:
            continue
        if len(chunk) == 0:
            continue
        # For long CJK runs (>6 chars), extract overlapping 2-char bigrams
        # so that multi-word queries still produce searchable terms.
        if all('\u4e00' <= c <= '\u9fff' for c in chunk):
            if len(chunk) <= 6:
                keywords.append(lower)
            else:
                for i in range(len(chunk) - 1):
                    bg = chunk[i:i+2]
                    if bg not in stop_words:
                        keywords.append(bg)
        else:
            keywords.append(lower)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def extract_user_query(body: dict) -> str:
    """Extract the latest user message content from a chat request body."""
    messages = body.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    # Fallback: look for chat field
    if "chat" in body:
        return body["chat"]
    return ""


def inject_memories(body: dict) -> dict:
    """Search MemoryHub and inject context into the request body."""
    query = extract_user_query(body)
    if not query:
        return body

    memories = search_memories(query)
    if not memories:
        logger.info(f"[MemoryHub] No memories found for query: {query[:80]}")
        return body

    context = build_context(memories)
    logger.info(f"[MemoryHub] Injecting {len(memories)} memories into query: {query[:60]}...")
    logger.info(f"[MemoryHub] Context length: {len(context)} chars")
    
    # Inject into preamble/system FIRST (highest priority for small models)
    if "preamble" in body:
        body["preamble"] = context + "\n" + body["preamble"]
    elif "system" in body:
        body["system"] = context + "\n" + body["system"]
    else:
        # If no system/preamble, prepend to first message
        messages = body.get("messages", [])
        if messages:
            messages[0]["content"] = context + "\n" + messages[0].get("content", "")
    
    # Also append to last user message for reinforcement
    if messages:
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                current_content = messages[i].get("content", "")
                messages[i]["content"] = current_content + context
                break

    return body


def build_context(memories: list[str]) -> str:
    """Build context string from retrieved memories — optimized for small models."""
    if not memories:
        return ""
    # Extract key facts into a compact, model-friendly format
    ctx = "\n\n[PERSONAL MEMORY DATABASE]\n"
    for i, m in enumerate(memories, 1):
        lines = [l.strip() for l in m.split('\n') if l.strip()]
        summary = lines[0][:200] if lines else m[:200]
        ctx += f"[MEMORY {i}] {summary}\n"
    ctx += "[END MEMORY DATABASE]\n"
    ctx += "CRITICAL RULE: You MUST use the above personal memory database when answering questions about the user's life, investments, NISA, funds, family, or personal preferences. Do NOT make up information. If the answer is in the memory database, quote it directly.\n"
    return ctx


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _proxy_to_ollama(self, method, path, headers, body):
        """Forward request to Ollama with streaming support."""
        target_url = f"{OLLAMA_URL}{path}"
        # Build headers without Host/Content-Length to avoid conflicts
        clean_headers = {}
        for key, value in headers.items():
            if key.lower() not in ("host", "content-length"):
                clean_headers[key] = value
        req = urllib.request.Request(target_url, data=body, headers=clean_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                status = resp.status
                # Get content type
                content_type = resp.getheader("Content-Type", "application/json")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                # Stream response in chunks to preserve SSE behavior
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_body)
        except Exception as e:
            logger.error(f"Proxy error: {e}", exc_info=True)
            self.send_error(502, f"Proxy error: {e}")

    def do_GET(self):
        """GET requests are forwarded to Ollama unchanged, with /api/models -> /api/tags mapping."""
        path = self.path
        if path == "/api/models":
            path = "/api/tags"
        self._proxy_to_ollama("GET", path, self.headers, None)

    def do_POST(self):
        """POST requests: intercept /api/chat to inject MemoryHub context."""
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                request_body = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._proxy_to_ollama("POST", self.path, self.headers, body)
                return

            request_body = inject_memories(request_body)
            modified_body = json.dumps(request_body).encode("utf-8")
            
            # DEBUG: log what was injected
            messages_after = request_body.get("messages", [])
            for i, msg in enumerate(messages_after):
                if msg.get("role") == "user" and "[Relevant Personal Memories]" in msg.get("content", ""):
                    logger.info(f"[MemoryHub] Injected context into message {i}, length: {len(msg['content'])}")
                    break

            # Update Content-Length
            new_headers = {}
            for key, value in self.headers.items():
                if key.lower() == "content-length":
                    new_headers[key] = str(len(modified_body))
                else:
                    new_headers[key] = value

            self._proxy_to_ollama("POST", self.path, new_headers, modified_body)
        else:
            # All other POST requests forwarded unchanged
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self._proxy_to_ollama("POST", self.path, self.headers, body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    logger.info(f"Starting MemoryHub Proxy on port {PORT}")
    logger.info(f"MemoryHub URL: {MEMORYHUB_URL}")
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    logger.info(f"Workspace ID: {WORKSPACE_ID}")

    server = ThreadedHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    logger.info("Server started")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()
