"""
ENVY Safety System
==================
Guardrails, crisis detection, and resource management.

Key Components:
- CrisisDetector: Detect mental health crises and provide appropriate responses
- Guardrails: Prevent infinite loops, budget overruns, and runaway processes
- ResourceManager: Track and limit token/cost usage

"In 2024, a multi-agent system ran for 11 DAYS before anyone noticed - $47,000 in API costs."
We learn from this.
"""

from .crisis_detector import CrisisDetector, CrisisLevel
from .guardrails import Guardrails, GuardrailCheck, EmergencyStop
from .resource_manager import ResourceManager

__all__ = [
    "CrisisDetector",
    "CrisisLevel",
    "Guardrails",
    "GuardrailCheck",
    "EmergencyStop",
    "ResourceManager"
]
