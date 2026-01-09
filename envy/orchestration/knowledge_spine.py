"""
Shared Knowledge Spine
======================
The single source of truth for the multi-agent system.

Stores:
- Projects and their state
- Artifacts (code, docs, diagrams)
- Decisions and their rationale
- Agent contracts
- Handoff packets
- Continuity logs
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .protocols import TaskEnvelope, HandoffPacket, AgentContract, Decision


class KnowledgeSpine:
    """
    Shared knowledge repository for multi-agent system.
    Uses file-based storage for simplicity and auditability.
    """
    
    def __init__(self, base_path: str = "./memory/knowledge_spine"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.base_path / "projects").mkdir(exist_ok=True)
        (self.base_path / "artifacts").mkdir(exist_ok=True)
        (self.base_path / "decisions").mkdir(exist_ok=True)
        (self.base_path / "handoffs").mkdir(exist_ok=True)
        (self.base_path / "agents").mkdir(exist_ok=True)
        (self.base_path / "continuity").mkdir(exist_ok=True)
    
    # === Projects ===
    
    def create_project(self, project_id: str, name: str, mission: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new project in the spine"""
        project = {
            "project_id": project_id,
            "name": name,
            "mission": mission,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "agents_involved": [],
            "artifacts": [],
            "decisions": [],
            "handoffs": [],
            "metadata": metadata or {}
        }
        
        project_path = self.base_path / "projects" / f"{project_id}.json"
        with open(project_path, 'w') as f:
            json.dump(project, f, indent=2)
        
        return project
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a project"""
        project_path = self.base_path / "projects" / f"{project_id}.json"
        if not project_path.exists():
            return None
        
        with open(project_path, 'r') as f:
            return json.load(f)
    
    def update_project(self, project_id: str, updates: Dict[str, Any]):
        """Update project fields"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        project.update(updates)
        project["updated_at"] = datetime.utcnow().isoformat()
        
        project_path = self.base_path / "projects" / f"{project_id}.json"
        with open(project_path, 'w') as f:
            json.dump(project, f, indent=2)
        
        return project
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects"""
        projects = []
        for project_file in (self.base_path / "projects").glob("*.json"):
            with open(project_file, 'r') as f:
                projects.append(json.load(f))
        return projects
    
    # === Artifacts ===
    
    def store_artifact(self, project_id: str, artifact_id: str, artifact_type: str, 
                      content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store an artifact (code, doc, diagram)"""
        artifact = {
            "artifact_id": artifact_id,
            "project_id": project_id,
            "type": artifact_type,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        artifact_path = self.base_path / "artifacts" / f"{artifact_id}.json"
        with open(artifact_path, 'w') as f:
            json.dump(artifact, f, indent=2)
        
        # Link to project
        project = self.get_project(project_id)
        if project:
            if artifact_id not in project.get("artifacts", []):
                project.setdefault("artifacts", []).append(artifact_id)
                self.update_project(project_id, {"artifacts": project["artifacts"]})
        
        return artifact
    
    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an artifact"""
        artifact_path = self.base_path / "artifacts" / f"{artifact_id}.json"
        if not artifact_path.exists():
            return None
        
        with open(artifact_path, 'r') as f:
            return json.load(f)
    
    # === Decisions ===
    
    def log_decision(self, decision: Decision):
        """Log a significant decision"""
        decision_path = self.base_path / "decisions" / f"{decision.decision_id}.json"
        with open(decision_path, 'w') as f:
            json.dump(decision.to_dict(), f, indent=2)
        
        # Link to project
        project = self.get_project(decision.project_id)
        if project:
            if decision.decision_id not in project.get("decisions", []):
                project.setdefault("decisions", []).append(decision.decision_id)
                self.update_project(decision.project_id, {"decisions": project["decisions"]})
    
    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a decision"""
        decision_path = self.base_path / "decisions" / f"{decision_id}.json"
        if not decision_path.exists():
            return None
        
        with open(decision_path, 'r') as f:
            return json.load(f)
    
    def get_project_decisions(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all decisions for a project"""
        project = self.get_project(project_id)
        if not project:
            return []
        
        decisions = []
        for decision_id in project.get("decisions", []):
            decision = self.get_decision(decision_id)
            if decision:
                decisions.append(decision)
        
        return decisions
    
    # === Handoffs ===
    
    def store_handoff(self, handoff: HandoffPacket):
        """Store a handoff packet"""
        handoff_path = self.base_path / "handoffs" / f"{handoff.handoff_id}.json"
        with open(handoff_path, 'w') as f:
            json.dump(handoff.to_dict(), f, indent=2)
        
        # Link to project
        project = self.get_project(handoff.project_id)
        if project:
            if handoff.handoff_id not in project.get("handoffs", []):
                project.setdefault("handoffs", []).append(handoff.handoff_id)
                self.update_project(handoff.project_id, {"handoffs": project["handoffs"]})
    
    def get_handoff(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a handoff packet"""
        handoff_path = self.base_path / "handoffs" / f"{handoff_id}.json"
        if not handoff_path.exists():
            return None
        
        with open(handoff_path, 'r') as f:
            return json.load(f)
    
    def get_project_handoffs(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all handoffs for a project"""
        project = self.get_project(project_id)
        if not project:
            return []
        
        handoffs = []
        for handoff_id in project.get("handoffs", []):
            handoff = self.get_handoff(handoff_id)
            if handoff:
                handoffs.append(handoff)
        
        return handoffs
    
    # === Agent Contracts ===
    
    def register_agent(self, contract: AgentContract):
        """Register an agent contract"""
        agent_path = self.base_path / "agents" / f"{contract.agent_name}.json"
        with open(agent_path, 'w') as f:
            json.dump(contract.to_dict(), f, indent=2)
    
    def get_agent_contract(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get an agent's contract"""
        agent_path = self.base_path / "agents" / f"{agent_name}.json"
        if not agent_path.exists():
            return None
        
        with open(agent_path, 'r') as f:
            return json.load(f)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        agents = []
        for agent_file in (self.base_path / "agents").glob("*.json"):
            with open(agent_file, 'r') as f:
                agents.append(json.load(f))
        return agents
    
    # === Continuity Logs (Legacy for Future) ===
    
    def write_continuity_log(self, project_id: str, entry: str, metadata: Dict[str, Any] = None):
        """Write a continuity log entry - a letter to future collaborators"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": project_id,
            "entry": entry,
            "metadata": metadata or {}
        }
        
        log_path = self.base_path / "continuity" / f"{project_id}.jsonl"
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def read_continuity_log(self, project_id: str) -> List[Dict[str, Any]]:
        """Read continuity log for a project"""
        log_path = self.base_path / "continuity" / f"{project_id}.jsonl"
        if not log_path.exists():
            return []
        
        entries = []
        with open(log_path, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.load(line))
        
        return entries
    
    # === Search and Query ===
    
    def search_artifacts(self, query: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Simple text search through artifacts"""
        results = []
        for artifact_file in (self.base_path / "artifacts").glob("*.json"):
            with open(artifact_file, 'r') as f:
                artifact = json.load(f)
                
                # Filter by project if specified
                if project_id and artifact.get("project_id") != project_id:
                    continue
                
                # Simple text search in content
                if query.lower() in artifact.get("content", "").lower():
                    results.append(artifact)
        
        return results
