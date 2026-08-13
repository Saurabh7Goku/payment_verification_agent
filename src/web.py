"""FastAPI web server for the Payment Collection Agent."""

import sys
import uuid
import os
from pathlib import Path

# Ensure project root is on sys.path so 'from src.agent import ...' always works
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Force reload environment variables on every server start
# This ensures .env changes are picked up even with auto-reload
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from src.agent import Agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - runs on startup and shutdown."""
    # Startup
    api_key = os.getenv("OPENROUTER_API_KEY", "NOT_SET")
    print("\n" + "=" * 80)
    print("SERVER STARTUP")
    print("=" * 80)
    if api_key and api_key != "NOT_SET":
        print(f"✓ API Key loaded: {api_key[:20]}...{api_key[-10:]}")
    else:
        print("✗ No API key found in environment!")
    print("=" * 80 + "\n")
    
    yield  # Server runs
    
    # Shutdown (if needed)
    print("Server shutting down...")


app = FastAPI(title="Payment Collection Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, Agent] = {}

STATIC_DIR = Path(__file__).parent.parent / "static"


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    state: str
    session_id: str


class ResetResponse(BaseModel):
    status: str
    session_id: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or uuid.uuid4().hex[:12]

    if session_id not in sessions:
        sessions[session_id] = Agent()

    agent = sessions[session_id]
    result = agent.next(req.message)

    return ChatResponse(
        response=result["message"],
        state=agent.state.current_state.value,
        session_id=session_id,
    )


@app.get("/api/session/{session_id}/reset", response_model=ResetResponse)
def reset_session(session_id: str) -> ResetResponse:
    sessions[session_id] = Agent()
    return ResetResponse(status="ok", session_id=session_id)


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def run(reload: bool = True):
    """
    Run the FastAPI server.
    
    Args:
        reload: Enable auto-reload on code changes (default: True for development)
    """
    import uvicorn
    uvicorn.run(
        "src.web:app",  # Use string format for reload to work properly
        host="0.0.0.0",
        port=8000,
        reload=reload,
        reload_dirs=["src", "static"],  # Watch these directories for changes
        log_level="info"
    )


if __name__ == "__main__":
    run(reload=True)
