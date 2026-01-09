#!/usr/bin/env python3
"""
ENVY FastAPI Server
===================
REST API and OpenAI-compatible endpoint for ENVY.

Compatible with Open WebUI and any OpenAI-compatible client.

Usage:
    python server.py
    
    # Or with uvicorn directly:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import json
import time
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from envy.agent import ENVY
from envy.personas.persona_definitions import PERSONAS
from envy.core.config import settings


# ===================================
# Pydantic Models (OpenAI-compatible)
# ===================================

class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "envy"
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False
    # ENVY-specific options
    persona: Optional[str] = None
    use_reflexion: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = "envy-response"
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "envy"
    choices: List[ChatCompletionChoice]
    usage: Usage


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "envy"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# ===================================
# FastAPI App
# ===================================

# Global ENVY instance
envy_instance: Optional[ENVY] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage ENVY lifecycle"""
    global envy_instance
    envy_instance = ENVY(session_id="api")
    await envy_instance.initialize()
    print("[*] ENVY Server initialized")
    yield
    if envy_instance:
        await envy_instance.close()
    print("[*] ENVY Server shutdown")


app = FastAPI(
    title="ENVY API",
    description="Self-Improving AI with 9 Expert Personas",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ===================================
# OpenAI-Compatible Endpoints
# ===================================

@app.get("/v1/models")
@app.get("/models")
async def list_models() -> ModelsResponse:
    """List available models (all personas + base ENVY)"""
    models = [
        ModelInfo(id="envy", owned_by="envy"),
        ModelInfo(id="envy-reflexion", owned_by="envy"),
    ]
    
    # Add each persona as a "model"
    for persona_id, persona in PERSONAS.items():
        models.append(ModelInfo(
            id=f"envy-{persona_id}",
            owned_by="envy"
        ))
    
    return ModelsResponse(data=models)


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """OpenAI-compatible chat completions endpoint"""
    global envy_instance
    
    if not envy_instance:
        raise HTTPException(status_code=503, detail="ENVY not initialized")
    
    # Extract last user message
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    # Parse persona from model name (e.g., "envy-jocko" -> "jocko")
    persona = request.persona
    use_reflexion = request.use_reflexion
    
    if request.model.startswith("envy-"):
        model_suffix = request.model[5:]  # Remove "envy-"
        if model_suffix == "reflexion":
            use_reflexion = True
        elif model_suffix in PERSONAS:
            persona = model_suffix
    
    # Chat with ENVY
    try:
        response = await envy_instance.chat(
            message=user_message,
            use_reflexion=use_reflexion,
            force_persona=persona
        )
        
        # Build response
        return ChatCompletionResponse(
            id=f"envy-{int(time.time())}",
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content=response.content),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                total_tokens=response.tokens_used
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions/stream")
async def chat_completions_stream(request: ChatCompletionRequest):
    """Streaming chat completions (SSE)"""
    global envy_instance
    
    if not envy_instance:
        raise HTTPException(status_code=503, detail="ENVY not initialized")
    
    # For now, simulate streaming by chunking the response
    # TODO: Implement true streaming from LLM
    
    async def generate():
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        if not user_message:
            yield f"data: {json.dumps({'error': 'No user message'})}\n\n"
            return
        
        try:
            response = await envy_instance.chat(user_message)
            
            # Chunk the response
            content = response.content
            chunk_size = 20  # Characters per chunk
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                data = {
                    "id": f"envy-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(0.02)  # Small delay between chunks
            
            # Send done signal
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# ===================================
# ENVY-Specific Endpoints
# ===================================

@app.get("/sw.js")
async def service_worker():
    """Serve service worker from root to ensure correct scope"""
    return FileResponse("static/sw.js", media_type="application/javascript")


@app.get("/manifest.json")
async def manifest():
    """Serve PWA manifest"""
    return FileResponse("static/manifest.json", media_type="application/json")


@app.get("/")
async def root():
    """Serve the static chat interface"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "initialized": envy_instance is not None,
        "timestamp": int(time.time())
    }


@app.get("/personas")
async def list_personas():
    """List all available personas with details"""
    return {
        "personas": [
            {
                "id": p.id,
                "name": p.name,
                "title": p.title,
                "expertise": p.expertise,
                "style": p.communication_style,
                "color": p.color
            }
            for p in PERSONAS.values()
        ]
    }


@app.get("/personas/{persona_id}")
async def get_persona(persona_id: str):
    """Get details for a specific persona"""
    if persona_id not in PERSONAS:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    p = PERSONAS[persona_id]
    return {
        "id": p.id,
        "name": p.name,
        "title": p.title,
        "expertise": p.expertise,
        "communication_style": p.communication_style,
        "trigger_keywords": p.trigger_keywords,
        "example_phrases": p.example_phrases,
        "color": p.color
    }


@app.get("/stats")
async def get_stats():
    """Get usage statistics"""
    global envy_instance
    
    if not envy_instance:
        raise HTTPException(status_code=503, detail="ENVY not initialized")
    
    return envy_instance.get_usage_stats()


class RememberRequest(BaseModel):
    content: str
    category: str = "user_note"


@app.post("/memory/remember")
async def remember(request: RememberRequest):
    """Store something in ENVY's memory"""
    global envy_instance
    
    if not envy_instance:
        raise HTTPException(status_code=503, detail="ENVY not initialized")
    
    await envy_instance.remember(request.content, request.category)
    return {"status": "stored", "content": request.content[:100]}


class RecallRequest(BaseModel):
    query: str
    limit: int = 5


@app.post("/memory/recall")
async def recall(request: RecallRequest):
    """Search ENVY's memory"""
    global envy_instance
    
    if not envy_instance:
        raise HTTPException(status_code=503, detail="ENVY not initialized")
    
    results = await envy_instance.recall(request.query)
    return {"query": request.query, "results": results}


# ===================================
# Main Entry Point
# ===================================

if __name__ == "__main__":
    import os
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    display_host = "localhost" if host == "0.0.0.0" else host
    print(f"""
+---------------------------------------------------------------+
|                                                               |
|   ENVY API Server                                             |
|                                                               |
|   Chat Interface:                                             |
|   http://{display_host}:{port}/                                         |
|                                                               |
|   API Documentation:                                          |
|   http://{display_host}:{port}/docs                                     |
|                                                               |
+---------------------------------------------------------------+
""")
    
    uvicorn.run(app, host=host, port=port)
