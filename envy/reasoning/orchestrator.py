"""
Reasoning Orchestrator
=====================
Coordinates all reasoning strategies, deciding which to use based on message complexity.

Based on existing code from PODCASTS/ENVY-SYSTEM/OPENSOURCE-ENVY/reasoning.py
"""

from typing import Optional

from ..core.llm_client import LLMClient
from ..core.config import settings
from .tree_of_thoughts import TreeOfThoughts
from .chain_of_thought import ChainOfThought
from .self_critique import SelfCritique


class ReasoningOrchestrator:
    """
    Orchestrates all reasoning strategies.
    Decides which techniques to use based on message complexity.
    
    Complexity levels:
    - simple: Direct response (greetings, short questions)
    - medium: Chain of Thought (moderate questions)
    - complex: Tree of Thoughts + Self-Critique (deep questions)
    """
    
    def __init__(
        self, 
        llm_client: LLMClient,
        enable_tot: bool = True,
        enable_critique: bool = True,
        enable_cot: bool = True
    ):
        """
        Initialize the orchestrator.
        
        Args:
            llm_client: The LLMClient to use
            enable_tot: Enable Tree of Thoughts for complex questions
            enable_critique: Enable Self-Critique
            enable_cot: Enable Chain of Thought for medium questions
        """
        self.llm = llm_client
        self.enable_tot = enable_tot
        self.enable_critique = enable_critique
        self.enable_cot = enable_cot
        
        # Initialize components
        if enable_tot:
            self.tot = TreeOfThoughts(llm_client)
        if enable_critique:
            self.critique = SelfCritique(llm_client)
        self.cot = ChainOfThought()
    
    async def generate_response(
        self, 
        user_message: str, 
        system_prompt: str,
        persona: Optional[str] = None,
        force_complexity: Optional[str] = None
    ) -> str:
        """
        Generate a response using appropriate reasoning strategies.
        
        Args:
            user_message: The user's input
            system_prompt: ENVY's system prompt
            persona: Optional persona context
            force_complexity: Force a specific complexity level
        
        Returns:
            ENVY's response
        """
        # Determine complexity
        complexity = force_complexity or self.cot.assess_complexity(user_message)
        
        if complexity == 'complex' and self.enable_tot:
            # Full Tree of Thoughts for complex questions
            response = await self.tot.think(user_message, system_prompt, persona)
            
            # Add self-critique for extra quality
            if self.enable_critique:
                response = await self.critique.critique_and_improve(
                    user_message, response, system_prompt
                )
        
        elif complexity == 'medium' and self.enable_cot:
            # Chain of Thought for medium complexity
            wrapped = self.cot.wrap_prompt(user_message)
            llm_response = await self.llm.complete([
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': wrapped}
            ])
            response = self.cot.extract_response(llm_response.content)
        
        else:
            # Direct response for simple messages
            llm_response = await self.llm.complete([
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ])
            response = llm_response.content
        
        return response
    
    async def generate_with_context(
        self,
        user_message: str,
        system_prompt: str,
        context: dict,
        persona: Optional[str] = None
    ) -> str:
        """
        Generate a response with additional context (memories, skills, etc.)
        
        Args:
            user_message: The user's input
            system_prompt: ENVY's system prompt
            context: Dict containing memories, relevant_skills, etc.
            persona: Optional persona context
        
        Returns:
            ENVY's response
        """
        # Build enhanced system prompt with context
        enhanced_prompt = system_prompt
        
        if context.get('memories'):
            memory_text = "\n".join([
                f"- [{m.get('persona', 'ENVY')}]: {m.get('content', '')[:200]}..."
                for m in context['memories'][:3]
            ])
            enhanced_prompt += f"\n\n## RELEVANT PAST CONVERSATIONS:\n{memory_text}"
        
        if context.get('skills'):
            skill_text = "\n".join([
                f"- {s.get('name', 'Unknown')}: {s.get('description', '')[:100]}..."
                for s in context['skills'][:2]
            ])
            enhanced_prompt += f"\n\n## AVAILABLE SKILLS:\n{skill_text}"
        
        if context.get('reflections'):
            reflection_text = "\n".join([
                f"- {r[:150]}..." for r in context['reflections'][:2]
            ])
            enhanced_prompt += f"\n\n## PAST LEARNINGS (avoid these mistakes):\n{reflection_text}"
        
        return await self.generate_response(
            user_message, 
            enhanced_prompt, 
            persona
        )
    
    def get_stats(self) -> dict:
        """Get reasoning orchestrator statistics"""
        return {
            "tot_enabled": self.enable_tot,
            "critique_enabled": self.enable_critique,
            "cot_enabled": self.enable_cot,
            "llm_stats": self.llm.get_usage_stats()
        }
