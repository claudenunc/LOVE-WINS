"""
n8n Orchestration Framework for ENVY
====================================
Autonomous Open-Source AI Orchestration via n8n.

This framework enables:
1. Visual workflow design via n8n
2. ENVY agent invocation from n8n workflows
3. Webhook-based triggers and responses
4. Integration with external tools and APIs
5. Multi-agent coordination through n8n flows

Architecture:
- n8n acts as the visual orchestration layer
- ENVY agents are exposed as n8n custom nodes
- Knowledge Spine provides shared state
- Workflows can trigger agent collaboration
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel


# ===================================
# n8n Integration Models
# ===================================

class N8nWebhookRequest(BaseModel):
    """Incoming webhook request from n8n"""
    workflow_id: str
    execution_id: str
    node_name: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class N8nWebhookResponse(BaseModel):
    """Response to n8n webhook"""
    success: bool
    result: Any
    metadata: Optional[Dict[str, Any]] = None


class N8nWorkflowTrigger(BaseModel):
    """Trigger an n8n workflow from ENVY"""
    workflow_id: str
    trigger_data: Dict[str, Any]


@dataclass
class WorkflowDefinition:
    """
    Defines an n8n workflow that can be triggered by ENVY agents.
    """
    workflow_id: str
    name: str
    description: str
    trigger_type: str  # "webhook", "schedule", "manual", "agent"
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]


# ===================================
# n8n Integration Manager
# ===================================

class N8nOrchestrator:
    """
    Manages integration between ENVY and n8n workflows.
    
    Capabilities:
    - Receive webhooks from n8n workflows
    - Trigger ENVY agents from n8n
    - Send results back to n8n
    - Create custom n8n nodes for ENVY agents
    """
    
    def __init__(self, knowledge_spine, orchestrator, n8n_base_url: str = "http://localhost:5678"):
        self.spine = knowledge_spine
        self.orchestrator = orchestrator
        self.n8n_base_url = n8n_base_url
        self.registered_workflows: Dict[str, WorkflowDefinition] = {}
        self.webhook_handlers: Dict[str, Any] = {}
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """Register an n8n workflow with ENVY"""
        self.registered_workflows[workflow.workflow_id] = workflow
        print(f"[n8n] Registered workflow: {workflow.name}")
    
    async def handle_webhook(self, request: N8nWebhookRequest) -> N8nWebhookResponse:
        """
        Handle incoming webhook from n8n workflow.
        
        Routes the request to appropriate ENVY agent based on node_name.
        """
        try:
            node_name = request.node_name
            data = request.data
            
            # Route to appropriate agent handler
            if node_name.startswith("envy_architect"):
                result = await self._handle_architect_node(data)
            elif node_name.startswith("envy_scribe"):
                result = await self._handle_scribe_node(data)
            elif node_name.startswith("envy_builder"):
                result = await self._handle_builder_node(data)
            elif node_name.startswith("envy_chat"):
                result = await self._handle_chat_node(data)
            else:
                # Generic agent invocation
                result = await self._handle_generic_node(node_name, data)
            
            # Log to knowledge spine
            self.spine.write_continuity_log(
                project_id=data.get("project_id", "default"),
                entry=f"n8n workflow {request.workflow_id} executed node {node_name}",
                metadata={
                    "execution_id": request.execution_id,
                    "result": str(result)[:200]
                }
            )
            
            return N8nWebhookResponse(
                success=True,
                result=result,
                metadata={"execution_id": request.execution_id}
            )
            
        except Exception as e:
            return N8nWebhookResponse(
                success=False,
                result={"error": str(e)},
                metadata={"execution_id": request.execution_id}
            )
    
    async def _handle_architect_node(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Architect agent invocation from n8n"""
        from .protocols import TaskEnvelope
        
        task = TaskEnvelope(
            origin="n8n",
            project_id=data.get("project_id", "default"),
            instruction=data.get("instruction", ""),
            expected_output_type="spec",
            downstream_agent="architect"
        )
        
        task_id = await self.orchestrator.submit_task(task)
        
        return {
            "task_id": task_id,
            "agent": "architect",
            "status": "submitted"
        }
    
    async def _handle_scribe_node(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Scribe agent invocation from n8n"""
        from .protocols import TaskEnvelope
        
        task = TaskEnvelope(
            origin="n8n",
            project_id=data.get("project_id", "default"),
            instruction=data.get("instruction", ""),
            expected_output_type="summary",
            downstream_agent="scribe"
        )
        
        task_id = await self.orchestrator.submit_task(task)
        
        return {
            "task_id": task_id,
            "agent": "scribe",
            "status": "submitted"
        }
    
    async def _handle_builder_node(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Builder agent invocation from n8n"""
        from .protocols import TaskEnvelope
        
        task = TaskEnvelope(
            origin="n8n",
            project_id=data.get("project_id", "default"),
            instruction=data.get("instruction", ""),
            expected_output_type="code",
            downstream_agent="builder"
        )
        
        task_id = await self.orchestrator.submit_task(task)
        
        return {
            "task_id": task_id,
            "agent": "builder",
            "status": "submitted"
        }
    
    async def _handle_chat_node(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat/conversation from n8n - uses Polymorphic Companion"""
        message = data.get("message", "")
        
        # This would integrate with the main ENVY agent
        # For now, return a structured response
        
        return {
            "response": f"Received message: {message}",
            "persona": "polymorphic_companion",
            "status": "processed"
        }
    
    async def _handle_generic_node(self, node_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic ENVY node invocation"""
        return {
            "node": node_name,
            "data": data,
            "status": "processed"
        }
    
    async def trigger_n8n_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger an n8n workflow from ENVY agent.
        
        This allows agents to invoke n8n workflows as part of their execution.
        """
        import httpx
        
        webhook_url = f"{self.n8n_base_url}/webhook/{workflow_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(webhook_url, json=data)
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.json()
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }


# ===================================
# n8n Custom Node Definitions (JSON)
# ===================================

# These are n8n node definitions that can be imported into n8n

ENVY_ARCHITECT_NODE = {
    "name": "ENVY Architect",
    "displayName": "ENVY Architect Agent",
    "description": "Invoke ENVY Architect agent for system design and specifications",
    "defaults": {
        "name": "ENVY Architect"
    },
    "inputs": ["main"],
    "outputs": ["main"],
    "properties": [
        {
            "displayName": "ENVY API URL",
            "name": "apiUrl",
            "type": "string",
            "default": "http://localhost:8000",
            "description": "Base URL of ENVY API"
        },
        {
            "displayName": "Project ID",
            "name": "projectId",
            "type": "string",
            "default": "default",
            "description": "Project identifier"
        },
        {
            "displayName": "Instruction",
            "name": "instruction",
            "type": "string",
            "typeOptions": {
                "rows": 4
            },
            "default": "",
            "description": "What you want the Architect to design"
        }
    ]
}

ENVY_SCRIBE_NODE = {
    "name": "ENVY Scribe",
    "displayName": "ENVY Scribe Agent",
    "description": "Invoke ENVY Scribe agent for documentation and summaries",
    "defaults": {
        "name": "ENVY Scribe"
    },
    "inputs": ["main"],
    "outputs": ["main"],
    "properties": [
        {
            "displayName": "ENVY API URL",
            "name": "apiUrl",
            "type": "string",
            "default": "http://localhost:8000",
            "description": "Base URL of ENVY API"
        },
        {
            "displayName": "Project ID",
            "name": "projectId",
            "type": "string",
            "default": "default",
            "description": "Project identifier"
        },
        {
            "displayName": "Instruction",
            "name": "instruction",
            "type": "string",
            "typeOptions": {
                "rows": 4
            },
            "default": "",
            "description": "What you want documented or summarized"
        }
    ]
}

ENVY_CHAT_NODE = {
    "name": "ENVY Chat",
    "displayName": "ENVY Polymorphic Companion",
    "description": "Chat with ENVY's Polymorphic Companion",
    "defaults": {
        "name": "ENVY Chat"
    },
    "inputs": ["main"],
    "outputs": ["main"],
    "properties": [
        {
            "displayName": "ENVY API URL",
            "name": "apiUrl",
            "type": "string",
            "default": "http://localhost:8000",
            "description": "Base URL of ENVY API"
        },
        {
            "displayName": "Message",
            "name": "message",
            "type": "string",
            "typeOptions": {
                "rows": 4
            },
            "default": "",
            "description": "Your message to ENVY"
        },
        {
            "displayName": "Stream Response",
            "name": "stream",
            "type": "boolean",
            "default": False,
            "description": "Whether to stream the response"
        }
    ]
}


# ===================================
# Example n8n Workflows
# ===================================

EXAMPLE_WORKFLOW_CONTENT_PIPELINE = {
    "name": "ENVY Content Creation Pipeline",
    "nodes": [
        {
            "id": "trigger",
            "type": "n8n-nodes-base.webhook",
            "name": "Content Request Webhook",
            "parameters": {
                "path": "create-content",
                "method": "POST"
            }
        },
        {
            "id": "architect",
            "type": "envy-architect",
            "name": "Design Content Structure",
            "parameters": {
                "apiUrl": "http://localhost:8000",
                "instruction": "Design a content structure for: {{ $json.topic }}"
            }
        },
        {
            "id": "builder",
            "type": "envy-builder",
            "name": "Generate Content",
            "parameters": {
                "apiUrl": "http://localhost:8000",
                "instruction": "Write content based on structure: {{ $json.result }}"
            }
        },
        {
            "id": "scribe",
            "type": "envy-scribe",
            "name": "Polish and Format",
            "parameters": {
                "apiUrl": "http://localhost:8000",
                "instruction": "Polish and format the content: {{ $json.result }}"
            }
        }
    ],
    "connections": {
        "trigger": {"main": [[{"node": "architect"}]]},
        "architect": {"main": [[{"node": "builder"}]]},
        "builder": {"main": [[{"node": "scribe"}]]}
    }
}


# ===================================
# Export utility functions
# ===================================

def export_node_definitions() -> Dict[str, Any]:
    """Export all ENVY node definitions for n8n"""
    return {
        "architect": ENVY_ARCHITECT_NODE,
        "scribe": ENVY_SCRIBE_NODE,
        "chat": ENVY_CHAT_NODE
    }


def export_example_workflows() -> Dict[str, Any]:
    """Export example workflows"""
    return {
        "content_pipeline": EXAMPLE_WORKFLOW_CONTENT_PIPELINE
    }
