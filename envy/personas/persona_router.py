"""
ENVY Persona Router (Simplified for Single Persona)
=====================================================
This router now defaults to the single Polymorphic Companion persona.
"""

from typing import Optional, List
from dataclasses import dataclass

from .persona_definitions import PERSONAS, Persona


@dataclass
class RoutingResult:
    """Result of persona routing decision"""
    persona_id: str
    persona: Persona
    confidence: float
    reason: str
    matched_keywords: List[str]


class PersonaRouter:
    """
    A simplified router that always returns the Polymorphic Companion.
    """
    
    def __init__(self, llm_client: Optional[object] = None):
        """Initializes the router."""
        self.default_persona_id = "omni_link"
        self.default_persona = PERSONAS[self.default_persona_id]
    
    async def route(
        self,
        message: str,
        use_llm: bool = False,
        context: Optional[List[str]] = None
    ) -> RoutingResult:
        """
        Always returns the Polymorphic Companion persona.
        """
        return RoutingResult(
            persona_id=self.default_persona_id,
            persona=self.default_persona,
            confidence=1.0,
            reason="Defaulting to the single Polymorphic Companion persona.",
            matched_keywords=[]
        )

    def set_default_persona(self, persona_id: str):
        """No-op, as there is only one persona."""
        pass