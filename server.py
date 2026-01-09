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
    """Bypass Auth for Founder Mode"""
    return {"id": "founder", "email": "nathan@foolishnessenvy.com"}

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
# Lifecycle & App
# ===================================

envy_instance: Optional[ENVY] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n>>> DEPLOYMENT: NO-AUTH v4.0 (Cache Buster) <<<\n")
    global envy_instance
    envy_instance = ENVY(session_id="production")
    await envy_instance.initialize()
    print("[*] ENVY System: ONLINE")
    yield
    if envy_instance:
        await envy_instance.close()
