"""Add dashboard and ollama proxy endpoints to app.py"""
import sys
from pathlib import Path

# Read the original file
app_path = Path(r"F:\LI_YONGSHUN\AI\personal-memory-hub\backend\src\backend\app.py")
content = app_path.read_text(encoding="utf-8")

# Check if imports already exist
if "from fastapi.responses import HTMLResponse" not in content:
    # Add HTMLResponse import
    content = content.replace(
        "from fastapi.responses import HTMLResponse",
        "from fastapi.responses import HTMLResponse, Response"
    )

# Check if Request import already exists
if "from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request" not in content:
    content = content.replace(
        "from fastapi import Body, Depends, FastAPI, HTTPException, Query",
        "from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request"
    )

# Add new endpoints before the if __name__ block
new_endpoints = '''

@app.get("/dashboard")
async def serve_dashboard():
    """Serve the main dashboard HTML file."""
    dashboard_path = Path("/app/dashboard-main.html")
    if dashboard_path.exists():
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/dashboard-main.html")
async def serve_dashboard_html():
    """Serve the dashboard HTML file."""
    dashboard_path = Path("/app/dashboard-main.html")
    if dashboard_path.exists():
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.api_route("/api/ollama/{path:path}", methods=["GET", "POST"])
async def proxy_ollama(request: Request, path: str):
    """Proxy requests to local Ollama server."""
    import httpx
    from backend.shared.infrastructure.config.settings import get_settings
    _settings = get_settings()
    ollama_url = _settings.OLLAMA_BASE_URL.rstrip('/')
    target_url = f"{ollama_url}/{path}"
    
    # Forward headers
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ('host', 'content-length')}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Read body for POST
        body = None
        if request.method == "POST":
            body = await request.body()
        
        resp = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        )
        
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers)
        )

'''

# Insert before the if __name__ block
if 'if __name__ == "__main__":' in content:
    content = content.replace(
        'if __name__ == "__main__":',
        new_endpoints + '\nif __name__ == "__main__":'
    )
else:
    # Append at the end
    content += new_endpoints

# Write back
app_path.write_text(content, encoding="utf-8")
print("✅ Endpoints added successfully")
