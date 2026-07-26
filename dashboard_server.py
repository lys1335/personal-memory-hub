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
            return self._proxy(MEM_HUB, '/api')
        elif self.path.startswith('/api/ollama'):
            return self._proxy(OLLAMA, '/api/ollama')
        # Serve static files
        return self._serve_file()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        if self.path.startswith('/api/memories'):
            return self._proxy(MEM_HUB, '/api', body)
        elif self.path.startswith('/api/ollama'):
            return self._proxy(OLLAMA, '/api/ollama', body)
        
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

    def _proxy(self, base_url, strip_prefix, body=None):
        path = self.path.replace(strip_prefix, '', 1)
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
