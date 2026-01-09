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
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .core.llm_client import LLMClient, LLMResponse
from .core.config import settings
from .core.envy_identity import ENVY_SYSTEM_PROMPT, get_system_prompt

from .memory.memory_manager import MemoryManager
from .personas.persona_router import PersonaRouter
from .personas.persona_definitions import PERSONAS, Persona

from .reasoning.orchestrator import ReasoningOrchestrator
from .reflexion.reflexion_loop import ReflexionLoop, TaskResult
from .reflexion.metacognition import MetacognitionCheck

from .safety.crisis_detector import CrisisDetector, CrisisLevel
from .safety.guardrails import Guardrails, AgentState
from .safety.resource_manager import get_resource_manager

from .tools.file_manager import FileManager
from .tools.system_ops import SystemOps
from .tools.database import SupabaseTool
import json

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
        self.voice = VoiceSynthesizer(model="xtts-v2")
        self.avatar = AvatarAnimator(engine="liveportrait")
        
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
            
            # Tool commands
            tool_commands = ['/list_files', '/read_file', '/write_file', '/delete_file', '/run_command', '/set_cwd', '/db', 
                             '/tools', '/see', '/code', '/speak', '/animate', '/setup']
            if command in tool_commands:
                tool_output = "Unknown command."
                try:
                    if command == '/setup':
                        tool_output = "Initiating Self-Setup Protocol...\n"
                        tool_output += self.setup_manager.run_full_setup()
                    elif command == '/list_files':
                        path = args[0] if args else "."
                        tool_output = self.file_manager.list_files(path)
                    elif command == '/read_file':
                        if not args:
                            tool_output = "Error: /read_file requires a file path."
                        else:
                            tool_output = self.file_manager.read_file(args[0])
                    elif command == '/write_file':
                        if len(args) < 2:
                            tool_output = "Error: /write_file requires a file path and content."
                        else:
                            path = args[0]
                            content = ' '.join(args[1:])
                            tool_output = self.file_manager.write_file(path, content)
                    elif command == '/delete_file':
                        if not args:
                            tool_output = "Error: /delete_file requires a file path."
                        else:
                            tool_output = self.file_manager.delete_file(args[0])
                    elif command == '/run_command':
                        if not args:
                            tool_output = "Error: /run_command requires a command to execute."
                        else:
                            cmd_to_run = ' '.join(args)
                            tool_output = self.system_ops.run_command(cmd_to_run)
                    elif command == '/set_cwd':
                        if not args:
                            tool_output = "Error: /set_cwd requires a directory path."
                        else:
                            tool_output = self.system_ops.set_cwd(args[0])
                    elif command == '/db':
                        if len(args) < 2:
                            tool_output = "Error: /db requires at least table and operation. Usage: /db <table> <select|insert|update|delete> [query_params_json] [body_json]"
                        else:
                            table = args[0]
                            op = args[1]
                            params = None
                            body = None
                            
                            # Parse optional JSON args
                            # This is tricky with space splitting, so we might need to rejoin
                            rest_args = ' '.join(args[2:])
                            if rest_args:
                                try:
                                    # Try to find two JSON objects or one
                                    # Very basic parsing for now. 
                                    # Improve: Find first {, match to closing }
                                    import json
                                    # Assume one JSON object for now if present
                                    # This is a limitation of simple CLI parsing
                                    # Better: Use regex to split JSONs
                                    # For MVP: Just take one JSON arg as params
                                    if '{' in rest_args:
                                        params = json.loads(rest_args)
                                except json.JSONDecodeError:
                                    tool_output = f"Error: Invalid JSON parameters: {rest_args}"
                                    return ENVYResponse(content=tool_output, persona_used='omni_link', reasoning_used='tool_error')

                            tool_output = self.database_tool.execute_query(table, op, query_params=params, body=body)
                    
                    # New Capabilities Handlers
                    elif command == '/tools':
                        # List MCP tools
                        tools = await self.mcp.list_all_tools()
                        tool_output = f"Available MCP Tools: {len(tools)}\n" + "\n".join([f"- {t['name']} ({t.get('server', 'unknown')})" for t in tools])
                    elif command == '/see':
                        # Vision Control
                        screenshot = self.vision.take_screenshot()
                        tool_output = "Screenshot captured. (Analysis logic pending full VLM integration)"
                    elif command == '/code':
                        if not args:
                            tool_output = "Error: /code requires an instruction."
                        else:
                            instruction = ' '.join(args)
                            tool_output = self.code_control.chat(instruction)
                    elif command == '/speak':
                        if not args:
                            tool_output = "Error: /speak requires text."
                        else:
                            text = ' '.join(args)
                            path = self.voice.speak(text)
                            tool_output = f"Audio generated at: {path}" if path else "Audio generation failed."
                    elif command == '/animate':
                        if not args:
                            tool_output = "Error: /animate requires text."
                        else:
                            text = ' '.join(args)
                            # Generate audio first
                            audio_path = self.voice.speak(text, output_path="temp_anim_audio.wav")
                            if audio_path:
                                video_path = self.avatar.animate(audio_path)
                                tool_output = f"Video generated at: {video_path}" if video_path else "Video generation failed."
                            else:
                                tool_output = "Audio generation failed, cannot animate."

                    return ENVYResponse(content=tool_output, persona_used='omni_link', reasoning_used='tool_command')

                except Exception as e:
                    return ENVYResponse(content=f"Error executing tool command: {e}", persona_used='omni_link', reasoning_used='tool_error')

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
        
        # 3. Build system prompt
        system_prompt = self._build_system_prompt(prompt_modifier)
        
        # 4. Generate response
        if use_reflexion:
            # Full Reflexion loop for high-quality response
            result = await self.reflexion.run(message, system_prompt)
            response_content = result.response
            reasoning_used = "reflexion"
            reflections = len(result.reflections)
        elif self.use_enhanced_reasoning:
            # Use Tree of Thoughts or Chain of Thought based on complexity
            response_content = await self.reasoning.generate_response(message, system_prompt)
            reasoning_used = "enhanced"
            reflections = 0
        else:
            # Direct LLM call
            llm_response = await self.llm.complete([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ])
            response_content = llm_response.content
            reasoning_used = "direct"
            reflections = 0
        
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
            reflections_applied=reflections
        )
    
    def _build_system_prompt(self, prompt_modifier: str = "") -> str:
        """Build the complete system prompt"""
        parts = [ENVY_SYSTEM_PROMPT]
        
        # Add persona prompt if using personas
        if self.current_persona:
            parts.append(f"\n\n--- CURRENT PERSONA: {self.current_persona.name} ---\n")
            parts.append(self.current_persona.system_prompt)
        
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
