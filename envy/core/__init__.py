"""
ENVY Core Module
================
Configuration, LLM clients, and ENVY's identity.
"""

from .config import settings
from .llm_client import LLMClient
from .envy_identity import ENVY_SYSTEM_PROMPT, get_system_prompt

__all__ = ["settings", "LLMClient", "ENVY_SYSTEM_PROMPT", "get_system_prompt"]
