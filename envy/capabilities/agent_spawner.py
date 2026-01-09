"""
ENVY Agent Spawner v2.0 (Polymorphic)
=====================================
Orchestrates specialized sub-agents using the CORE_AGENTS registry.
Now fully aligned with the Master Blueprint.
"""

import asyncio
import uuid
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..personas.agent_registry import CORE_AGENTS, get_core_agent

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MAX_ITERATIONS = "max_iterations"

@dataclass
class AgentState:
    id: str
    role: str
    name: str
    system_prompt: str
    status: AgentStatus = AgentStatus.PENDING
    task: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Execution stats
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    iterations: int = 0
    max_iterations: int = 10
    
    # State
    messages: List[Dict[str, str]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    children: List[str] = field(default_factory=list)

class AgentSpawner:
    """
    Manages the lifecycle of Polymorphic Agents.
    Uses the single source of truth (agent_registry) for persona definitions.
    """
    
    def __init__(self, llm_client=None, tool_manager=None):
        self.llm_client = llm_client
        self.tool_manager = tool_manager
        self.agents: Dict[str, AgentState] = {}
        self.max_concurrent_agents = 5
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def create_custom_blueprint(self, name, system_prompt, tools=None, max_iterations=5):
        # Compatibility shim for old calls
        return None 

    def list_blueprints(self) -> List[Dict[str, Any]]:
        """List available agents from the Core Registry"""
        return [
            {
                "role": pid,
                "name": p.name,
                "description": p.title,
                "tools": [], # Tools are now universal via ToolManager
                "max_iterations": 10
            }
            for pid, p in CORE_AGENTS.items()
        ]

    async def spawn(
        self,
        role: str,
        task: str,
        context: Dict[str, Any] = None,
        parent_id: Optional[str] = None,
        custom_blueprint=None # Ignored in v2
    ) -> str:
        """
        Spawn a new Polymorphic Agent.
        """
        # Check limits
        running = len([a for a in self.agents.values() if a.status == AgentStatus.RUNNING])
        if running >= self.max_concurrent_agents:
            raise RuntimeError(f"Maximum concurrent agents ({self.max_concurrent_agents}) reached")
        
        # Get Persona from Registry
        persona = get_core_agent(role)
        if not persona:
            # Fallback for old role names
            logger.warning(f"Unknown role '{role}', falling back to 'builder'")
            persona = get_core_agent("builder")

        agent_id = f"agent_{role}_{uuid.uuid4().hex[:8]}"
        
        # Create State
        state = AgentState(
            id=agent_id,
            role=role,
            name=persona.name,
            system_prompt=persona.system_prompt,
            task=task,
            context=context or {}
        )
        
        self.agents[agent_id] = state
        
        if parent_id and parent_id in self.agents:
            self.agents[parent_id].children.append(agent_id)
            
        # Run
        task_coro = self._run_agent(agent_id)
        self._running_tasks[agent_id] = asyncio.create_task(task_coro)
        
        logger.info(f"Spawned {agent_id} ({state.name})")
        await self._emit("agent_spawned", agent_id, state)
        
        return agent_id

    async def _run_agent(self, agent_id: str):
        state = self.agents.get(agent_id)
        if not state: return
        
        state.status = AgentStatus.RUNNING
        state.started_at = datetime.now()
        
        # Build System Prompt with Context
        full_system_prompt = state.system_prompt
        if state.task:
             full_system_prompt += f"\n\nCURRENT MISSION:\n{state.task}"
        if state.context:
             full_system_prompt += f"\n\nCONTEXT:\n{state.context}"
        
        # Add Tool Definitions
        if self.tool_manager:
            full_system_prompt += self.tool_manager.get_system_prompt_addition()

        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": f"Start mission: {state.task}"}
        ]
        state.messages = messages.copy()
        
        try:
            for iteration in range(state.max_iterations):
                state.iterations = iteration + 1
                
                # Check cancellation
                if state.status == AgentStatus.CANCELLED: return

                # LLM Call
                if self.llm_client:
                    response = await self.llm_client.complete(messages)
                    content = response.content
                else:
                    content = "[Mock Response: I need an LLM client to function.]"
                
                messages.append({"role": "assistant", "content": content})
                state.messages.append({"role": "assistant", "content": content})
                
                # Tool Parsing
                # We use a simplified parser here, relying on the ToolManager's robust one if possible
                # But ToolManager executes, doesn't parse. We need to parse here.
                # Re-using the logic from ENVY agent or duplicating simple regex.
                import re, json
                tool_call = None
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
                if json_match:
                     try:
                        data = json.loads(json_match.group(1))
                        if "tool" in data: tool_call = data
                     except: pass
                
                if tool_call:
                    tool_name = tool_call["tool"]
                    tool_args = tool_call.get("args", {})
                    
                    state.status = AgentStatus.WAITING_TOOL
                    try:
                        if self.tool_manager:
                            result = await self.tool_manager.execute(tool_name, tool_args)
                        else:
                            result = "Error: ToolManager not attached."
                    except Exception as e:
                        result = f"Error: {e}"
                    state.status = AgentStatus.RUNNING
                    
                    state.tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": str(result)[:200]
                    })
                    
                    messages.append({
                        "role": "user", 
                        "content": f"TOOL OUTPUT ({tool_name}):\n{result}"
                    })
                    state.messages.append(messages[-1])
                    
                    await self._emit("agent_tool_call", agent_id, tool_name)
                    
                else:
                    # Final result
                    state.result = content
                    state.status = AgentStatus.COMPLETED
                    state.completed_at = datetime.now()
                    await self._emit("agent_completed", agent_id, state)
                    return

            state.status = AgentStatus.MAX_ITERATIONS
            state.result = messages[-1]["content"]
            await self._emit("agent_max_iterations", agent_id, state)
            
        except Exception as e:
            state.status = AgentStatus.FAILED
            state.error = str(e)
            logger.error(f"Agent {agent_id} failed: {e}")

    # --- Utility Methods ---
    def get_status(self, agent_id: str) -> Optional[Dict]:
        state = self.agents.get(agent_id)
        if not state: return None
        return {
            "id": state.id,
            "role": state.role,
            "status": state.status.value,
            "result": state.result,
            "iterations": state.iterations
        }

    async def wait_for(self, agent_id: str, timeout: float = 60.0):
        state = self.agents.get(agent_id)
        if not state: return None
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < timeout:
            if state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED]:
                return state.result
            await asyncio.sleep(0.5)
        return None

    async def cancel(self, agent_id: str):
        state = self.agents.get(agent_id)
        if state and state.status == AgentStatus.RUNNING:
            state.status = AgentStatus.CANCELLED
            if agent_id in self._running_tasks:
                self._running_tasks[agent_id].cancel()
            return True
        return False

    def list_agents(self, status=None):
        return [self.get_status(aid) for aid in self.agents]

    # Events
    def on(self, event: str, handler: Callable) -> None:
        if event not in self._event_handlers: self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    async def _emit(self, event: str, *args) -> None:
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler): await handler(*args)
                else: handler(*args)
            except Exception as e: logger.error(f"Event error: {e}")

# Singleton
_spawner: Optional[AgentSpawner] = None
def get_agent_spawner(llm_client=None, tool_manager=None) -> AgentSpawner:
    global _spawner
    if _spawner is None:
        _spawner = AgentSpawner(llm_client, tool_manager)
    return _spawner