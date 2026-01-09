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

from envy.agent import ENVY
from envy.personas.persona_definitions import PERSONAS
from envy.core.config import settings

# Import orchestration components
from envy.orchestration.orchestrator import Orchestrator
from envy.orchestration.knowledge_spine import KnowledgeSpine
from envy.orchestration.protocols import TaskEnvelope

# ===================================
# Database Setup (Optional)
# ===================================

supabase = None
try:
    from supabase import create_client, Client
    if settings.has_supabase:
        supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
except ImportError:
    print("[!] Supabase not installed - database features disabled (optional)")

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

class BlueprintRequest(BaseModel):
    """Request to execute Architect → Builder → Scribe pipeline"""
    blueprint_type: str = Field(..., description="n8n_workflow, website, app, automation, etc.")
    name: str = Field(..., description="Name of the thing to build")
    description: str = Field(..., description="What it should do")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Additional requirements")
    project_id: Optional[str] = Field(default="default", description="Project ID for context")

class BlueprintResponse(BaseModel):
    """Response from blueprint execution"""
    success: bool
    project_id: str
    task_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attachments: Optional[List[Dict[str, str]]] = None

# ===================================
# Lifecycle & App
# ===================================

envy_instance: Optional[ENVY] = None
orchestrator_instance: Optional[Orchestrator] = None
knowledge_spine: Optional[KnowledgeSpine] = None
init_error: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n>>> DEPLOYMENT: NO-AUTH v5.0 (Sign-in Disabled) <<<\n")
    global envy_instance, orchestrator_instance, knowledge_spine, init_error
    
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
            
            # Initialize multi-agent orchestration system
            knowledge_spine = KnowledgeSpine(base_path="./memory/knowledge_spine")
            orchestrator_instance = Orchestrator(envy_instance.llm, knowledge_spine)
            print("[*] Multi-Agent Orchestrator: ONLINE")
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

@app.get("/api/validate-key")
async def validate_api_key():
    """Validate that the API key works by making a test call"""
    if not envy_instance:
        return {
            "valid": False,
            "error": init_error or "ENVY not initialized",
            "fix": "Set GROQ_API_KEY or OPENROUTER_API_KEY environment variable"
        }
    
    try:
        # Make a minimal test call to verify the API key works
        test_response = await envy_instance.process("test")
        return {
            "valid": True,
            "provider": "groq" if settings.has_groq else "openrouter",
            "model": settings.groq_model if settings.has_groq else settings.openrouter_model
        }
    except Exception as e:
        error_str = str(e)
        fix_message = "Unknown error"
        
        if "401" in error_str or "Unauthorized" in error_str:
            fix_message = "API key is invalid. Get a new one from https://console.groq.com/keys or https://openrouter.ai/keys"
        elif "No address" in error_str or "connection" in error_str.lower():
            fix_message = "Cannot reach API server. Check internet connection or try again later."
        elif "429" in error_str or "rate limit" in error_str.lower():
            fix_message = "Rate limit exceeded. Wait and try again or use a different API key."
        else:
            fix_message = f"Error: {error_str}"
        
        return {
            "valid": False,
            "error": error_str,
            "fix": fix_message
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
            error_str = str(e)
            error_msg = f"⚠️ **Error:** {error_str}\n\n"
            
            # Provide specific troubleshooting based on error type
            if "401" in error_str or "Unauthorized" in error_str or "authentication" in error_str.lower():
                error_msg += "**Cause:** Invalid API key\n\n"
                error_msg += "**Fix:**\n"
                error_msg += "1. Get a FREE Groq API key from: https://console.groq.com/keys\n"
                error_msg += "2. On Render: Dashboard → Your Service → Environment → Add `GROQ_API_KEY`\n"
                error_msg += "3. Or try OpenRouter: Get key from https://openrouter.ai/keys → Set `OPENROUTER_API_KEY`\n"
            elif "No address" in error_str or "connection" in error_str.lower() or "timeout" in error_str.lower():
                error_msg += "**Cause:** Cannot reach LLM API (network/DNS issue)\n\n"
                error_msg += "**Fix:**\n"
                error_msg += "1. Check your internet connection\n"
                error_msg += "2. Verify Groq/OpenRouter services are up (status pages)\n"
                error_msg += "3. On Render: Check service logs for network errors\n"
                error_msg += "4. Wait a few minutes and try again\n"
            elif "429" in error_str or "rate limit" in error_str.lower():
                error_msg += "**Cause:** Rate limit exceeded\n\n"
                error_msg += "**Fix:**\n"
                error_msg += "1. Groq free tier: 14,400 requests/day limit\n"
                error_msg += "2. Wait for rate limit to reset (usually 24 hours)\n"
                error_msg += "3. Or switch to OpenRouter API (different limits)\n"
            else:
                error_msg += "**Troubleshooting:**\n"
                error_msg += "1. Check server logs for details\n"
                error_msg += "2. Verify API key is valid: `echo $GROQ_API_KEY`\n"
                error_msg += "3. See TROUBLESHOOTING.md for more help\n"
            
            error_data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": error_msg},
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
# Blueprint Execution API
# ===================================

@app.post("/api/blueprint/execute", response_model=BlueprintResponse)
async def execute_blueprint(request: BlueprintRequest):
    """
    Execute the Architect → Builder → Scribe pipeline to create something.
    
    This is the unified creation endpoint that orchestrates multi-agent workflows.
    """
    if not orchestrator_instance or not envy_instance:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialized. Please configure API keys."
        )
    
    try:
        # Create or get project
        project_id = request.project_id or "default"
        
        # Check if project exists, create if not
        existing_project = orchestrator_instance.spine.get_project(project_id)
        if not existing_project:
            project_id = await orchestrator_instance.create_project(
                name=request.name,
                mission=request.description
            )
        
        # Build instruction based on blueprint type
        instruction = _build_blueprint_instruction(
            request.blueprint_type,
            request.name,
            request.description,
            request.requirements
        )
        
        # Create task envelope for Architect
        task = TaskEnvelope(
            origin="human",
            project_id=project_id,
            instruction=instruction,
            expected_output_type="spec",
            downstream_agent="architect",
            priority="high"
        )
        
        # Submit to orchestrator (Architect → Builder → Scribe happens automatically)
        task_id = await orchestrator_instance.submit_task(task)
        
        # Get results from Knowledge Spine
        project_status = orchestrator_instance.get_project_status(project_id)
        
        return BlueprintResponse(
            success=True,
            project_id=project_id,
            task_id=task_id,
            result={
                "status": "Pipeline executing",
                "project": project_status,
                "message": f"Creating {request.blueprint_type}: {request.name}"
            }
        )
        
    except Exception as e:
        return BlueprintResponse(
            success=False,
            project_id=request.project_id or "unknown",
            task_id="error",
            error=str(e)
        )


def _build_blueprint_instruction(
    blueprint_type: str,
    name: str,
    description: str,
    requirements: Dict[str, Any]
) -> str:
    """Build instruction for the Architect based on blueprint type"""
    
    if blueprint_type == "n8n_workflow":
        return f"""Design an n8n workflow: {name}

Description: {description}

Requirements:
{json.dumps(requirements, indent=2)}

Please create a complete n8n workflow specification including:
1. Trigger nodes (webhook, schedule, etc.)
2. Processing nodes (ENVY agents, transformations)
3. Action nodes (send email, update database, etc.)
4. Error handling
5. Connection map between all nodes

Output the workflow as JSON compatible with n8n import."""
    
    elif blueprint_type == "website":
        return f"""Design a website: {name}

Description: {description}

Requirements:
{json.dumps(requirements, indent=2)}

Please create a complete website specification including:
1. Page structure and routes
2. Design style and components
3. Technology stack (HTML/CSS/JS or React/Vue/etc.)
4. Content for each page
5. Navigation structure

Prepare specs for the Builder to implement."""
    
    elif blueprint_type == "app":
        return f"""Design an application: {name}

Description: {description}

Requirements:
{json.dumps(requirements, indent=2)}

Please create a complete application specification including:
1. Architecture (frontend, backend, database)
2. Features and user flows
3. API endpoints if applicable
4. Database schema if needed
5. Tech stack recommendations

Prepare detailed specs for implementation."""
    
    else:
        return f"""Design and create: {name}

Type: {blueprint_type}
Description: {description}

Requirements:
{json.dumps(requirements, indent=2)}

Please analyze and create appropriate specifications."""


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
