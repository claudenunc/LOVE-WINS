#!/usr/bin/env python3
"""
ENVY Production Server v6.0
===========================
Full-stack backend with Claude.ai-like capabilities:
- File Upload (documents, images, code)
- MCP Integration (connectors, tools, SSE)
- Agent Spawner (multi-agent orchestration)
- Artifacts UI support
- NO authentication required

Integrates:
- FastAPI (High-performance web server)
- Supabase (Database - optional)
- ENVY Agent (Reasoning Engine)
- MCP Client (Model Context Protocol)
- File Handler (Multi-format processing)
- Agent Spawner (Sub-agent orchestration)
"""

import os
import json
import time
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Optional Supabase
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# ENVY Core
from envy.agent import ENVY
from envy.personas.persona_definitions import PERSONAS
from envy.core.config import settings

# ENVY Capabilities
from envy.capabilities.file_handler import FileHandler, FileType, get_file_handler
from envy.capabilities.connector_registry import ConnectorRegistry, get_connector_registry, ConnectorType
from envy.capabilities.mcp_client_enhanced import EnhancedMCPClient, get_mcp_client
from envy.capabilities.agent_spawner import AgentSpawner, get_agent_spawner, AgentStatus

# ENVY Projects (Phase 1.1)
from envy.projects import ProjectManager, Project, ProjectSettings, FileTree, get_project_manager

# ENVY Memory (Phase 1.2 & 1.3)
from envy.memory import (
    VectorStore, RAGPipeline, get_vector_store, get_rag_pipeline,
    UserProfile, UserProfileManager, UserPreferences, StyleProfile, Tone, get_profile_manager
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
    attachments: Optional[List[str]] = None  # List of file IDs

class ConnectorCredentials(BaseModel):
    credentials: Dict[str, str] = {}

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class SpawnAgentRequest(BaseModel):
    role: str
    task: str
    context: Optional[Dict[str, Any]] = None

class CustomBlueprintRequest(BaseModel):
    name: str
    system_prompt: str
    tools: List[str] = []
    max_iterations: int = 5
    task: str = ""
    context: Optional[Dict[str, Any]] = None

# Project Models (Phase 1.1)
class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class AddFileRequest(BaseModel):
    path: str
    content: str
    mime_type: str = "text/plain"
    metadata: Optional[Dict[str, Any]] = None

class UpdateContextRequest(BaseModel):
    file_paths: List[str]

# User Profile Models (Phase 1.3)
class UpdateUserProfileRequest(BaseModel):
    name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    writing_style: Optional[Dict[str, Any]] = None
    active_project_id: Optional[str] = None

class AddFactRequest(BaseModel):
    fact: str

class AddLearningRequest(BaseModel):
    content: str
    category: str = "general"
    confidence: float = 0.8
    source: str = "explicit"

# ===================================
# Global State
# ===================================

supabase: Optional[Client] = None
envy_instance: Optional[ENVY] = None
init_error: Optional[str] = None
file_handler: Optional[FileHandler] = None
mcp_client: Optional[EnhancedMCPClient] = None
connector_registry: Optional[ConnectorRegistry] = None
agent_spawner: Optional[AgentSpawner] = None
project_manager: Optional[ProjectManager] = None
profile_manager: Optional[UserProfileManager] = None
vector_store: Optional[VectorStore] = None
rag_pipeline: Optional[RAGPipeline] = None

# ===================================
# Lifecycle & App
# ===================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 60)
    print("   ENVY v6.0 - FULL CAPABILITIES MODE")
    print("   No Authentication Required")
    print("=" * 60 + "\n")
    
    global envy_instance, init_error, file_handler, mcp_client, connector_registry, agent_spawner, supabase, project_manager, profile_manager, vector_store, rag_pipeline
    
    # Initialize Supabase if configured
    if settings.has_supabase and create_client:
        try:
            supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
            print("[OK] Supabase connected")
        except Exception as e:
            print(f"[!] Supabase error: {e}")
    
    # Initialize File Handler
    file_handler = get_file_handler()
    print("[OK] File Handler initialized")
    
    # Initialize MCP Client
    mcp_client = get_mcp_client()
    print("[OK] MCP Client initialized")
    
    # Initialize Connector Registry
    connector_registry = get_connector_registry(mcp_client)
    print(f"[OK] Connector Registry initialized ({len(connector_registry.configs)} connectors available)")
    
    # Initialize Project Manager (Phase 1.1)
    project_manager = get_project_manager(supabase)
    print("[OK] Project Manager initialized")
    
    # Initialize Memory Systems (Phase 1.2 & 1.3)
    vector_store = get_vector_store(supabase)
    rag_pipeline = get_rag_pipeline(vector_store)
    profile_manager = get_profile_manager(supabase)
    print("[OK] Memory Systems initialized (Vector Store, RAG, User Profiles)")
    
    # Check for API keys
    has_llm = settings.has_groq or settings.has_openrouter
    if not has_llm:
        init_error = "No LLM API key configured! Please set GROQ_API_KEY or OPENROUTER_API_KEY"
        print(f"[!] WARNING: {init_error}")
        print("[*] Chat will be disabled until API keys are configured.")
    else:
        try:
            envy_instance = ENVY(session_id="production")
            await envy_instance.initialize()
            print("[OK] ENVY Agent initialized")
            
            # Initialize Agent Spawner with ENVY's LLM client
            agent_spawner = get_agent_spawner(envy_instance.llm, envy_instance.tool_manager)
            print("[OK] Agent Spawner initialized")
            
        except Exception as e:
            init_error = f"Failed to initialize ENVY: {str(e)}"
            print(f"[!] ERROR: {init_error}")
    
    print("\n" + "=" * 60)
    print("   Server Ready - All Systems Online")
    print("=" * 60 + "\n")
    
    yield
    
    # Cleanup
    if envy_instance:
        await envy_instance.close()
    if mcp_client:
        await mcp_client.close()

app = FastAPI(
    title="ENVY API",
    description="Polymorphic Intelligence System with Full MCP & Agent Capabilities",
    version="6.0.0",
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
# UTILITY FUNCTIONS
# ===================================

def validate_uuid(value: str, param_name: str = "ID") -> None:
    """
    Validate that a string is a valid UUID format.
    Raises HTTPException with 400 status code if invalid.
    
    Args:
        value: The string to validate as UUID
        param_name: Name of the parameter for error message
    
    Raises:
        HTTPException: 400 Bad Request if the value is not a valid UUID
    """
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format: '{value}'. Expected a valid UUID."
        )

# ===================================
# HEALTH & STATUS
# ===================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if envy_instance else "degraded",
        "version": "6.0.0",
        "auth": "disabled",
        "llm_configured": settings.has_groq or settings.has_openrouter,
        "error": init_error,
        "capabilities": {
            "file_upload": file_handler is not None,
            "mcp": mcp_client is not None,
            "connectors": connector_registry is not None,
            "agents": agent_spawner is not None,
            "projects": project_manager is not None,
            "vector_store": vector_store is not None,
            "rag": rag_pipeline is not None,
            "user_profiles": profile_manager is not None
        }
    }

@app.get("/api/status")
async def api_status():
    """Detailed API status"""
    return {
        "ready": envy_instance is not None,
        "error": init_error,
        "groq_configured": settings.has_groq,
        "openrouter_configured": settings.has_openrouter,
        "supabase_configured": settings.has_supabase,
        "uploaded_files": len(file_handler.files) if file_handler else 0,
        "connected_connectors": len(connector_registry.list_connected()) if connector_registry else 0,
        "active_agents": len([a for a in agent_spawner.agents.values() if a.status == AgentStatus.RUNNING]) if agent_spawner else 0
    }

@app.get("/api/capabilities")
async def get_capabilities():
    """Get all system capabilities"""
    capabilities = {
        "file_upload": {
            "enabled": True,
            "supported_types": {
                "documents": [".pdf", ".docx", ".txt", ".md", ".csv", ".json"],
                "images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"],
                "code": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".sql"]
            },
            "max_size_mb": 50
        },
        "mcp": {
            "enabled": True,
            "connected_servers": mcp_client.list_servers() if mcp_client else [],
            "total_tools": len(mcp_client.get_aggregated_tools()) if mcp_client else 0
        },
        "connectors": {
            "enabled": True,
            "available": connector_registry.list_connectors() if connector_registry else [],
            "health": connector_registry.get_health_status() if connector_registry else {}
        },
        "agents": {
            "enabled": True,
            "blueprints": agent_spawner.list_blueprints() if agent_spawner else [],
            "active": len(agent_spawner.list_agents(AgentStatus.RUNNING)) if agent_spawner else 0
        },
        "personas": [
            {"id": p.id, "name": p.name, "title": p.title}
            for p in PERSONAS.values()
        ]
    }
    return capabilities

# ===================================
# FILE UPLOAD ENDPOINTS
# ===================================

@app.post("/api/files/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload one or more files.
    Supports documents, images, and code files.
    """
    if not file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")
    
    results = []
    for file in files:
        try:
            contents = await file.read()
            uploaded = await file_handler.process_upload(contents, file.filename)
            results.append({
                "id": uploaded.id,
                "filename": uploaded.filename,
                "type": uploaded.file_type.value,
                "size_bytes": uploaded.size_bytes,
                "mime_type": uploaded.mime_type,
                "metadata": uploaded.metadata
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {"uploaded": results}

@app.get("/api/files/{file_id}")
async def get_file(file_id: str, include_content: bool = False):
    """Get file metadata and optionally content"""
    if not file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")
    
    file = file_handler.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    result = {
        "id": file.id,
        "filename": file.filename,
        "type": file.file_type.value,
        "mime_type": file.mime_type,
        "size_bytes": file.size_bytes,
        "created_at": file.created_at.isoformat(),
        "metadata": file.metadata
    }
    
    if include_content:
        result["content"] = file.content
    
    return result

@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str):
    """Download file content"""
    if not file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")
    
    file = file_handler.get_file(file_id)
    if not file or not file.path:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file.path,
        filename=file.filename,
        media_type=file.mime_type
    )

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file"""
    if not file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")
    
    if file_handler.delete_file(file_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/files")
async def list_files(type: Optional[str] = None):
    """List all uploaded files"""
    if not file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")
    
    file_type = None
    if type:
        try:
            file_type = FileType(type)
        except ValueError:
            pass
    
    return {"files": file_handler.list_files(file_type)}

# ===================================
# MCP & CONNECTOR ENDPOINTS
# ===================================

@app.get("/api/mcp/sse")
async def mcp_sse_stream():
    """
    Server-Sent Events stream for MCP events.
    Frontend connects here to receive real-time updates.
    """
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    async def event_generator():
        try:
            async for event in mcp_client.stream_events():
                yield f"data: {json.dumps(event.to_dict())}\n\n"
        except asyncio.CancelledError:
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/mcp/connectors")
async def list_connectors():
    """List all available connectors"""
    if not connector_registry:
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    
    return {"connectors": connector_registry.list_connectors(include_disabled=True)}

@app.post("/api/mcp/connectors/{connector_id}/connect")
async def connect_connector(connector_id: str, body: ConnectorCredentials = None):
    """Connect to a connector"""
    if not connector_registry:
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    
    credentials = body.credentials if body else {}
    
    try:
        state = await connector_registry.connect(connector_id, credentials)
        return {
            "id": connector_id,
            "status": state.status.value,
            "tools": len(state.tools),
            "error": state.error_message
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/mcp/connectors/{connector_id}/disconnect")
async def disconnect_connector(connector_id: str):
    """Disconnect from a connector"""
    if not connector_registry:
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    
    try:
        state = await connector_registry.disconnect(connector_id)
        return {"id": connector_id, "status": state.status.value}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/mcp/connectors/{connector_id}")
async def get_connector_status(connector_id: str):
    """Get connector status and tools"""
    if not connector_registry:
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    
    state = connector_registry.get_state(connector_id)
    if not state:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    return {
        "id": connector_id,
        "name": state.config.name,
        "status": state.status.value,
        "tools": state.tools,
        "resources": state.resources,
        "error": state.error_message
    }

@app.get("/api/mcp/tools")
async def list_all_tools():
    """List all tools from all connected connectors"""
    if not connector_registry:
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    
    return {"tools": connector_registry.get_all_tools()}

@app.post("/api/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    """Execute a tool"""
    if not connector_registry:
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    
    try:
        result = await connector_registry.call_tool(request.tool_name, request.arguments)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/mcp/health")
async def mcp_health():
    """Get MCP subsystem health"""
    return {
        "mcp_client": mcp_client.get_health() if mcp_client else {"status": "unavailable"},
        "connectors": connector_registry.get_health_status() if connector_registry else {"status": "unavailable"}
    }

# ===================================
# AGENT SPAWNER ENDPOINTS
# ===================================

@app.post("/api/agents/spawn")
async def spawn_agent(request: SpawnAgentRequest):
    """Spawn a new agent"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    try:
        agent_id = await agent_spawner.spawn(
            role=request.role,
            task=request.task,
            context=request.context
        )
        return {"agent_id": agent_id, "status": "spawned"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/agents/spawn/custom")
async def spawn_custom_agent(request: CustomBlueprintRequest):
    """Spawn a custom agent with inline blueprint"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    try:
        blueprint = agent_spawner.create_custom_blueprint(
            name=request.name,
            system_prompt=request.system_prompt,
            tools=request.tools,
            max_iterations=request.max_iterations
        )
        agent_id = await agent_spawner.spawn(
            role="custom",
            task=request.task,
            context=request.context,
            custom_blueprint=blueprint
        )
        return {"agent_id": agent_id, "status": "spawned"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/agents/{agent_id}")
async def get_agent_status(agent_id: str):
    """Get agent status and result"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    status = agent_spawner.get_status(agent_id)
    if not status:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return status

@app.get("/api/agents/{agent_id}/result")
async def get_agent_result(agent_id: str):
    """Get agent result (waits for completion)"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    result = await agent_spawner.wait_for(agent_id, timeout=60.0)
    return {"agent_id": agent_id, "result": result}

@app.post("/api/agents/{agent_id}/cancel")
async def cancel_agent(agent_id: str):
    """Cancel a running agent"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    if await agent_spawner.cancel(agent_id):
        return {"agent_id": agent_id, "status": "cancelled"}
    raise HTTPException(status_code=400, detail="Could not cancel agent")

@app.get("/api/agents")
async def list_agents(status: Optional[str] = None):
    """List all agents"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    status_filter = None
    if status:
        try:
            status_filter = AgentStatus(status)
        except ValueError:
            pass
    
    return {"agents": agent_spawner.list_agents(status_filter)}

@app.get("/api/agents/blueprints")
async def list_blueprints():
    """List available agent blueprints"""
    if not agent_spawner:
        raise HTTPException(status_code=503, detail="Agent spawner not initialized")
    
    return {"blueprints": agent_spawner.list_blueprints()}

# ===================================
# PROJECT ENDPOINTS (Phase 1.1)
# ===================================

@app.post("/api/projects")
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    try:
        settings_obj = None
        if request.settings:
            settings_obj = ProjectSettings(**request.settings)
        
        project = await project_manager.create_project(
            name=request.name,
            description=request.description,
            settings=settings_obj,
            metadata=request.metadata
        )
        
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value,
            "created_at": project.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/projects")
async def list_projects(status: Optional[str] = None):
    """List all projects"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    from envy.projects.project_manager import ProjectStatus as ProjStatus
    status_filter = None
    if status:
        try:
            status_filter = ProjStatus(status)
        except ValueError:
            pass
    
    projects = await project_manager.list_projects(status_filter)
    return {"projects": projects}

@app.get("/api/projects/active")
async def get_active_project():
    """Get the currently active project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    project = await project_manager.get_active_project()
    if not project:
        return {"active_project": None}
    
    return {
        "id": project.id,
        "name": project.name,
        "file_count": project.get_file_count()
    }

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get a project by ID"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Build file tree
    tree = FileTree.from_project_files(project.files)
    
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status.value,
        "settings": project.settings.to_dict(),
        "file_count": project.get_file_count(),
        "total_size": project.get_total_size(),
        "file_tree": tree.to_dict(),
        "context_snapshot": project.context_snapshot,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "metadata": project.metadata
    }

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    settings_obj = None
    if request.settings:
        settings_obj = ProjectSettings(**request.settings)
    
    project = await project_manager.update_project(
        project_id=project_id,
        name=request.name,
        description=request.description,
        settings=settings_obj,
        metadata=request.metadata
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"id": project.id, "updated": True}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    if await project_manager.delete_project(project_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Project not found")

@app.post("/api/projects/{project_id}/archive")
async def archive_project(project_id: str):
    """Archive a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    project = await project_manager.archive_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"id": project.id, "status": project.status.value}

@app.post("/api/projects/{project_id}/activate")
async def activate_project(project_id: str):
    """Set a project as the active project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    project = await project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_manager.set_active_project(project_id)
    return {"active_project": project_id}

# Project Files
@app.post("/api/projects/{project_id}/files")
async def add_project_file(project_id: str, request: AddFileRequest):
    """Add a file to a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    pf = await project_manager.add_file(
        project_id=project_id,
        path=request.path,
        content=request.content,
        mime_type=request.mime_type,
        metadata=request.metadata
    )
    
    if not pf:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "id": pf.id,
        "path": pf.path,
        "filename": pf.filename,
        "size_bytes": pf.size_bytes
    }

@app.get("/api/projects/{project_id}/files")
async def list_project_files(project_id: str):
    """List all files in a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    files = await project_manager.list_files(project_id)
    return {"files": files}

@app.get("/api/projects/{project_id}/files/{file_path:path}")
async def get_project_file(project_id: str, file_path: str):
    """Get a specific file from a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    pf = await project_manager.get_file(project_id, file_path)
    if not pf:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "id": pf.id,
        "path": pf.path,
        "filename": pf.filename,
        "content": pf.content,
        "mime_type": pf.mime_type,
        "size_bytes": pf.size_bytes,
        "is_embedded": pf.is_embedded,
        "updated_at": pf.updated_at.isoformat()
    }

@app.delete("/api/projects/{project_id}/files/{file_path:path}")
async def delete_project_file(project_id: str, file_path: str):
    """Delete a file from a project"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    if await project_manager.delete_file(project_id, file_path):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="File not found")

# Project Context
@app.get("/api/projects/{project_id}/context")
async def get_project_context(project_id: str):
    """Get project context for LLM injection"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    context_prompt = await project_manager.build_context_prompt(project_id)
    files = await project_manager.get_context_files(project_id)
    
    return {
        "project_id": project_id,
        "context_prompt": context_prompt,
        "files_included": [f.path for f in files],
        "total_chars": len(context_prompt)
    }

@app.put("/api/projects/{project_id}/context")
async def update_project_context(project_id: str, request: UpdateContextRequest):
    """Manually set which files are in context"""
    if not project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    
    # Validate UUID format
    validate_uuid(project_id, "project ID")
    
    project = await project_manager.update_context_snapshot(project_id, request.file_paths)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"context_snapshot": project.context_snapshot}

# ===================================
# USER PROFILE ENDPOINTS (Phase 1.3)
# ===================================

@app.get("/api/profile/{user_id}")
async def get_user_profile(user_id: str = "default"):
    """Get a user's profile"""
    if not profile_manager:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    
    profile = await profile_manager.load(user_id)
    return profile.to_dict()

@app.put("/api/profile/{user_id}")
async def update_user_profile(user_id: str, request: UpdateUserProfileRequest):
    """Update a user's profile"""
    if not profile_manager:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    
    profile = await profile_manager.load(user_id)
    
    if request.name is not None:
        profile.name = request.name
    
    if request.active_project_id is not None:
        profile.active_project_id = request.active_project_id
    
    if request.preferences:
        for key, value in request.preferences.items():
            if hasattr(profile.preferences, key):
                setattr(profile.preferences, key, value)
    
    if request.writing_style:
        for key, value in request.writing_style.items():
            if hasattr(profile.writing_style, key):
                if key == 'tone':
                    value = Tone(value) if isinstance(value, str) else value
                setattr(profile.writing_style, key, value)
    
    await profile_manager.save(profile)
    return {"updated": True, "user_id": user_id}

@app.post("/api/profile/{user_id}/facts")
async def add_user_fact(user_id: str, request: AddFactRequest):
    """Add a known fact about the user"""
    if not profile_manager:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    
    profile = await profile_manager.load(user_id)
    profile.add_fact(request.fact)
    await profile_manager.save(profile)
    
    return {"added": True, "facts_count": len(profile.known_facts)}

@app.post("/api/profile/{user_id}/learnings")
async def add_user_learning(user_id: str, request: AddLearningRequest):
    """Add a learning about the user"""
    if not profile_manager:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    
    await profile_manager.add_learning(
        user_id=user_id,
        content=request.content,
        category=request.category,
        confidence=request.confidence,
        source=request.source
    )
    
    return {"added": True}

@app.get("/api/profile/{user_id}/context")
async def get_user_context(user_id: str = "default"):
    """Get user context prompt for LLM injection"""
    if not profile_manager:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    
    profile = await profile_manager.load(user_id)
    context = profile.get_context_prompt()
    
    return {
        "user_id": user_id,
        "context_prompt": context,
        "interaction_count": profile.interaction_count
    }

@app.delete("/api/profile/{user_id}")
async def delete_user_profile(user_id: str):
    """Delete a user profile"""
    if not profile_manager:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    
    if await profile_manager.delete(user_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Profile not found")

# ===================================
# RAG ENDPOINTS (Phase 1.2)
# ===================================

@app.post("/api/rag/index")
async def index_document(project_id: str, file_path: str):
    """Index a project file for RAG retrieval"""
    if not rag_pipeline or not project_manager:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    # Get the file from the project
    pf = await project_manager.get_file(project_id, file_path)
    if not pf:
        raise HTTPException(status_code=404, detail="File not found")
    
    chunk_ids = await rag_pipeline.index_file(pf, project_id)
    return {
        "indexed": True,
        "file_path": file_path,
        "chunks_created": len(chunk_ids)
    }

@app.post("/api/rag/search")
async def rag_search(query: str, project_id: Optional[str] = None, top_k: int = 5):
    """Search indexed documents"""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    context = await rag_pipeline.retrieve(query, project_id, top_k)
    
    return {
        "query": query,
        "results": [
            {
                "chunk_id": chunk.chunk_id,
                "content": chunk.text[:500],  # Preview
                "score": chunk.score,
                "metadata": chunk.metadata
            }
            for chunk in context.chunks
        ],
        "context_prompt": context.context_prompt[:1000] if context.context_prompt else None
    }

# ===================================
# CHAT ENDPOINTS (with file support)
# ===================================

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    """Non-streaming chat completion with file attachment support"""
    if not envy_instance:
        error_msg = init_error or "ENVY not initialized. Please configure API keys."
        raise HTTPException(status_code=503, detail=error_msg)
    
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    user_message = messages[-1]["content"] if messages else ""
    
    # Inject file context if attachments provided
    if request.attachments and file_handler:
        file_contexts = []
        for file_id in request.attachments:
            file = file_handler.get_file(file_id)
            if file:
                if file.file_type == FileType.IMAGE:
                    file_contexts.append(f"[Image attached: {file.filename}]")
                else:
                    file_contexts.append(f"--- {file.filename} ---\n{file.content[:2000]}\n---")
        
        if file_contexts:
            user_message = f"{user_message}\n\nATTACHED FILES:\n" + "\n".join(file_contexts)
    
    try:
        response = await envy_instance.process(user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response},
            "finish_reason": "stop"
        }]
    }

@app.post("/v1/chat/completions/stream")
async def chat_completion_stream(request: ChatRequest):
    """Streaming chat completion with file and artifact support"""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    user_message = messages[-1]["content"] if messages else ""
    
    # DEBUG: Log incoming request
    print(f"\n[DEBUG STREAM] Received request with {len(request.attachments or [])} attachments")
    if request.attachments:
        print(f"[DEBUG STREAM] Attachment IDs: {request.attachments}")
    
    # Inject file context
    if request.attachments and file_handler:
        file_contexts = []
        for file_id in request.attachments:
            file = file_handler.get_file(file_id)
            print(f"[DEBUG STREAM] Processing file {file_id}: found={file is not None}")
            if file:
                print(f"[DEBUG STREAM] File type: {file.file_type}, filename: {file.filename}")
                if file.file_type == FileType.IMAGE:
                    # Pass image reference to context
                    file_contexts.append(f"[IMAGE: {file.filename} (Path: {file.path})]")
                else:
                    file_contexts.append(f"--- {file.filename} ---\n{file.content[:2000]}\n---")
        
        if file_contexts:
            user_message = f"{user_message}\n\nATTACHED FILES:\n" + "\n".join(file_contexts)
    
    print(f"[DEBUG STREAM] Final message length: {len(user_message)} chars")
    
    async def generate() -> AsyncGenerator[str, None]:
        if not envy_instance:
            error_msg = init_error or "ENVY not initialized."
            data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"⚠️ **Configuration Error**\n\n{error_msg}"},
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

@app.post("/api/blueprint/execute")
async def execute_blueprint(request: ChatRequest):
    """
    Execute the full Architect -> Builder -> Scribe pipeline.
    This is the "100x Leverage" mode.
    """
    if not envy_instance:
         raise HTTPException(status_code=503, detail="ENVY not initialized")
    
    # Extract the user's initial prompt
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    initial_prompt = messages[-1]["content"] if messages else ""

    try:
        results = await envy_instance.reasoning.execute_blueprint_pipeline(
            initial_request=initial_prompt,
            context={}
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===================================
# PERSONA ENDPOINTS
# ===================================

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

# ===================================
# ARTIFACT ENDPOINTS
# ===================================

@app.get("/api/artifacts/sandbox")
async def get_artifact_sandbox():
    """Get HTML template for artifact sandbox iframe"""
    sandbox_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; margin: 0; padding: 16px; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'RENDER_ARTIFACT') {
                const code = event.data.code;
                const artifactType = event.data.artifactType;
                
                if (artifactType === 'react' || artifactType === 'application/vnd.ant.react') {
                    try {
                        const transformed = Babel.transform(code, { presets: ['react'] }).code;
                        eval(transformed);
                    } catch (e) {
                        document.getElementById('root').innerHTML = '<pre style="color:red">' + e.message + '</pre>';
                    }
                } else if (artifactType === 'html' || artifactType === 'text/html') {
                    document.getElementById('root').innerHTML = code;
                } else if (artifactType === 'svg' || artifactType === 'image/svg+xml') {
                    document.getElementById('root').innerHTML = code;
                }
            }
        });
        
        // Signal ready
        window.parent.postMessage({ type: 'SANDBOX_READY' }, '*');
    </script>
</body>
</html>
"""
    return HTMLResponse(content=sandbox_html)

# ===================================
# Static Files & Root Route
# ===================================

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve the main chat interface"""
    return FileResponse("static/index.html")

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
