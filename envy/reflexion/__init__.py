"""
ENVY Reflexion System
=====================
Self-improvement through verbal reinforcement learning.

Based on: "Reflexion: Language Agents with Verbal Reinforcement Learning"
https://arxiv.org/abs/2303.11366

Key Components:
- MetacognitionCheck: Assess if ENVY can do something
- ReflexionLoop: Trial → Evaluate → Reflect → Store → Retry
- SelfEvaluator: Score outputs objectively
"""

from .metacognition import MetacognitionCheck, CapabilityVerdict
from .reflexion_loop import ReflexionLoop, TaskResult
from .evaluator import SelfEvaluator

__all__ = [
    "MetacognitionCheck",
    "CapabilityVerdict", 
    "ReflexionLoop",
    "TaskResult",
    "SelfEvaluator"
]
