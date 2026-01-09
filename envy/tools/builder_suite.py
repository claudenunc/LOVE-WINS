"""
Builder Suite - Production Creation Tools
=========================================
Provides concrete functions for creating n8n workflows, websites, apps, etc.

These are the "handles" that agents can grab to build real things.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


# ===================================
# n8n Workflow Builder
# ===================================

def create_n8n_workflow(
    name: str,
    description: str,
    nodes: List[Dict[str, Any]],
    connections: Dict[str, Any],
    settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an n8n workflow definition.
    
    Args:
        name: Workflow name
        description: What this workflow does
        nodes: List of node definitions
        connections: Connection map between nodes
        settings: Optional workflow settings
    
    Returns:
        Complete n8n workflow JSON
    """
    workflow = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": settings or {},
        "id": None,  # Will be assigned by n8n
        "tags": []
    }
    
    if description:
        workflow["settings"]["description"] = description
    
    return workflow


def add_webhook_trigger(workflow_id: str, path: str) -> Dict[str, Any]:
    """Add a webhook trigger node to workflow"""
    return {
        "parameters": {
            "path": path,
            "method": "POST",
            "responseMode": "onReceived"
        },
        "name": "Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 1,
        "position": [250, 300],
        "webhookId": workflow_id
    }


def add_envy_agent_node(
    agent_name: str,
    instruction: str,
    project_id: str = "default"
) -> Dict[str, Any]:
    """Add an ENVY agent node to workflow"""
    return {
        "parameters": {
            "agent": agent_name,
            "instruction": instruction,
            "projectId": project_id,
            "apiUrl": "http://localhost:8000"
        },
        "name": f"ENVY {agent_name.title()}",
        "type": f"envy-{agent_name}",
        "typeVersion": 1,
        "position": [450, 300]
    }


# ===================================
# Website Generator
# ===================================

def generate_website(
    title: str,
    description: str,
    pages: List[Dict[str, str]],
    style: str = "modern",
    framework: str = "html"
) -> Dict[str, Any]:
    """
    Generate a complete website structure.
    
    Args:
        title: Site title
        description: Site description
        pages: List of {name, content, route}
        style: Design style (modern, minimal, corporate)
        framework: html, react, vue, etc.
    
    Returns:
        Dictionary with file structure
    """
    
    if framework == "html":
        return _generate_html_site(title, description, pages, style)
    elif framework == "react":
        return _generate_react_site(title, description, pages, style)
    else:
        raise ValueError(f"Unsupported framework: {framework}")


def _generate_html_site(
    title: str,
    description: str,
    pages: List[Dict[str, str]],
    style: str
) -> Dict[str, Any]:
    """Generate static HTML website"""
    
    # Base HTML template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <h1>{title}</h1>
        <nav>
            {{nav_links}}
        </nav>
    </header>
    <main>
        {{content}}
    </main>
    <footer>
        <p>&copy; 2026 {title}. All rights reserved.</p>
    </footer>
</body>
</html>"""
    
    # Generate nav links
    nav_links = "\n".join([
        f'<a href="{page.get("route", "/")}">{page["name"]}</a>'
        for page in pages
    ])
    
    # Generate pages
    files = {}
    for page in pages:
        page_html = html_template.replace("{{nav_links}}", nav_links)
        page_html = page_html.replace("{{content}}", page.get("content", ""))
        
        route = page.get("route", "/").strip("/")
        filename = f"{route or 'index'}.html"
        files[filename] = page_html
    
    # Generate CSS
    files["style.css"] = _generate_css(style)
    
    return {
        "framework": "html",
        "title": title,
        "files": files,
        "entry_point": "index.html"
    }


def _generate_react_site(title: str, description: str, pages: List[Dict[str, str]], style: str) -> Dict[str, Any]:
    """Generate React website (stub for now)"""
    return {
        "framework": "react",
        "title": title,
        "description": description,
        "files": {
            "package.json": json.dumps({
                "name": title.lower().replace(" ", "-"),
                "version": "1.0.0",
                "dependencies": {
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0"
                }
            }, indent=2),
            "src/App.js": "// React app stub"
        },
        "entry_point": "src/App.js"
    }


def _generate_css(style: str) -> str:
    """Generate CSS based on style"""
    if style == "modern":
        return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }
header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; }
header h1 { font-size: 2.5rem; margin-bottom: 1rem; }
nav a { color: white; text-decoration: none; margin-right: 2rem; font-weight: 500; }
nav a:hover { text-decoration: underline; }
main { max-width: 1200px; margin: 2rem auto; padding: 0 2rem; }
footer { background: #f8f9fa; text-align: center; padding: 2rem; margin-top: 4rem; }
"""
    else:
        return "/* Minimal CSS */"


# ===================================
# App Generator
# ===================================

def generate_app(
    name: str,
    app_type: str,
    features: List[str],
    database_schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a complete application.
    
    Args:
        name: App name
        app_type: web, mobile, desktop, api
        features: List of features (auth, crud, search, etc.)
        database_schema: Optional database schema
    
    Returns:
        Application structure with files
    """
    
    if app_type == "api":
        return _generate_api_app(name, features, database_schema)
    elif app_type == "web":
        return _generate_web_app(name, features, database_schema)
    else:
        return {"error": f"App type {app_type} not yet implemented"}


def _generate_api_app(name: str, features: List[str], database_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate FastAPI application"""
    
    main_py = f"""from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="{name} API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {{"message": "Welcome to {name} API"}}

@app.get("/health")
def health_check():
    return {{"status": "healthy"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
    
    files = {
        "main.py": main_py,
        "requirements.txt": "fastapi\nuvicorn[standard]\npydantic",
        "README.md": f"# {name} API\n\nGenerated by ENVY Builder Suite"
    }
    
    if "auth" in features:
        files["auth.py"] = "# Authentication module stub"
    
    if database_schema:
        files["models.py"] = "# Database models stub"
        files["database.py"] = "# Database connection stub"
    
    return {
        "app_type": "api",
        "name": name,
        "files": files,
        "entry_point": "main.py"
    }


def _generate_web_app(name: str, features: List[str], database_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate full-stack web app (stub)"""
    return {
        "app_type": "web",
        "name": name,
        "files": {
            "frontend/": "React app stub",
            "backend/": "FastAPI backend stub"
        }
    }


# ===================================
# Automation Builder
# ===================================

def create_automation(
    name: str,
    trigger: Dict[str, Any],
    actions: List[Dict[str, Any]],
    conditions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create an automation workflow.
    
    Args:
        name: Automation name
        trigger: Trigger definition (webhook, schedule, event)
        actions: List of actions to execute
        conditions: Optional conditions to check
    
    Returns:
        Automation definition
    """
    return {
        "name": name,
        "trigger": trigger,
        "conditions": conditions or [],
        "actions": actions,
        "enabled": True
    }


# ===================================
# Knowledge System Builder
# ===================================

def create_knowledge_base(
    name: str,
    documents: List[str],
    embedding_model: str = "sentence-transformers",
    chunk_size: int = 500
) -> Dict[str, Any]:
    """
    Create a RAG knowledge base.
    
    Args:
        name: KB name
        documents: List of document paths/URLs
        embedding_model: Model to use for embeddings
        chunk_size: Text chunk size
    
    Returns:
        Knowledge base configuration
    """
    return {
        "name": name,
        "documents": documents,
        "embedding_model": embedding_model,
        "chunk_size": chunk_size,
        "vector_store": "chromadb",  # or "pgvector"
        "status": "pending_ingestion"
    }


# ===================================
# Documentation Generator
# ===================================

def generate_documentation(
    project_name: str,
    components: List[Dict[str, Any]],
    format: str = "markdown"
) -> Dict[str, str]:
    """
    Generate documentation for a project.
    
    Args:
        project_name: Project name
        components: List of components to document
        format: Output format (markdown, html, pdf)
    
    Returns:
        Dictionary of documentation files
    """
    
    readme = f"""# {project_name}

## Overview

Generated by ENVY Builder Suite.

## Components

"""
    
    for component in components:
        readme += f"### {component.get('name', 'Component')}\n\n"
        readme += f"{component.get('description', 'No description')}\n\n"
    
    return {
        "README.md": readme,
        "ARCHITECTURE.md": f"# {project_name} Architecture\n\nTBD",
        "API.md": f"# {project_name} API Reference\n\nTBD"
    }


# ===================================
# Protocol/API Definition Builder
# ===================================

def create_api_spec(
    name: str,
    version: str,
    endpoints: List[Dict[str, Any]],
    format: str = "openapi"
) -> Dict[str, Any]:
    """
    Create an API specification.
    
    Args:
        name: API name
        version: API version
        endpoints: List of endpoint definitions
        format: Spec format (openapi, graphql, grpc)
    
    Returns:
        API specification
    """
    
    if format == "openapi":
        return {
            "openapi": "3.0.0",
            "info": {
                "title": name,
                "version": version,
                "description": f"API specification for {name}"
            },
            "paths": {
                endpoint["path"]: {
                    endpoint["method"].lower(): {
                        "summary": endpoint.get("summary", ""),
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }
                }
                for endpoint in endpoints
            }
        }
    else:
        return {"error": f"Format {format} not yet supported"}


# ===================================
# Utility Functions
# ===================================

def save_to_disk(files: Dict[str, str], base_path: str) -> List[str]:
    """
    Save generated files to disk.
    
    Args:
        files: Dictionary of {filename: content}
        base_path: Base directory path
    
    Returns:
        List of created file paths
    """
    base = Path(base_path)
    base.mkdir(parents=True, exist_ok=True)
    
    created = []
    for filename, content in files.items():
        filepath = base / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        created.append(str(filepath))
    
    return created
