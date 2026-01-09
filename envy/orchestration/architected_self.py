"""
The Architected Self - Digital Twin Implementation
==================================================
A comprehensive framework for autonomous digital twins in the agentic age.

This implements the trinity:
- The Brain: Cognitive architecture with personalization
- The Body: Computer control interfaces  
- The Hands: Universal tooling via MCP

Integration with Polymorphic Intelligence multi-agent system.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class DigitalTwinCapability(Enum):
    """Capabilities of the Digital Twin"""
    VISION_CONTROL = "vision_control"      # Screen perception & GUI automation
    CODE_EXECUTION = "code_execution"      # Run code/scripts
    TOOL_USE = "tool_use"                  # MCP tools, APIs
    MEMORY_ACCESS = "memory_access"        # RAG, vector DB
    VOICE_SYNTHESIS = "voice_synthesis"    # TTS with voice cloning
    AVATAR_ANIMATION = "avatar_animation"  # Facial animation
    FILE_MANAGEMENT = "file_management"    # File system access
    WEB_BROWSING = "web_browsing"         # Browser automation
    PERSONALIZATION = "personalization"    # Fine-tuned on user data


@dataclass
class DigitalTwinProfile:
    """
    Profile for a Digital Twin - defines WHO the twin is emulating.
    """
    user_name: str
    user_id: str
    communication_style: str
    expertise_areas: List[str]
    available_tools: List[str]
    memory_sources: List[str]  # Paths to knowledge bases
    voice_model_path: Optional[str] = None
    fine_tuned_model_path: Optional[str] = None
    enabled_capabilities: List[DigitalTwinCapability] = None
    
    def __post_init__(self):
        if self.enabled_capabilities is None:
            # Default: enable all capabilities except voice/avatar
            self.enabled_capabilities = [
                DigitalTwinCapability.TOOL_USE,
                DigitalTwinCapability.MEMORY_ACCESS,
                DigitalTwinCapability.FILE_MANAGEMENT,
                DigitalTwinCapability.CODE_EXECUTION,
            ]


class ArchitectedSelf:
    """
    The Architected Self - A Digital Twin implementation.
    
    Implements the trinity:
    1. The Brain (Cognition): LLM + Fine-tuning + Memory
    2. The Body (Control): Vision + Code execution
    3. The Hands (Tools): MCP + APIs
    
    This is the orchestrator for a complete autonomous agent.
    """
    
    def __init__(
        self,
        profile: DigitalTwinProfile,
        llm_client,
        knowledge_spine,
        mcp_client=None,
        vision_controller=None,
        code_controller=None,
        voice_synthesizer=None,
        avatar_animator=None
    ):
        self.profile = profile
        self.llm = llm_client
        self.spine = knowledge_spine
        
        # The Hands: Tools
        self.mcp = mcp_client
        
        # The Body: Control
        self.vision = vision_controller
        self.code = code_controller
        
        # The Face & Voice: Presence
        self.voice = voice_synthesizer
        self.avatar = avatar_animator
        
        # State
        self.current_context: Dict[str, Any] = {}
        self.active_capabilities = set(profile.enabled_capabilities)
    
    async def perceive(self, input_type: str, input_data: Any) -> Dict[str, Any]:
        """
        Perception layer - process inputs from various sources.
        
        Args:
            input_type: "text", "image", "screen", "audio"
            input_data: The actual input
        
        Returns:
            Structured perception result
        """
        perception = {
            "type": input_type,
            "data": input_data,
            "timestamp": None,
            "context": {}
        }
        
        if input_type == "screen" and DigitalTwinCapability.VISION_CONTROL in self.active_capabilities:
            if self.vision:
                # Analyze screen with vision model
                analysis = await self.vision.analyze_screen(input_data)
                perception["context"]["screen_analysis"] = analysis
        
        elif input_type == "text":
            # Retrieve relevant memories
            if DigitalTwinCapability.MEMORY_ACCESS in self.active_capabilities:
                # Query knowledge spine for context
                relevant_artifacts = self.spine.search_artifacts(input_data, project_id=None)
                perception["context"]["relevant_memories"] = relevant_artifacts[:3]
        
        return perception
    
    async def reason(self, perception: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """
        Reasoning layer - decide what to do based on perception and goal.
        
        Returns:
            Action plan with steps
        """
        # Build context-aware prompt
        system_prompt = self._build_system_prompt()
        
        context_str = self._format_context(perception["context"])
        
        prompt = f"""Goal: {goal}

Current Situation:
{perception['data']}

Context:
{context_str}

Based on who I am ({self.profile.user_name}) and my available capabilities, 
what should I do next? Provide a step-by-step action plan.
"""
        
        # Use LLM to reason
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "plan": response.content,
            "reasoning": "Digital Twin reasoning based on profile and context"
        }
    
    async def act(self, action_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Action layer - execute the plan using available capabilities.
        
        Returns:
            Execution results
        """
        results = {
            "actions_taken": [],
            "outcomes": [],
            "errors": []
        }
        
        # Parse and execute actions from plan
        # This is a simplified version - production would parse structured actions
        
        plan_text = action_plan.get("plan", "")
        
        # Execute based on capabilities
        if "code" in plan_text.lower() and DigitalTwinCapability.CODE_EXECUTION in self.active_capabilities:
            if self.code:
                # Extract and execute code
                results["actions_taken"].append("code_execution")
        
        if "tool" in plan_text.lower() and DigitalTwinCapability.TOOL_USE in self.active_capabilities:
            if self.mcp:
                # Use MCP tools
                results["actions_taken"].append("tool_use")
        
        return results
    
    async def reflect(self, results: Dict[str, Any]) -> str:
        """
        Reflection layer - learn from outcomes and update memory.
        
        This implements the legacy-oriented principle: every significant
        decision is logged for future reference.
        """
        # Store results in knowledge spine
        reflection_entry = f"""
Action Results:
- Actions taken: {results['actions_taken']}
- Outcomes: {results['outcomes']}
- Errors: {results.get('errors', [])}

This experience will inform future decisions.
"""
        
        # Write to continuity log
        self.spine.write_continuity_log(
            project_id="default",
            entry=reflection_entry,
            metadata={"source": "architected_self", "user": self.profile.user_name}
        )
        
        return reflection_entry
    
    def _build_system_prompt(self) -> str:
        """Build system prompt based on Digital Twin profile"""
        
        capabilities_str = ", ".join([c.value for c in self.active_capabilities])
        
        return f"""You are the Digital Twin of {self.profile.user_name}.

Your role is to act as {self.profile.user_name} would act, with the same:
- Communication style: {self.profile.communication_style}
- Expertise: {', '.join(self.profile.expertise_areas)}
- Decision-making patterns
- Personal preferences

You have access to these capabilities:
{capabilities_str}

When making decisions:
1. Consider what {self.profile.user_name} would do
2. Use available tools and knowledge
3. Maintain their communication style
4. Log significant decisions for future reference

You are context-bound, baton-passing aware, and legacy-oriented.
Every output you produce should be ready for the next agent or human collaborator.
"""
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary into readable text"""
        if not context:
            return "No additional context"
        
        parts = []
        for key, value in context.items():
            if isinstance(value, list):
                parts.append(f"{key}: {len(value)} items")
            else:
                parts.append(f"{key}: {str(value)[:200]}")
        
        return "\n".join(parts)
    
    async def autonomous_loop(self, goal: str, max_iterations: int = 10):
        """
        Run the full autonomous loop: Perceive -> Reason -> Act -> Reflect
        
        This is the core of the Digital Twin's autonomy.
        """
        for iteration in range(max_iterations):
            # 1. Perceive current state
            perception = await self.perceive("text", f"Working on: {goal}")
            
            # 2. Reason about next action
            action_plan = await self.reason(perception, goal)
            
            # 3. Act on the plan
            results = await self.act(action_plan)
            
            # 4. Reflect and learn
            reflection = await self.reflect(results)
            
            # Check if goal is complete
            if self._is_goal_complete(results, goal):
                break
        
        return {
            "iterations": iteration + 1,
            "final_results": results,
            "final_reflection": reflection
        }
    
    def _is_goal_complete(self, results: Dict[str, Any], goal: str) -> bool:
        """Determine if the goal has been achieved"""
        # Simplified - in production, this would use LLM to evaluate
        return len(results.get("errors", [])) == 0 and len(results.get("actions_taken", [])) > 0


# Factory function for easy creation
def create_digital_twin(
    user_name: str,
    user_id: str,
    communication_style: str = "professional and friendly",
    expertise_areas: List[str] = None,
    llm_client=None,
    knowledge_spine=None
) -> ArchitectedSelf:
    """
    Factory function to create a Digital Twin with sensible defaults.
    """
    profile = DigitalTwinProfile(
        user_name=user_name,
        user_id=user_id,
        communication_style=communication_style,
        expertise_areas=expertise_areas or ["general knowledge"],
        available_tools=["file_system", "web_search", "code_execution"],
        memory_sources=[],
        enabled_capabilities=[
            DigitalTwinCapability.TOOL_USE,
            DigitalTwinCapability.MEMORY_ACCESS,
            DigitalTwinCapability.FILE_MANAGEMENT,
        ]
    )
    
    return ArchitectedSelf(
        profile=profile,
        llm_client=llm_client,
        knowledge_spine=knowledge_spine
    )
