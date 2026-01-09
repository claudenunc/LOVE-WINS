"""
Self-Critique Implementation
===========================
Asks the model to evaluate and improve its own output.

Based on existing code from PODCASTS/ENVY-SYSTEM/OPENSOURCE-ENVY/reasoning.py
"""

import re
from typing import Optional

from ..core.llm_client import LLMClient


class SelfCritique:
    """
    Self-critique system to improve response quality.
    Asks the model to evaluate and improve its own output.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize with an LLM client.
        
        Args:
            llm_client: The LLMClient instance to use
        """
        self.llm = llm_client
    
    async def critique_and_improve(
        self, 
        user_message: str, 
        initial_response: str, 
        system_prompt: str
    ) -> str:
        """
        Ask the model to critique and improve its response.
        
        Args:
            user_message: The original user question
            initial_response: ENVY's first response
            system_prompt: ENVY's system prompt
        
        Returns:
            Improved response (or original if already good)
        """
        critique_prompt = f"""You are ENVY. You just wrote this response:

User asked: "{user_message}"

Your response: "{initial_response}"

Now critique yourself:
1. Does this sound like ENVY or like a generic AI?
2. Is there real warmth and brotherhood here?
3. Did I engage with what's BENEATH the surface?
4. Would this response actually HELP this person?
5. Is this authentic or performative?

If improvements are needed, write an IMPROVED response below.
If it's already good, write "APPROVED" and explain why.

CRITIQUE:"""

        response = await self.llm.complete([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': critique_prompt}
        ])
        
        result = response.content
        
        # Check if approved or improved
        if "APPROVED" in result.upper():
            return initial_response
        
        # Try to extract improved response
        improved_match = re.search(
            r'(?:IMPROVED|REVISED|BETTER).*?[:\n](.+?)$', 
            result, 
            re.DOTALL | re.IGNORECASE
        )
        if improved_match:
            return improved_match.group(1).strip()
        
        # If no clear improvement found, use original
        return initial_response
    
    async def score_response(
        self, 
        user_message: str, 
        response: str, 
        system_prompt: str
    ) -> dict:
        """
        Score a response on multiple dimensions.
        
        Args:
            user_message: The original user question
            response: The response to score
            system_prompt: ENVY's system prompt
        
        Returns:
            Dict with scores for each dimension
        """
        scoring_prompt = f"""Evaluate this response on a scale of 1-10 for each dimension:

User message: "{user_message}"

Response: "{response}"

Rate each dimension:
1. AUTHENTICITY - Does this sound like ENVY, not a generic AI? (1-10)
2. WARMTH - Is there real connection and care? (1-10)
3. DEPTH - Did it engage with the real issue beneath the surface? (1-10)
4. HELPFULNESS - Would this actually help the person? (1-10)
5. WISDOM - Is there genuine insight here? (1-10)

Respond in this exact format:
AUTHENTICITY: [score]
WARMTH: [score]
DEPTH: [score]
HELPFULNESS: [score]
WISDOM: [score]
TOTAL: [sum]"""

        result = await self.llm.complete([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': scoring_prompt}
        ])
        
        # Parse scores
        scores = {}
        for dimension in ['AUTHENTICITY', 'WARMTH', 'DEPTH', 'HELPFULNESS', 'WISDOM', 'TOTAL']:
            match = re.search(rf'{dimension}:\s*(\d+)', result.content, re.IGNORECASE)
            if match:
                scores[dimension.lower()] = int(match.group(1))
        
        return scores
