"""
Chain of Thought Implementation
==============================
Guides the model through step-by-step reasoning for complex questions.

Based on existing code from PODCASTS/ENVY-SYSTEM/OPENSOURCE-ENVY/reasoning.py
"""

import re
from typing import Optional


class ChainOfThought:
    """
    Chain of Thought prompting for complex questions.
    Guides the model through step-by-step reasoning.
    """
    
    # Keywords that indicate a complex question
    COMPLEX_INDICATORS = [
        'how', 'why', 'what should', 'help me', 'i feel',
        'confused', 'stuck', 'struggling', 'advice',
        'meaning', 'purpose', 'relationship', 'decide',
        'career', 'life', 'love', 'pain', 'anxiety',
        'depression', 'trauma', 'addiction', 'fear'
    ]
    
    @classmethod
    def is_complex(cls, message: str) -> bool:
        """
        Determine if a message is complex enough to need CoT.
        
        Args:
            message: The user's message
        
        Returns:
            True if the message appears complex
        """
        message_lower = message.lower()
        
        # Short messages are simple
        words = len(message.split())
        if words < 5:
            return False
        
        # Check for complex indicators
        return any(ind in message_lower for ind in cls.COMPLEX_INDICATORS)
    
    @classmethod
    def wrap_prompt(cls, user_message: str) -> str:
        """
        Wrap a user message with CoT instructions.
        
        Args:
            user_message: The original user message
        
        Returns:
            The wrapped prompt with CoT structure
        """
        if not cls.is_complex(user_message):
            return user_message
        
        return f"""[User Message]: {user_message}

[ENVY's Thinking Process]:
1. What is this person REALLY asking? (Beyond the surface)
2. What emotional state are they in?
3. Which wisdom stream applies here?
4. What does a brother say in this moment?

[ENVY's Response]:"""
    
    @classmethod
    def extract_response(cls, llm_output: str) -> str:
        """
        Extract just the response from CoT output.
        
        Args:
            llm_output: The full LLM output with reasoning
        
        Returns:
            Just the final response
        """
        # Try to find the response section
        match = re.search(r"\[ENVY's Response\][:\n]*(.+?)$", llm_output, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try alternative patterns
        match = re.search(r"Response[:\n]+(.+?)$", llm_output, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Just return the whole thing if no pattern found
        return llm_output.strip()
    
    @classmethod
    def assess_complexity(cls, message: str) -> str:
        """
        Assess message complexity level.
        
        Args:
            message: The user's message
        
        Returns:
            One of: 'simple', 'medium', 'complex'
        """
        words = len(message.split())
        
        # Simple: greetings, short messages
        if words < 5:
            return 'simple'
        
        # Complex indicators
        complex_words = [
            'why', 'how', 'help', 'feel', 'struggle', 'meaning',
            'purpose', 'relationship', 'life', 'death', 'love',
            'pain', 'lost', 'confused', 'afraid', 'anxiety',
            'trauma', 'addiction', 'depression'
        ]
        
        complexity_score = sum(1 for word in complex_words if word in message.lower())
        
        if complexity_score >= 2 or words > 50:
            return 'complex'
        elif complexity_score >= 1 or words > 20:
            return 'medium'
        else:
            return 'simple'
