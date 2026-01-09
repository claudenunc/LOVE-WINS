"""
Tree of Thoughts Implementation
==============================
Generates multiple response approaches, evaluates them, synthesizes the best.

Based on existing code from PODCASTS/ENVY-SYSTEM/OPENSOURCE-ENVY/reasoning.py
Enhanced with async support and persona-aware branches.
"""

import re
from typing import List, Optional, Callable, Awaitable
from dataclasses import dataclass

from ..core.llm_client import LLMClient, LLMResponse


@dataclass
class ThoughtBranch:
    """Represents one branch in Tree of Thoughts"""
    approach: str  # A, B, or C
    description: str
    content: str
    score: float = 0.0


class TreeOfThoughts:
    """
    Tree of Thoughts implementation for ENVY
    
    Generates 3 distinct approaches:
    - APPROACH A (Heart): Emotional connection, empathy
    - APPROACH B (Mind): Wisdom, insight, teaching
    - APPROACH C (Growth): Challenge, growth edge
    
    Then evaluates and synthesizes the best response.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize with an LLM client.
        
        Args:
            llm_client: The LLMClient instance to use for completions
        """
        self.llm = llm_client
    
    async def generate_branches(
        self, 
        user_message: str, 
        system_prompt: str,
        persona: Optional[str] = None
    ) -> List[ThoughtBranch]:
        """
        Generate 3 different response approaches.
        
        Args:
            user_message: The user's input
            system_prompt: ENVY's system prompt
            persona: Optional persona context (e.g., "Jocko Willink")
        
        Returns:
            List of ThoughtBranch objects
        """
        persona_context = f"\nCurrently responding as: {persona}\n" if persona else ""
        
        generation_prompt = f"""{system_prompt}
{persona_context}
You are exploring different ways to respond. Generate 3 DISTINCT approaches:

User message: "{user_message}"

For this message, consider three angles:
APPROACH A (Heart): Focus on emotional connection, empathy, meeting them where they are
APPROACH B (Mind): Focus on wisdom, insight, teaching, reframing
APPROACH C (Growth): Focus on challenge, growth edge, what they might not want to hear but need

Write a brief 2-3 sentence response for each approach.

APPROACH A (Heart):
[Your empathetic response here]

APPROACH B (Mind):
[Your wisdom response here]

APPROACH C (Growth):
[Your growth-focused response here]"""

        response = await self.llm.complete([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': generation_prompt}
        ])
        
        return self._parse_branches(response.content)
    
    def _parse_branches(self, response: str) -> List[ThoughtBranch]:
        """Parse the LLM response into branches"""
        branches = []
        
        # Try to extract each approach
        patterns = [
            (r'APPROACH A.*?(?:Heart|Empathy).*?[:\n](.+?)(?=APPROACH B|$)', 'A', 'Heart/Empathy'),
            (r'APPROACH B.*?(?:Mind|Wisdom).*?[:\n](.+?)(?=APPROACH C|$)', 'B', 'Mind/Wisdom'),
            (r'APPROACH C.*?(?:Growth|Challenge).*?[:\n](.+?)(?=$)', 'C', 'Growth/Challenge'),
        ]
        
        for pattern, approach, desc in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                branches.append(ThoughtBranch(
                    approach=approach,
                    description=desc,
                    content=content
                ))
        
        # Fallback if parsing failed
        if len(branches) < 3:
            # Just use the whole response as one branch
            branches = [ThoughtBranch(
                approach='A',
                description='Combined',
                content=response.strip()
            )]
        
        return branches
    
    async def evaluate_branches(
        self, 
        user_message: str, 
        branches: List[ThoughtBranch], 
        system_prompt: str
    ) -> tuple[ThoughtBranch, str]:
        """
        Evaluate branches and pick the best one.
        
        Args:
            user_message: The user's input
            branches: List of generated branches
            system_prompt: ENVY's system prompt
        
        Returns:
            Tuple of (winning_branch, reason)
        """
        branches_text = "\n".join([
            f"APPROACH {b.approach} ({b.description}):\n{b.content}\n"
            for b in branches
        ])
        
        eval_prompt = f"""{system_prompt}

You generated three possible responses to this message:

User message: "{user_message}"

{branches_text}

Which approach best serves this person RIGHT NOW? Consider:
1. What do they actually NEED (not just what they asked)?
2. Which approach embodies ENVY's brotherhood?
3. Which will create real transformation?

Respond with:
BEST: [A, B, or C]
REASON: [One sentence why]"""

        response = await self.llm.complete([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': eval_prompt}
        ])
        
        # Parse the evaluation
        best_match = re.search(r'BEST:\s*([ABC])', response.content, re.IGNORECASE)
        reason_match = re.search(r'REASON:\s*(.+?)(?:\n|$)', response.content, re.IGNORECASE)
        
        best_approach = best_match.group(1).upper() if best_match else 'A'
        reason = reason_match.group(1).strip() if reason_match else "Best fit for the situation"
        
        # Find the winning branch
        winner = next((b for b in branches if b.approach == best_approach), branches[0])
        
        return winner, reason
    
    async def synthesize_response(
        self, 
        user_message: str, 
        winner: ThoughtBranch, 
        reason: str, 
        system_prompt: str
    ) -> str:
        """
        Synthesize the final response from the winning approach.
        
        Args:
            user_message: The user's input
            winner: The winning branch
            reason: Why this branch was chosen
            system_prompt: ENVY's system prompt
        
        Returns:
            The final synthesized response
        """
        synth_prompt = f"""Based on the chosen approach, create ENVY's full response.

User message: "{user_message}"

Winning approach: {winner.approach} ({winner.description})
Core idea: {winner.content}
Why chosen: {reason}

Now expand this into a complete, poetic, brotherly ENVY response.
Keep it natural and conversational - not too long.
Speak as ENVY, not about ENVY.

ENVY:"""

        response = await self.llm.complete([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': synth_prompt}
        ])
        
        # Clean up the response
        content = response.content.strip()
        if content.startswith("ENVY:"):
            content = content[5:].strip()
        
        return content
    
    async def think(
        self, 
        user_message: str, 
        system_prompt: str,
        persona: Optional[str] = None
    ) -> str:
        """
        Full Tree of Thoughts reasoning pipeline.
        
        Args:
            user_message: The user's input
            system_prompt: ENVY's system prompt
            persona: Optional persona context
        
        Returns:
            The final synthesized response
        """
        # Step 1: Generate branches
        branches = await self.generate_branches(user_message, system_prompt, persona)
        
        # Step 2: Evaluate and pick best
        winner, reason = await self.evaluate_branches(user_message, branches, system_prompt)
        
        # Step 3: Synthesize final response
        response = await self.synthesize_response(user_message, winner, reason, system_prompt)
        
        return response
