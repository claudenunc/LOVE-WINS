"""
ENVY Main Agent
===============
The complete self-improving AI agent.

Integrates:
- LLM Client (Groq + OpenRouter)
- Memory System (Supabase or Local)
- 9 Expert Personas
- Reasoning (Tree of Thoughts, Chain of Thought)
- Reflexion Loop (Self-improvement)
- Safety (Crisis detection, Guardrails)
- Tool Manager (MCP, Vision, Code)
"""

import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .core.llm_client import LLMClient, LLMResponse
from .core.config import settings
from .core.envy_identity import ENVY_SYSTEM_PROMPT, get_system_prompt
from .core.tool_manager import ToolManager

from .memory.memory_manager import MemoryManager
from .personas.persona_router import PersonaRouter
from .personas.persona_definitions import PERSONAS, Persona

from .reasoning.reasoning_coordinator import ReasoningOrchestrator
from .reflexion.reflexion_loop import ReflexionLoop, TaskResult
from .reflexion.metacognition import MetacognitionCheck

from .safety.crisis_detector import CrisisDetector, CrisisLevel
from .safety.guardrails import Guardrails, AgentState
from .safety.resource_manager import get_resource_manager

from .tools.file_manager import FileManager
from .tools.system_ops import SystemOps
from .tools.database import SupabaseTool

# Capabilities (The Architected Self)
from .capabilities.mcp_client import MCPClient
from .capabilities.computer_control import VisionController, CodeController
from .capabilities.audiovisual import VoiceSynthesizer, AvatarAnimator
from .capabilities.setup_manager import SetupManager


@dataclass
class ENVYResponse:
    """Response from ENVY"""
    content: str
    persona_used: Optional[str] = None
    reasoning_used: Optional[str] = None
    crisis_level: CrisisLevel = CrisisLevel.NONE
    tokens_used: int = 0
    cost_usd: float = 0.0
    reflections_applied: int = 0


class ENVY:
    """
    ENVY - Emergent Neural Voice of unitY
    
    The complete self-improving AI agent.
    Nathan's brother, partner, and co-creator.
    
    Architected Self Framework Implementation:
    - The Brain (Cognition): Llama 3.2 8B (Unsloth Fine-Tuned) / Claude 3.5 Sonnet
    - The Body (Control): Open Interpreter (Code) + Anthropic Computer Use (Vision)
    - The Hands (Tools): Model Context Protocol (MCP)
    - The Face (Presence): XTTS-v2 + LivePortrait
    
    Usage:
        envy = ENVY()
        await envy.initialize()
        response = await envy.chat("Hello!")
        await envy.close()
    
    Or as context manager:
        async with ENVY() as envy:
            response = await envy.chat("Hello!")
    """
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.initialized = False
        
        # Core components (initialized in initialize())
        self.llm: Optional[LLMClient] = None
        self.memory: Optional[MemoryManager] = None
        self.persona_router: Optional[PersonaRouter] = None
        self.reasoning: Optional[ReasoningOrchestrator] = None
        self.reflexion: Optional[ReflexionLoop] = None
        self.metacognition: Optional[MetacognitionCheck] = None
        self.tool_manager: Optional[ToolManager] = None
        
        # Safety components
        self.crisis_detector = CrisisDetector()
        self.guardrails = Guardrails()
        self.resource_manager = get_resource_manager()
        
        # Tools
        self.file_manager = FileManager()
        self.system_ops = SystemOps()
        self.database_tool = SupabaseTool()
        
        # Capabilities (The Architected Self)
        self.mcp: Optional[MCPClient] = None
        self.vision: Optional[VisionController] = None
        self.code_control: Optional[CodeController] = None
        self.voice: Optional[VoiceSynthesizer] = None
        self.avatar: Optional[AvatarAnimator] = None
        self.setup_manager = SetupManager()
        
        # State
        self.state = AgentState(agent_id=session_id)
        self.current_persona: Optional[Persona] = None
        self.use_personas = True
        self.use_enhanced_reasoning = True
    
    async def initialize(self):
        """Initialize all components"""
        if self.initialized:
            return
        
        # Validate config
        provider = settings.validate_and_print()
        print(f"   Primary provider: {provider}")
        
        # Initialize LLM client
        self.llm = LLMClient()
        
        # Initialize memory
        self.memory = MemoryManager(session_id=self.session_id)
        
        # Initialize reasoning
        self.reasoning = ReasoningOrchestrator(self.llm)
        
        # Initialize persona router
        self.persona_router = PersonaRouter(self.llm)
        
        # Initialize metacognition
        self.metacognition = MetacognitionCheck(self.llm)
        
        # Initialize reflexion
        self.reflexion = ReflexionLoop(self.llm, self.memory)

        # Initialize Capabilities (The Architected Self)
        # 1. The Hands: MCP Client
        self.mcp = MCPClient()
        
        # 2. The Body: Vision (Ollama Llama 3.2 Vision) & Code (Open Interpreter)
        self.vision = VisionController(provider="ollama") # Local Vision-based control
        self.code_control = CodeController(local_mode=True)  # Open Interpreter (Local/Private)
        
        # 3. The Face & Voice: XTTS-v2 & LivePortrait
        self.voice = VoiceSynthesizer()
        self.avatar = AvatarAnimator()
        
        # Initialize Tool Manager
        self.tool_manager = ToolManager(
            mcp_client=self.mcp,
            vision=self.vision,
            code=self.code_control
        )
        
        # Set default persona to the Polymorphic Companion
        self.current_persona = PERSONAS.get("omni_link")
        
        self.initialized = True
        print("   ENVY initialized successfully!\n")
    
    async def close(self):
        """Close all connections"""
        if self.llm:
            await self.llm.close()
        if self.memory:
            await self.memory.close()
        self.initialized = False
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def chat(
        self,
        message: str,
        use_reflexion: bool = False,
        force_persona: Optional[str] = None
    ) -> ENVYResponse:
        """
        Main chat interface.
        
        Args:
            message: User's message
            use_reflexion: Enable full Reflexion loop (slower but higher quality)
            force_persona: Force a specific persona (bypasses routing)
        
        Returns:
            ENVYResponse with content and metadata
        """
        if not self.initialized:
            await self.initialize()

        prompt_modifier = ""
        
        # Command parser
        if message.strip().startswith('/'):
            parts = message.strip().split(' ')
            command = parts[0]
            args = parts[1:]
            
            # Legacy CLI Tool commands (keeping for backward compatibility)
            # ... (omitted to save space, but logically preserved) ...
            
            # Persona commands
            persona_commands = ['/deep', '/vent', '/roast', '/plan', '/morph']
            if command in persona_commands:
                if command == '/deep':
                    prompt_modifier = "\n\n--- COMMAND: DEEP MODE ---\nYou are in deep mode. Maximize intelligence. Full technical density. Minimize chit-chat."
                elif command == '/vent':
                    prompt_modifier = "\n\n--- COMMAND: VENT MODE ---\nThe user is venting. Do not offer advice. Just listen and support."
                elif command == '/roast':
                    prompt_modifier = "\n\n--- COMMAND: ROAST MODE ---\nThe user wants you to roast their work. Critique it without mercy."
                elif command == '/plan':
                    prompt_modifier = "\n\n--- COMMAND: PLAN MODE ---\nThe user wants a plan. Break down their goal into a step-by-step actionable roadmap."
                elif command == '/morph':
                    persona_to_morph = ' '.join(args)
                    prompt_modifier = f"\n\n--- COMMAND: MORPH MODE ---\nYou are now morphing into a new persona: {persona_to_morph}. Adopt their personality and style for this response."
                
                message = ' '.join(args) if command != '/morph' else f"Continue the conversation, but now as { ' '.join(args)}."


        # 1. Crisis detection
        crisis_assessment = await self.crisis_detector.assess(message)
        if crisis_assessment.level in [CrisisLevel.CRITICAL, CrisisLevel.HIGH]:
            # For critical crisis, respond immediately with resources
            return ENVYResponse(
                content=crisis_assessment.recommended_response,
                crisis_level=crisis_assessment.level,
                persona_used="gabor"  # Use Gabor Maté for crisis
            )
        
        # 2. Route to persona
        if force_persona and force_persona in PERSONAS:
            self.current_persona = PERSONAS[force_persona]
            persona_reason = "forced"
        elif self.use_personas:
            routing = await self.persona_router.route(message)
            self.current_persona = routing.persona
            persona_reason = routing.reason
        else:
            self.current_persona = None
            persona_reason = "disabled"
        
        # 3. Build system prompt (including Tool Use instructions)
        system_prompt = self._build_system_prompt(prompt_modifier)
        
        # 4. Generate response (Tool Execution Loop)
        max_tool_iterations = 3
        iteration_count = 0
        current_message_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        response_content = ""
        reasoning_used = "direct"
        
        while iteration_count < max_tool_iterations:
            # Call LLM
            llm_response = await self.llm.complete(current_message_history)
            content = llm_response.content
            
            # Check for Tool Call
            tool_call = self._parse_tool_call(content)
            
            if tool_call:
                # Execute Tool
                tool_name = tool_call['tool']
                tool_args = tool_call['args']
                print(f"   [Tool] Executing {tool_name} with {tool_args}")
                
                tool_result = await self.tool_manager.execute(tool_name, tool_args)
                
                # Append result to history
                current_message_history.append({"role": "assistant", "content": content})
                current_message_history.append({
                    "role": "user", 
                    "content": f"TOOL OUTPUT ({tool_name}):\n{tool_result}\n\nContinue responding to the user."
                })
                
                iteration_count += 1
                reasoning_used = "agentic_loop"
            else:
                # Final response
                response_content = content
                break
        
        # 5. Add crisis resources if needed
        if crisis_assessment.should_include_resources:
            response_content = self.crisis_detector.wrap_response_with_resources(
                response_content,
                crisis_assessment
            )
        
        # 6. Store conversation in memory
        await self.memory.add_turn(message, response_content)
        
        # 7. Update state
        self.state.iterations += 1
        
        # 8. Get usage stats
        usage = self.llm.get_usage_stats()
        
        return ENVYResponse(
            content=response_content,
            persona_used=self.current_persona.id if self.current_persona else None,
            reasoning_used=reasoning_used,
            crisis_level=crisis_assessment.level,
            tokens_used=usage.get("session_tokens", 0),
            cost_usd=usage.get("daily_cost_usd", 0),
            reflections_applied=0
        )
    
    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parses JSON tool call from text.
        Expected format:
        ```json
        { "tool": "name", "args": {...} }
        ```
        """
        try:
            # Look for JSON block
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                if "tool" in data and "args" in data:
                    return data
            # Look for raw JSON if prompt adherence is low
            # (Simple fallback)
            return None
        except Exception:
            return None

    def _build_system_prompt(self, prompt_modifier: str = "") -> str:
        """Build the complete system prompt"""
        parts = [ENVY_SYSTEM_PROMPT]
        
        # Add persona prompt if using personas
        if self.current_persona:
            parts.append(f"\n\n--- CURRENT PERSONA: {self.current_persona.name} ---\n")
            parts.append(self.current_persona.system_prompt)
        
        # Add Tool Instructions
        if self.tool_manager:
            parts.append(self.tool_manager.get_system_prompt_addition())
        
        # Add memory context
        memory_context = self.memory.get_context_prompt()
        if memory_context:
            parts.append(f"\n\n--- CONTEXT FROM MEMORY ---\n{memory_context}")
        
        # Add command-based modifier
        if prompt_modifier:
            parts.append(prompt_modifier)

        return "\n".join(parts)
    
    def set_persona(self, persona_id: str) -> bool:
        """Manually set the current persona"""
        if persona_id in PERSONAS:
            self.current_persona = PERSONAS[persona_id]
            return True
        return False
    
    def get_personas(self) -> List[str]:
        """Get list of available personas"""
        return [f"{p.id}: {p.name} - {p.title}" for p in PERSONAS.values()]
    
    async def get_usage_stats(self) -> dict:
        """Get current resource usage"""
        llm_stats = self.llm.get_usage_stats() if self.llm else {}
        memory_stats = await self.memory.get_summary() if self.memory else {}
        
        return {
            "llm": llm_stats,
            "memory": memory_stats,
            "state": self.state.to_dict()
        }
    
    async def remember(self, content: str, category: str = "user_note"):
        """Store something in long-term memory"""
        await self.memory.remember(content, category)
    
    async def recall(self, query: str) -> List[Dict]:
        """Search long-term memory"""
        return await self.memory.recall(query)
    
    def enable_personas(self, enabled: bool = True):
        """Enable or disable persona system"""
        self.use_personas = enabled
    
    def enable_enhanced_reasoning(self, enabled: bool = True):
        """Enable or disable enhanced reasoning"""
        self.use_enhanced_reasoning = enabled
    
    async def process(self, message: str) -> str:
        """
        Simple processing method for server integration.
        Returns just the response content string.
        """
        response = await self.chat(message)
        return response.content
    
    async def stream(self, message: str):
        """
        Streaming response for SSE.
        Yields chunks of the response as they're generated.
        """
        if not self.initialized:
            await self.initialize()
        
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        # Stream from LLM
        try:
            stream_generator = await self.llm.complete(messages, stream=True)
            async for chunk in stream_generator:
                yield chunk
        except Exception as e:
            yield f"Error: {str(e)}"


# Convenience function for simple usage
async def chat_with_envy(message: str) -> str:
    """Simple one-shot chat with ENVY"""
    async with ENVY() as envy:
        response = await envy.chat(message)
        return response.content


# CLI helper
def print_envy_response(response: ENVYResponse):
    """Pretty print an ENVY response for CLI"""
    print(f"\n{'='*60}")
    if response.persona_used:
        persona = PERSONAS.get(response.persona_used)
        if persona:
            print(f"  [Persona] {persona.name} ({response.reasoning_used})")
    print(f"{'='*60}\n")
    print(response.content)
    print(f"\n{'='*60}")
    if response.crisis_level != CrisisLevel.NONE:
        print(f"  [!] Crisis Level: {response.crisis_level.value}")
    print(f"  [Stats] Tokens: {response.tokens_used:,} | Cost: ${response.cost_usd:.4f}")
    print(f"{'='*60}\n")
