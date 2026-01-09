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
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from supabase import create_client, Client

from envy.agent import ENVY
from envy.personas.persona_definitions import PERSONAS
from envy.core.config import settings

# ===================================
# Database Setup (Optional)
# ===================================

supabase: Optional[Client] = None
if settings.has_supabase:
    supabase = create_client(settings.supabase_url, settings.supabase_anon_key)

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
    attachments: Optional[List[Dict[str, str]]] = None

# ===================================
# Lifecycle & App
# ===================================

envy_instance: Optional[ENVY] = None
init_error: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n>>> DEPLOYMENT: NO-AUTH v5.0 (Sign-in Disabled) <<<\n")
    global envy_instance, init_error
    
    # Check for API keys
    has_llm = settings.has_groq or settings.has_openrouter
    if not has_llm:
        init_error = "No LLM API key configured! Please set GROQ_API_KEY or OPENROUTER_API_KEY environment variable on Render."
        print(f"[!] WARNING: {init_error}")
        print("[*] Chat will be disabled until API keys are configured.")
    else:
        try:
            envy_instance = ENVY(session_id="production")
            await envy_instance.initialize()
            print("[*] ENVY System: ONLINE")
        except Exception as e:
            init_error = f"Failed to initialize ENVY: {str(e)}"
            print(f"[!] ERROR: {init_error}")
    
    yield
    
    if envy_instance:
        await envy_instance.close()

app = FastAPI(
    title="ENVY API",
    description="Polymorphic Intelligence System",
    version="5.0.0",
    lifespan=lifespan
)

# ===================================
# CORS Middleware
# ===================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================================
# API Routes (No Auth Required)
# ===================================

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy" if envy_instance else "degraded",
        "version": "5.0.0",
        "auth": "disabled",
        "llm_configured": settings.has_groq or settings.has_openrouter,
        "error": init_error
    }

@app.get("/api/status")
async def api_status():
    """Check if the AI is ready"""
    return {
        "ready": envy_instance is not None,
        "error": init_error,
        "groq_configured": settings.has_groq,
        "openrouter_configured": settings.has_openrouter
    }

@app.get("/api/personas")
async def get_personas():
    """Get available personas"""
    return {
        "personas": [
            {
                "id": p.id,
                "name": p.name,
                "title": p.title,
                "avatar": p.avatar
            }
            for p in PERSONAS.values()
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    """Non-streaming chat completion"""
    if not envy_instance:
        error_msg = init_error or "ENVY not initialized. Please configure GROQ_API_KEY or OPENROUTER_API_KEY in Render environment variables."
        raise HTTPException(status_code=503, detail=error_msg)
    
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    user_message = messages[-1]["content"] if messages else ""
    
    try:
        response = await envy_instance.process(user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
    
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response
            },
            "finish_reason": "stop"
        }]
    }

@app.post("/v1/chat/completions/stream")
async def chat_completion_stream(request: ChatRequest):
    """Streaming chat completion (SSE)"""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    user_message = messages[-1]["content"] if messages else ""
    
    async def generate() -> AsyncGenerator[str, None]:
        # Check if ENVY is initialized
        if not envy_instance:
            error_msg = init_error or "ENVY not initialized. Please configure GROQ_API_KEY or OPENROUTER_API_KEY in Render environment variables."
            data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"⚠️ **Configuration Error**\n\n{error_msg}\n\nTo fix this:\n1. Go to Render Dashboard\n2. Navigate to your service\n3. Add environment variable: `OPENROUTER_API_KEY` or `GROQ_API_KEY`\n4. The service will restart automatically"},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(data)}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        try:
            async for chunk in envy_instance.stream(user_message):
                data = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"\n\n⚠️ **Error:** {str(e)}"},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# ===================================
# Static Files & Root Route
# ===================================

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root route - serve chat interface directly (NO SIGN IN)
@app.get("/")
async def root():
    """Serve the main chat interface - NO AUTHENTICATION REQUIRED"""
    return FileResponse("static/index.html")

# Fallback for app.html
@app.get("/app")
async def app_page():
    """Serve the app page"""
    return FileResponse("static/app.html")

# ===================================
# Run Server
# ===================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
