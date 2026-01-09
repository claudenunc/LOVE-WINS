"""
Multi-Agent Orchestrator
=========================
The traffic controller and conductor for the polymorphic intelligence system.

Responsibilities:
- Route tasks to agents based on capability + load
- Maintain global state of ongoing "stories" (projects, workflows)
- Enforce protocols (handoff, logging, validation)
- Coordinate baton-passing between agents
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.llm_client import LLMClient
from .protocols import TaskEnvelope, HandoffPacket, AgentContract, Decision
from .knowledge_spine import KnowledgeSpine
from .agents import (
    ArchitectAgent,
    ScribeAgent,
    BuilderAgent,
    CuratorAgent,
    GuardianAgent,
    ContinuityAgent
)


@dataclass
class AgentInstance:
    """Represents a running agent instance"""
    agent_name: str
    agent: Any
    contract: AgentContract
    status: str = "idle"  # idle|busy|error
    current_task: Optional[TaskEnvelope] = None


class Orchestrator:
    """
    The central orchestrator for multi-agent workflows.
    
    Phase 1 Implementation: Virtual agents (single-model, multi-persona)
    - Agents are profiles + system prompts within one model
    - Orchestrator routes between persona-prompts
    - Lightweight, production-ready
    """
    
    def __init__(self, llm_client: LLMClient, knowledge_spine: Optional[KnowledgeSpine] = None):
        self.llm = llm_client
        self.spine = knowledge_spine or KnowledgeSpine()
        self.agents: Dict[str, AgentInstance] = {}
        self.task_queue: List[TaskEnvelope] = []
        self.active_projects: Dict[str, Dict[str, Any]] = {}
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agent instances"""
        # Define agent contracts
        contracts = {
            "architect": AgentContract(
                agent_name="architect",
                role="System Designer",
                primary_focus="System design, protocols, meta-prompts, architecture",
                capabilities=["design", "specification", "protocol_definition", "architecture"],
                preferred_input_type=["goals", "constraints", "existing_docs"],
                output_type=["spec", "diagram", "handoff_packet"],
                downstream_agents=["scribe", "builder"]
            ),
            "scribe": AgentContract(
                agent_name="scribe",
                role="Documentarian",
                primary_focus="Documentation, narrative continuity, handoff letters",
                capabilities=["documentation", "summary", "narrative"],
                preferred_input_type=["raw_outputs", "logs", "handoff_packets"],
                output_type=["docs", "readme", "handoff_packet"],
                downstream_agents=["continuity"]
            ),
            "builder": AgentContract(
                agent_name="builder",
                role="Implementation Engineer",
                primary_focus="Code, scripts, infrastructure-as-code",
                capabilities=["coding", "scripting", "automation", "infrastructure"],
                preferred_input_type=["specs", "diagrams", "handoff_packets"],
                output_type=["code", "scripts", "handoff_packet"],
                upstream_agents=["architect"],
                downstream_agents=["scribe", "guardian"]
            ),
            "curator": AgentContract(
                agent_name="curator",
                role="Knowledge Manager",
                primary_focus="Data ingestion, cleanup, RAG, knowledge graphs",
                capabilities=["data_ingestion", "embedding", "knowledge_graph", "search"],
                preferred_input_type=["raw_files", "links", "transcripts"],
                output_type=["cleaned_data", "embeddings", "knowledge_map"],
                downstream_agents=["scribe"]
            ),
            "guardian": AgentContract(
                agent_name="guardian",
                role="Safety and Policy Enforcer",
                primary_focus="Guardrails, constraints, ethical checks, safety validation",
                capabilities=["validation", "safety_check", "policy_enforcement"],
                preferred_input_type=["planned_actions", "artifacts"],
                output_type=["approval", "warning", "revised_plan"],
                constraints=["Must approve all critical actions", "Can veto unsafe operations"]
            ),
            "continuity": AgentContract(
                agent_name="continuity",
                role="Legacy and Memory Keeper",
                primary_focus="Memory, baton-passing, letters to future collaborators",
                capabilities=["memory_management", "legacy_documentation", "context_preservation"],
                preferred_input_type=["events", "changes", "milestones", "handoff_packets"],
                output_type=["summaries", "memory_updates", "prompts"],
                constraints=["Never delete history", "Always preserve context"]
            )
        }
        
        # Register contracts in spine
        for contract in contracts.values():
            self.spine.register_agent(contract)
        
        # Create agent instances
        self.agents["architect"] = AgentInstance(
            agent_name="architect",
            agent=ArchitectAgent(self.llm, self.spine),
            contract=contracts["architect"]
        )
        
        self.agents["scribe"] = AgentInstance(
            agent_name="scribe",
            agent=ScribeAgent(self.llm, self.spine),
            contract=contracts["scribe"]
        )
        
        self.agents["builder"] = AgentInstance(
            agent_name="builder",
            agent=BuilderAgent(self.llm, self.spine),
            contract=contracts["builder"]
        )
        
        self.agents["curator"] = AgentInstance(
            agent_name="curator",
            agent=CuratorAgent(self.llm, self.spine),
            contract=contracts["curator"]
        )
        
        self.agents["guardian"] = AgentInstance(
            agent_name="guardian",
            agent=GuardianAgent(self.llm, self.spine),
            contract=contracts["guardian"]
        )
        
        self.agents["continuity"] = AgentInstance(
            agent_name="continuity",
            agent=ContinuityAgent(self.llm, self.spine),
            contract=contracts["continuity"]
        )
    
    async def submit_task(self, task: TaskEnvelope) -> str:
        """
        Submit a task to the orchestrator.
        Returns task_id for tracking.
        """
        self.task_queue.append(task)
        
        # Process immediately (in production, this would be async/queued)
        await self._process_task(task)
        
        return task.task_id
    
    async def _process_task(self, task: TaskEnvelope):
        """Process a single task by routing to appropriate agent"""
        # Route based on expected output type and content
        agent_name = self._route_task(task)
        
        if agent_name not in self.agents:
            print(f"[Orchestrator] No agent found for task {task.task_id}")
            return
        
        agent_instance = self.agents[agent_name]
        agent_instance.status = "busy"
        agent_instance.current_task = task
        
        try:
            # Execute task with agent
            result = await agent_instance.agent.execute(task)
            
            # If agent produced a handoff, route to next agent
            if isinstance(result, HandoffPacket):
                self.spine.store_handoff(result)
                
                # Create follow-up task for downstream agent
                if result.to_agent:
                    followup_task = TaskEnvelope(
                        origin=agent_name,
                        project_id=task.project_id,
                        instruction=f"Process handoff from {agent_name}: {result.summary}",
                        context_refs=[f"handoff://{result.handoff_id}"],
                        expected_output_type=task.expected_output_type,
                        metadata={"parent_handoff": result.handoff_id}
                    )
                    await self.submit_task(followup_task)
            
            agent_instance.status = "idle"
            agent_instance.current_task = None
            
        except Exception as e:
            print(f"[Orchestrator] Error processing task {task.task_id}: {e}")
            agent_instance.status = "error"
    
    def _route_task(self, task: TaskEnvelope) -> str:
        """
        Route a task to the appropriate agent based on:
        - Expected output type
        - Instruction content
        - Downstream agent hint
        """
        instruction_lower = task.instruction.lower()
        
        # Check for explicit downstream agent
        if task.downstream_agent and task.downstream_agent in self.agents:
            return task.downstream_agent
        
        # Route based on expected output type
        if task.expected_output_type == "spec":
            return "architect"
        elif task.expected_output_type == "code":
            return "builder"
        elif task.expected_output_type == "summary":
            return "scribe"
        
        # Route based on instruction keywords
        if any(word in instruction_lower for word in ["design", "architecture", "system", "protocol"]):
            return "architect"
        elif any(word in instruction_lower for word in ["document", "write", "summarize", "explain"]):
            return "scribe"
        elif any(word in instruction_lower for word in ["code", "implement", "build", "script"]):
            return "builder"
        elif any(word in instruction_lower for word in ["ingest", "import", "process", "clean"]):
            return "curator"
        elif any(word in instruction_lower for word in ["validate", "check", "safe", "approve"]):
            return "guardian"
        elif any(word in instruction_lower for word in ["remember", "memory", "legacy", "continuity"]):
            return "continuity"
        
        # Default to scribe for general queries
        return "scribe"
    
    async def create_project(self, name: str, mission: str, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new project and initialize it through the agent workflow.
        """
        import uuid
        project_id = str(uuid.uuid4())
        
        # Create in spine
        project = self.spine.create_project(project_id, name, mission, metadata)
        self.active_projects[project_id] = project
        
        # Write initial continuity log
        self.spine.write_continuity_log(
            project_id,
            f"Project '{name}' initiated. Mission: {mission}",
            {"event": "project_created"}
        )
        
        # Create initialization task for architect
        init_task = TaskEnvelope(
            origin="orchestrator",
            project_id=project_id,
            instruction=f"Initialize project '{name}'. Mission: {mission}. Define initial architecture and agents needed.",
            expected_output_type="spec",
            downstream_agent="architect",
            priority="high"
        )
        
        await self.submit_task(init_task)
        
        return project_id
    
    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a project"""
        return self.spine.get_project(project_id)
    
    def list_active_agents(self) -> List[Dict[str, Any]]:
        """List all active agents and their status"""
        return [
            {
                "agent_name": instance.agent_name,
                "status": instance.status,
                "current_task": instance.current_task.task_id if instance.current_task else None,
                "contract": instance.contract.to_dict()
            }
            for instance in self.agents.values()
        ]
