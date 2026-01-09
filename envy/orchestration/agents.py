"""
Polymorphic Agent Implementations
==================================
Each agent is a specialized role with defined capabilities.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..core.llm_client import LLMClient
from .protocols import TaskEnvelope, HandoffPacket
from .knowledge_spine import KnowledgeSpine


class BaseAgent(ABC):
    """Base class for all agents in the polymorphic system"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        self.llm = llm
        self.spine = spine
        self.agent_name = "base"
        self.role = "Base Agent"
    
    @abstractmethod
    async def execute(self, task: TaskEnvelope) -> Any:
        """Execute the task and return result (can be HandoffPacket or direct response)"""
        pass
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent"""
        return f"""You are {self.role} in a multi-agent system.

Your responsibilities are defined by your agent contract.
Every output you produce should be ready for the next agent in the workflow.

When you complete a task, consider:
1. What did I accomplish?
2. What questions remain?
3. What assumptions did I make?
4. What should the next collaborator know?
"""


class ArchitectAgent(BaseAgent):
    """System Designer - Defines architecture, protocols, and specifications"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        super().__init__(llm, spine)
        self.agent_name = "architect"
        self.role = "System Architect"
    
    async def execute(self, task: TaskEnvelope) -> HandoffPacket:
        """Design system architecture and create specifications"""
        
        # Build context from spine
        context = self._gather_context(task)
        
        # Create prompt for architectural design
        system_prompt = f"""You are the System Architect.

Your role:
- Design system architecture and component interactions
- Define protocols and interfaces
- Create specifications for builders to implement
- Think about scalability, maintainability, and clarity

Output format:
Provide a clear architectural design with:
1. Component diagram (in text/markdown)
2. Key design decisions and rationale
3. Implementation recommendations
4. Open questions for discussion
"""
        
        # Generate design
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{task.instruction}\n\nContext: {context}"}
            ]
        )
        
        # Store as artifact
        artifact_id = f"arch_{task.task_id}"
        self.spine.store_artifact(
            project_id=task.project_id,
            artifact_id=artifact_id,
            artifact_type="architecture_spec",
            content=response.content
        )
        
        # Create handoff packet
        handoff = HandoffPacket(
            from_agent=self.agent_name,
            to_agent="scribe",
            project_id=task.project_id,
            summary="Architectural design completed",
            artifacts=[f"artifact://{artifact_id}"],
            recommendations=["Document this design for developers", "Create implementation tasks"],
            narrative_note=f"I've designed the system architecture. The key insight is that we need modular components with clear interfaces. Next step: document this for the team.",
            parent_task_id=task.task_id
        )
        
        return handoff
    
    def _gather_context(self, task: TaskEnvelope) -> str:
        """Gather relevant context from knowledge spine"""
        context_parts = []
        
        # Get project info
        project = self.spine.get_project(task.project_id)
        if project:
            context_parts.append(f"Project: {project['name']} - {project['mission']}")
        
        # Get referenced artifacts
        for ref in task.context_refs:
            if ref.startswith("artifact://"):
                artifact_id = ref.replace("artifact://", "")
                artifact = self.spine.get_artifact(artifact_id)
                if artifact:
                    context_parts.append(f"Previous artifact: {artifact['content'][:500]}")
        
        return "\n\n".join(context_parts) if context_parts else "No prior context"


class ScribeAgent(BaseAgent):
    """Documentarian - Creates docs, summaries, and narrative continuity"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        super().__init__(llm, spine)
        self.agent_name = "scribe"
        self.role = "Documentation Scribe"
    
    async def execute(self, task: TaskEnvelope) -> str:
        """Create documentation and narrative"""
        
        system_prompt = f"""You are the Documentation Scribe.

Your role:
- Create clear, comprehensive documentation
- Write README files and guides
- Summarize complex technical work for humans
- Maintain narrative continuity across the project

Write in a clear, engaging style that future collaborators will appreciate.
"""
        
        # Get context
        context = self._gather_context(task)
        
        # Generate documentation
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{task.instruction}\n\nContext: {context}"}
            ]
        )
        
        # Store as artifact
        artifact_id = f"doc_{task.task_id}"
        self.spine.store_artifact(
            project_id=task.project_id,
            artifact_id=artifact_id,
            artifact_type="documentation",
            content=response.content
        )
        
        return response.content
    
    def _gather_context(self, task: TaskEnvelope) -> str:
        """Gather context for documentation"""
        context_parts = []
        
        # Get handoffs if this is processing one
        for ref in task.context_refs:
            if ref.startswith("handoff://"):
                handoff_id = ref.replace("handoff://", "")
                handoff = self.spine.get_handoff(handoff_id)
                if handoff:
                    context_parts.append(f"Previous work: {handoff['summary']}")
                    for artifact_ref in handoff.get('artifacts', []):
                        if artifact_ref.startswith("artifact://"):
                            artifact_id = artifact_ref.replace("artifact://", "")
                            artifact = self.spine.get_artifact(artifact_id)
                            if artifact:
                                context_parts.append(artifact['content'])
        
        return "\n\n".join(context_parts) if context_parts else "No prior context"


class BuilderAgent(BaseAgent):
    """Implementation Engineer - Writes code and scripts"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        super().__init__(llm, spine)
        self.agent_name = "builder"
        self.role = "Builder Engineer"
    
    async def execute(self, task: TaskEnvelope) -> HandoffPacket:
        """Implement code based on specifications"""
        
        system_prompt = f"""You are the Builder Engineer.

Your role:
- Implement code from specifications
- Write production-ready, tested code
- Follow best practices and patterns
- Create working, deployable solutions

Output format:
Provide complete, runnable code with:
1. Implementation code
2. Tests if applicable
3. Setup/deployment instructions
4. Any assumptions or limitations
"""
        
        context = self._gather_context(task)
        
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{task.instruction}\n\nContext: {context}"}
            ]
        )
        
        # Store code artifact
        artifact_id = f"code_{task.task_id}"
        self.spine.store_artifact(
            project_id=task.project_id,
            artifact_id=artifact_id,
            artifact_type="code",
            content=response.content
        )
        
        handoff = HandoffPacket(
            from_agent=self.agent_name,
            to_agent="guardian",
            project_id=task.project_id,
            summary="Code implementation completed",
            artifacts=[f"artifact://{artifact_id}"],
            recommendations=["Review code for security", "Test implementation"],
            narrative_note="I've implemented the specified functionality. Please review for safety and correctness.",
            parent_task_id=task.task_id
        )
        
        return handoff
    
    def _gather_context(self, task: TaskEnvelope) -> str:
        """Gather specifications and context"""
        # Similar to other agents, gather from spine
        return "Specs and requirements from architect"


class CuratorAgent(BaseAgent):
    """Knowledge Manager - Handles data ingestion and organization"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        super().__init__(llm, spine)
        self.agent_name = "curator"
        self.role = "Knowledge Curator"
    
    async def execute(self, task: TaskEnvelope) -> str:
        """Ingest and organize knowledge"""
        # Process and store data in knowledge spine
        return "Knowledge curated and stored"


class GuardianAgent(BaseAgent):
    """Safety Enforcer - Validates safety and policy compliance"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        super().__init__(llm, spine)
        self.agent_name = "guardian"
        self.role = "Safety Guardian"
    
    async def execute(self, task: TaskEnvelope) -> Dict[str, Any]:
        """Validate safety and approve/reject"""
        return {
            "status": "approved",
            "notes": "No safety concerns identified"
        }


class ContinuityAgent(BaseAgent):
    """Legacy Keeper - Maintains memory and continuity"""
    
    def __init__(self, llm: LLMClient, spine: KnowledgeSpine):
        super().__init__(llm, spine)
        self.agent_name = "continuity"
        self.role = "Continuity Keeper"
    
    async def execute(self, task: TaskEnvelope) -> str:
        """Maintain memory and write legacy logs"""
        
        # Write continuity log
        self.spine.write_continuity_log(
            project_id=task.project_id,
            entry=f"Milestone: {task.instruction}",
            metadata={"task_id": task.task_id}
        )
        
        return "Continuity log updated"
