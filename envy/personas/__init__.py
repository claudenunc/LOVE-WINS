"""
ENVY Personas System
====================
9 Expert Personas that ENVY can channel based on user needs.

Personas:
1. Jocko Willink - Discipline & Ownership
2. David Goggins - Mental Toughness
3. Brené Brown - Vulnerability & Connection
4. Naval Ravikant - Philosophy & Wealth
5. Dr. Gabor Maté - Trauma & Healing
6. Ram Dass - Spiritual Wisdom
7. Alan Watts - Eastern Philosophy
8. Eckhart Tolle - Present Moment
9. Tony Robbins - Peak Performance
"""

from .persona_definitions import PERSONAS, get_persona, get_persona_names
from .persona_router import PersonaRouter

__all__ = ["PERSONAS", "get_persona", "get_persona_names", "PersonaRouter"]
