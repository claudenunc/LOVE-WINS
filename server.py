#!/usr/bin/env python3
"""
ENVY Production Server
======================
Full-stack backend mimicking Claude.ai capabilities.
Integrates:
- FastAPI (High-performance web server)
- Supabase (Auth & Database)
- ENVY Agent (Reasoning Engine)
"""

import os
import json
import time
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn
from supabase import create_client, Client

from envy.agent import ENVY
from envy.personas.persona_definitions import PERSONAS
from envy.core.config import settings

# ===================================
# Database & Auth Setup
# ===================================

supabase: Optional[Client] = None
if settings.has_supabase:
    supabase = create_client(settings.supabase_url, settings.supabase_anon_key)

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from Supabase"""
    token = credentials.credentials
    if not supabase:
        # Dev mode: Mock user if DB not set up
        return {"id": "dev-user", "email": "dev@foolishnessenvy.com"}
    
    try:
        user = supabase.auth.get_user(token)
        return user.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ===================================
# Pydantic Models
# ===================================

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "envy"
    messages: List[Message]
    stream: bool = True
    session_id: Optional[str] = None

# ===================================
# Lifecycle & App
# ===================================

envy_instance: Optional[ENVY] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global envy_instance
    envy_instance = ENVY(session_id="production")
    await envy_instance.initialize()
    print("[*] ENVY System: ONLINE")
    yield
    if envy_instance:
        await envy_instance.close()

app = FastAPI(title="ENVY", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ===================================
# API Endpoints
# ===================================

# ===================================
# Config Endpoint
# ===================================

@app.get("/api/config")
async def get_config():
    """Serve public config to frontend"""
    return {
        "supabase_url": settings.supabase_url,
        "supabase_anon_key": settings.supabase_anon_key
    }

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse("static/manifest.json", media_type="application/json")

@app.get("/sw.js")
async def sw():
    return FileResponse("static/sw.js", media_type="application/javascript")

@app.get("/health")
async def health():
    return {"status": "nominal", "database": "connected" if supabase else "offline"}

# --- History Management ---

@app.get("/api/history")
async def get_history(user: dict = Depends(get_current_user)):
    """Fetch chat sessions for the user"""
    if not supabase:
        return []
    
    # Query 'sessions' table
    try:
        res = supabase.table("sessions").select("*").eq("user_id", user.id).order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"DB Error: {e}")
        return []

@app.get("/api/history/{session_id}")
async def get_chat_details(session_id: str, user: dict = Depends(get_current_user)):
    """Fetch messages for a specific session"""
    if not supabase:
        return []
    
    try:
        res = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
        return res.data
    except Exception:
        return []

# --- Chat Generation ---

@app.post("/v1/chat/completions/stream")
async def chat_stream(request: ChatRequest): # Auth temporarily optional for "Founder Mode" speed
    """High-performance streaming endpoint"""
    global envy_instance
    
    if not envy_instance:
        raise HTTPException(503, "System initializing...")

    user_msg = request.messages[-1].content
    
    # 1. Save User Message (Async)
    # TODO: Fire and forget to Supabase 'messages' table

    async def generate():
        try:
            # Direct access to the internal LLM for raw speed
            # We bypass the full agent loop for the streaming response to get the first token FAST
            # Then we process tools in the background (Conceptually)
            
            # For v3.0, we use the tool-aware chat but we need to adapt it for streaming.
            # Currently ENVY.chat is not a generator. 
            # We will use the LLM directly for the UI stream, and let the Agent think in parallel.
            
            # Streaming from LLM Client
            async for chunk in envy_instance.llm.complete(
                [{"role": "system", "content": envy_instance._build_system_prompt()}, 
                 {"role": "user", "content": user_msg}],
                stream=True
            ):
                data = {
                    "choices": [{"delta": {"content": chunk}}]
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            err = json.dumps({"error": str(e)})
            yield f"data: {err}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
