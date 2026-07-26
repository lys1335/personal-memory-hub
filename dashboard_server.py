"""
Dashboard proxy server.
Serves HTML dashboard on :8080 and proxies API calls to Memory Hub (8000) and Ollama (11434).
Avoids CORS by running everything on same origin.
"""
import http.server
import socketserver
import json
import os
import sys
import urllib.request
import urllib.error

try:
    import requests as req_lib
except ImportError:
    print("Installing requests...")
    os.system(f'{sys.executable} -m pip install requests -q')
    import requests as req_lib

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_HUB = "http://localhost:8000"
OLLAMA = "http://localhost:11434"


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path.startswith('/api/memories'):
            return self._proxy(MEM_HUB, '/api/memories', self.path)
        elif self.path.startswith('/api/sql'):
            return self._proxy(MEM_HUB, '/api', self.path)
        elif self.path.startswith('/api/logs'):
            return self._serve_logs()
        elif self.path.startswith('/api/cron'):
            return self._proxy(MEM_HUB, '/api', self.path)
        elif self.path.startswith('/api/ollama'):
            return self._proxy(OLLAMA, '/api/ollama', self.path)
        # Serve static files
        return self._serve_file()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        if self.path.startswith('/api/memories'):
            return self._proxy(MEM_HUB, '/api/memories', self.path, body)
        elif self.path.startswith('/api/sql'):
            return self._proxy(MEM_HUB, '/api', self.path, body)
        elif self.path.startswith('/api/ollama'):
            return self._proxy(OLLAMA, '/api/ollama', self.path, body)
        elif self.path.startswith('/api/cron'):
            return self._proxy(MEM_HUB, '/api', self.path, body)

        if self.path.startswith('/api/review'):
            return self._proxy(MEM_HUB, '/api', self.path, body)

        self.send_error(404, "Not found")

    def _serve_file(self):
        """Serve static files from dashboard directory."""
        if self.path == '/' or self.path == '':
            self.path = '/dashboard-main.html'
        
        # Strip query string to get clean file path
        clean_path = self.path.split('?')[0]
        filepath = os.path.join(DASHBOARD_DIR, clean_path.lstrip('/'))
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            if filepath.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif filepath.endswith('.css'):
                content_type = 'text/css'
            elif filepath.endswith('.js'):
                content_type = 'application/javascript'
            else:
                content_type = 'application/octet-stream'
            
            with open(filepath, 'rb') as f:
                data = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, f"File not found: {self.path}")

    def _proxy(self, base_url, strip_prefix, request_path=None, body=None):
        path = (request_path or self.path).replace(strip_prefix, '', 1)
        # If we stripped '/api', prepend it back to the URL
        if strip_prefix == '/api':
            url = base_url + '/api' + path
        else:
            url = base_url + path
        
        headers = {}
        ct = self.headers.get('Content-Type')
        if ct:
            headers['Content-Type'] = ct
        
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
                if kl not in ('transfer-encoding', 'connection', 'content-encoding'):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.content)
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")

    def _serve_logs(self):
        """Serve application logs for the Log Viewer tab."""
        import time
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        keyword = params.get('q', [''])[0] if 'q' in params else ''
        level_filter = params.get('level', [''])[0] if 'level' in params else ''
        lines_count = int(params.get('lines', ['-1'])[0])  # -1 = all
        
        log_path = os.path.join(DASHBOARD_DIR, 'logs', 'memory_hub.log')
        
        # Also check common Docker volume paths
        alt_paths = [
            '/app/logs/memory_hub.log',  # Docker container path (for docker exec)
            os.path.expanduser('~/.hermes/memory_hub.log'),
        ]
        
        log_lines = []
        for p in [log_path] + alt_paths:
            try:
                with open(p, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                if lines:
                    log_lines.extend(lines)
                    break  # Use first found
            except FileNotFoundError:
                continue
        
        # Apply filters
        filtered = []
        for line in log_lines:
            line = line.rstrip('\n\r')
            if not line:
                continue
            # Level filter
            if level_filter and level_filter != 'all':
                if f' {level_filter.upper()} ' not in line and not line.endswith(f'"{level_filter.upper()}"'):
                    continue
            # Keyword filter
            if keyword and keyword.lower() not in line.lower():
                continue
            filtered.append(line)
        
        # Line limit (last N lines)
        if lines_count > 0:
            filtered = filtered[-lines_count:]
        
        result = json.dumps({
            'total_lines': len(log_lines),
            'filtered_lines': len(filtered),
            'logs': filtered,
            'keyword': keyword,
            'level': level_filter
        }, ensure_ascii=False)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(result.encode('utf-8'))

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stderr.flush()


# Allow reuse of address
socketserver.TCPServer.allow_reuse_address = True

if __name__ == '__main__':
    port = 8080
    server = http.server.HTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f"Dashboard running at http://localhost:{port}")
    print(f"  /api/memories/* -> {MEM_HUB}")
    print(f"  /api/ollama/*   -> {OLLAMA}")
    print(f"  Static files     -> {DASHBOARD_DIR}")
    server.serve_forever()
