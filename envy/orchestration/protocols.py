"""
Task Envelopes and Handoff Packets
===================================
Standard data structures for multi-agent communication.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4


@dataclass
class TaskEnvelope:
    """
    Standard task envelope for agent communication.
    Every task handed to an agent follows this schema.
    """
    task_id: str = field(default_factory=lambda: str(uuid4()))
    origin: str = "orchestrator"  # orchestrator|human|agent_name
    project_id: str = "default"
    context_refs: List[str] = field(default_factory=list)  # doc://path or graph://path
    instruction: str = ""
    constraints: List[str] = field(default_factory=list)
    expected_output_type: Literal["spec", "code", "diagram", "handoff_packet", "summary", "chat"] = "chat"
    downstream_agent: Optional[str] = None
    priority: Literal["normal", "high", "critical"] = "normal"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission"""
        return {
            "task_id": self.task_id,
            "origin": self.origin,
            "project_id": self.project_id,
            "context_refs": self.context_refs,
            "instruction": self.instruction,
            "constraints": self.constraints,
            "expected_output_type": self.expected_output_type,
            "downstream_agent": self.downstream_agent,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class HandoffPacket:
    """
    The heart of baton-passing and legacy.
    
    This structure ensures every agent's work is:
    1. Contextualized for the next agent
    2. Documented for future collaborators
    3. Traceable and auditable
    """
    handoff_id: str = field(default_factory=lambda: str(uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    project_id: str = "default"
    summary: str = ""  # High-level summary of work done
    artifacts: List[str] = field(default_factory=list)  # doc:// or file:// paths
    open_questions: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    narrative_note: str = ""  # Human-readable letter to next collaborator
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    parent_task_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission"""
        return {
            "handoff_id": self.handoff_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "project_id": self.project_id,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "open_questions": self.open_questions,
            "assumptions": self.assumptions,
            "recommendations": self.recommendations,
            "narrative_note": self.narrative_note,
            "timestamp": self.timestamp,
            "parent_task_id": self.parent_task_id
        }


@dataclass
class AgentContract:
    """
    Defines what an agent can do and how it communicates.
    """
    agent_name: str
    role: str
    primary_focus: str
    capabilities: List[str]
    preferred_input_type: List[str]
    output_type: List[str]
    upstream_agents: List[str] = field(default_factory=list)
    downstream_agents: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "primary_focus": self.primary_focus,
            "capabilities": self.capabilities,
            "preferred_input_type": self.preferred_input_type,
            "output_type": self.output_type,
            "upstream_agents": self.upstream_agents,
            "downstream_agents": self.downstream_agents,
            "constraints": self.constraints
        }


@dataclass
class Decision:
    """
    Records significant decisions for legacy and auditability.
    """
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    project_id: str = "default"
    context: str = ""  # What prompted this decision
    options_considered: List[str] = field(default_factory=list)
    chosen_option: str = ""
    rationale: str = ""
    author: str = "orchestrator"  # Which agent made this decision
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    impact: Literal["low", "medium", "high", "critical"] = "medium"
    reversible: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "project_id": self.project_id,
            "context": self.context,
            "options_considered": self.options_considered,
            "chosen_option": self.chosen_option,
            "rationale": self.rationale,
            "author": self.author,
            "timestamp": self.timestamp,
            "impact": self.impact,
            "reversible": self.reversible
        }
