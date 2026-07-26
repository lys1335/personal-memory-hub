"""
Open WebUI RAG integration for Personal Memory Hub.
Wraps Memory Hub search API as a simple text retrieval endpoint that OWUI can use.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="Memory Hub RAG Bridge")

MEMORY_HUB_API = os.getenv("MEMORY_HUB_API", "http://localhost:8000")
WORKSPACE_ID = os.getenv("WORKSPACE_ID", "fd0223ed-7aa2-491e-8db5-b0de71b75219")


class QueryRequest(BaseModel):
    query: str
    k: int = 5


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/retrieve")
def retrieve(request: QueryRequest):
    """Retrieve relevant memories for a given query."""
    try:
        # Call Memory Hub search API
        response = requests.post(
            f"{MEMORY_HUB_API}/memories/search",
            json={
                "workspace_id": WORKSPACE_ID,
                "query": request.query,
                "limit": request.k,
                "ranking_approach": "hybrid"
            },
            timeout=10
        )
        data = response.json()
        
        items = data.get("data", {}).get("items", [])
        results = []
        for item in items:
            content = item.get("content", "")
            if content:
                results.append({
                    "content": content,
                    "score": item.get("confidence", 0) or item.get("score", 0),
                    "source": item.get("source", "unknown"),
                    "created_at": item.get("created_at", "")
                })
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8766)
