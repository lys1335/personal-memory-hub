"""Dashboard proxy server.

Serves HTML dashboard on :5000 and proxies API calls to Memory Hub (8000) 
and Ollama (11434). Avoids CORS by running everything on same origin.

Usage:
    python dashboard_server.py [--port 5000] [--no-browser]
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.request
import urllib.error
import argparse

try:
    import requests as req_lib
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests as req_lib

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_HUB = "http://localhost:8000"
OLLAMA = "http://localhost:11434"


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path.startswith("/api/memories"):
            target_path = self.path.replace("/api/memories", "/memories", 1)
            target_url = f"{MEM_HUB}{target_path}"
            try:
                resp = req_lib.request(
                    method=self.command,
                    url=target_url,
                    headers=dict(self.headers),
                    timeout=60,
                    allow_redirects=False
                )
                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    kl = k.lower()
                    if kl not in ("transfer-encoding", "connection", "content-encoding"):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.content)
            except Exception as e:
                self.send_error(502, f"Proxy error: {e}")
            return
        
        elif self.path.startswith("/api/sql"):
            return self._proxy(MEM_HUB, "/api", self.path)
        elif self.path.startswith("/api/logs"):
            return self._serve_logs()
        elif self.path.startswith("/api/cron"):
            return self._proxy(MEM_HUB, "/api", self.path)
        elif self.path.startswith("/api/ollama"):
            return self._proxy(OLLAMA, "/api/ollama", self.path)
        
        if self.path.startswith("/api/review"):
            return self._proxy(MEM_HUB, "/api", self.path)
        
        return self._serve_file()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        if self.path.startswith("/api/memories"):
            target_path = self.path.replace("/api/memories", "/memories", 1)
            target_url = f"{MEM_HUB}{target_path}"
            try:
                resp = req_lib.request(
                    method=self.command,
                    url=target_url,
                    data=body,
                    headers=dict(self.headers),
                    timeout=60,
                    allow_redirects=False
                )
                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    kl = k.lower()
                    if kl not in ("transfer-encoding", "connection", "content-encoding"):
                        self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(resp.content)
                    return
            except Exception as e:
                self.send_error(502, f"Proxy error: {e}")
                return
        elif self.path.startswith("/api/sql"):
            return self._proxy(MEM_HUB, "/api", self.path, body)
        elif self.path.startswith("/api/ollama"):
            return self._proxy(OLLAMA, "/api/ollama", self.path, body)
        elif self.path.startswith("/api/cron"):
            return self._proxy(MEM_HUB, "/api", self.path, body)
        
        if self.path.startswith("/api/review"):
            return self._proxy(MEM_HUB, "/api", self.path, body)
        
        self.send_error(404, "Not found")

    def _proxy(self, base_url, strip_prefix, request_path=None, body=None):
        path = (request_path or self.path).replace(strip_prefix, '', 1)
        if strip_prefix == "/api":
            url = base_url + "/api" + path
        else:
            url = base_url + path
        
        headers = {}
        ct = self.headers.get("Content-Type")
        if ct:
            headers["Content-Type"] = ct
        
        try:
            resp = req_lib.request(
                method=self.command,
                url=url,
                data=body,
                headers=headers,
                timeout=60,
                allow_redirects=False
            )
            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                kl = k.lower()
                if kl not in ("transfer-encoding", "connection", "content-encoding"):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.content)
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")
    def _serve_logs(self):
        import time
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        keyword = params.get("q", [""])[0] if "q" in params else ""
        level_filter = params.get("level", [""])[0] if "level" in params else ""
        lines_count = int(params.get("lines", ["-1"])[0])
        
        log_path = os.path.join(DASHBOARD_DIR, "logs", "memory_hub.log")
        alt_paths = ["/app/logs/memory_hub.log", os.path.expanduser("~/.hermes/memory_hub.log")]
        
        log_lines = []
        for p in [log_path] + alt_paths:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                if lines:
                    log_lines.extend(lines)
                    break
            except FileNotFoundError:
                continue
        
        filtered = []
        for line in log_lines:
            line = line.rstrip("\n\r")
            if not line:
                continue
            if level_filter and level_filter != "all":
                if f' {level_filter.upper()} ' not in line and not line.endswith(f'"{level_filter.upper()}"'):
                    continue
            if keyword and keyword.lower() not in line.lower():
                continue
            filtered.append(line)
        
        if lines_count > 0:
            filtered = filtered[-lines_count:]
        
        result = json.dumps({
            "total_lines": len(log_lines),
            "filtered_lines": len(filtered),
            "logs": filtered,
            "keyword": keyword,
            "level": level_filter
        }, ensure_ascii=False)
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(result.encode("utf-8"))
    def _serve_file(self):
        """Serve static files (HTML, CSS, JS, images) from DASHBOARD_DIR."""
        if self.path == "/":
            self.path = "/dashboard-main.html"
        
        file_path = os.path.join(DASHBOARD_DIR, self.path.lstrip("/"))
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(DASHBOARD_DIR)):
            self.send_error(403, "Access denied")
            return
        
        try:
            ext = os.path.splitext(self.path)[1].lower()
            if ext in (".html", ".htm"):
                content_type = "text/html; charset=utf-8"
            elif ext == ".css":
                content_type = "text/css"
            elif ext == ".js":
                content_type = "application/javascript"
            else:
                content_type = "application/octet-stream"
            
            with open(real_path, "rb") as f:
                content_bytes = f.read()
            
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content_bytes)
        except FileNotFoundError:
            self.send_error(404, "File not found")
        except Exception as e:
            self.send_error(500, f"Server error: {e}")
    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stderr.flush()


def start_server(port=5000, open_browser=True):
    server_address = ("0.0.0.0", port)
    server = socketserver.TCPServer(server_address, ProxyHandler)
    server.allow_reuse_address = True
    
    print(f"Dashboard running at http://{port}")
    print(f"  /api/memories/* -> {MEM_HUB}/memories (mapped)")
    print(f"  /api/ollama/*   -> {OLLAMA}")
    print(f"Static files     -> {DASHBOARD_DIR}")
    
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{port}")
            print("[Browser opened successfully]")
        except Exception as e:
            print(f"[⚠] Cannot auto-open browser: {e}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\u1f51c Server shutting down...")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Personal Memory Hub Dashboard")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()
    
    start_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()