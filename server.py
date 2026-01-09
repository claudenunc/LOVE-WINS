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

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify JWT token from Supabase (Optional for now)"""
    if not credentials:
        return {"id": "anonymous-user", "email": "visitor@foolishnessenvy.com"}
        
    token = credentials.credentials
    if not supabase:
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
    attachments: Optional[List[Dict[str, str]]] = None # [{"type": "image", "url": "..."}]

# ===================================
# API Endpoints
# ===================================

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

# --- File Management (Vision/RAG) ---

@app.post("/api/upload")
async def upload_file(file: Request):
    """Handle file uploads to Supabase Storage"""
    if not supabase:
        raise HTTPException(503, "Database offline")
    
    # Simple multipart parser (FastAPI UploadFile is better but we use Request for raw control)
    form = await file.form()
    uploaded_file = form.get("file")
    
    if not uploaded_file:
        raise HTTPException(400, "No file provided")
    
    # 1. Upload to Supabase Storage 'uploads' bucket
    file_bytes = await uploaded_file.read()
    file_name = f"{int(time.time())}_{uploaded_file.filename}"
    
    try:
        # Ensure bucket exists (would normally do this in migration)
        # supabase.storage.create_bucket("uploads") 
        res = supabase.storage.from_("uploads").upload(file_name, file_bytes)
        
        # Get Public URL
        public_url = supabase.storage.from_("uploads").get_public_url(file_name)
        return {"url": public_url, "name": file_name, "type": uploaded_file.content_type}
        
    except Exception as e:
        # Mock response if storage not set up yet
        print(f"Storage Error (using mock): {e}")
        return {"url": "https://placehold.co/600x400?text=Uploaded+Image", "name": file_name, "type": "mock"}

# --- Subscription (Stripe) ---

STRIPE_ENABLED = False # Set to True when ready to enable payments

@app.post("/api/subscribe")
async def create_checkout(user: dict = Depends(get_current_user)):
    """Create Stripe Checkout Session (Standby Mode)"""
    if not STRIPE_ENABLED:
        return {"url": "#", "message": "Subscription system is in standby mode."}
        
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        return {"url": "#", "error": "Stripe keys not found in environment."}
    
    import stripe
    stripe.api_key = stripe_key
    
    try:
        # Note: You need to create a Price ID in your Stripe Dashboard first
        price_id = os.getenv("STRIPE_PRICE_ID", "price_default")
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.app_url}/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/",
            customer_email=user.get("email"),
            client_reference_id=user.get("id")
        )
        return {"url": session.url}
    except Exception as e:
        return {"url": "#", "error": str(e)}

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
