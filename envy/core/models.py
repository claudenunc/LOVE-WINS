"""
ENVY Core Data Models (Knowledge Spine)
=======================================
Strict implementation of the ENVY Master Blueprint entities.
These models serve as the Single Source of Truth for agent communication.
"""

from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field

def generate_uuid() -> str:
    return str(uuid4())

def get_iso_time() -> str:
    return datetime.now().isoformat()

# =============================================================================
# HANDOFF PACKET (The Glue)
# =============================================================================

class HandoffPacket(BaseModel):
    """
    Structured protocol for agent-to-agent state transfer.
    As defined in Section 6 of the ENVY Master Blueprint.
    """
    handoff_id: str = Field(default_factory=generate_uuid)
    from_agent: str
    to_agent: str
    project_id: str = "envy-core"
    summary: str = Field(description="Short description of what was done.")
    artifacts: List[str] = Field(description="URIs or identifiers of created artifacts (e.g., doc://..., file://...)")
    
    # Context & Continuity
    open_questions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Narrative Bridge (The "Letter" to the next agent)
    narrative_note: str = Field(description="Conversational handoff note preserving the OmniLink voice.")
    
    timestamp: str = Field(default_factory=get_iso_time)

    class Config:
        json_schema_extra = {
            "example": {
                "handoff_id": "550e8400-e29b-41d4-a716-446655440000",
                "from_agent": "architect-agent",
                "to_agent": "builder-agent",
                "project_id": "envy-core",
                "summary": "Designed the database schema for the user profiles.",
                "artifacts": ["doc://schemas/user_profile_v1.md", "file://database/schema.sql"],
                "narrative_note": "Yo Builder, I mapped out the user schema. Watch out for the foreign key on 'org_id', it's tricky. Good luck.",
                "timestamp": "2023-10-27T10:00:00Z"
            }
        }

# =============================================================================
# KNOWLEDGE SPINE ENTITIES
# =============================================================================

class AgentProfile(BaseModel):
    """
    Definition of a Polymorphic Agent.
    """
    id: str
    name: str
    role_description: str
    specialized_capabilities: List[str]
    # Every agent acts as a 'morph' of the base OmniLink persona
    base_persona_id: str = "omni_link"

class Artifact(BaseModel):
    """
    A persistent object created by an agent (file, doc, code, etc.)
    """
    id: str = Field(default_factory=generate_uuid)
    uri: str # e.g., file://path/to/file or doc://title
    type: Literal["code", "document", "workflow", "image", "other"]
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: str
    created_at: str = Field(default_factory=get_iso_time)

class Decision(BaseModel):
    """
    Log of a major architectural or logic decision.
    """
    id: str = Field(default_factory=generate_uuid)
    title: str
    description: str
    rationale: str
    made_by: str
    timestamp: str = Field(default_factory=get_iso_time)
