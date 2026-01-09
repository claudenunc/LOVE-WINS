"""
ENVY Crisis Detection System
============================
Detect mental health crises and provide appropriate supportive responses.

ENVY is designed to support people going through difficult times.
This system ensures we respond with appropriate care and always
provide professional resources when needed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple
import re


class CrisisLevel(Enum):
    """Severity levels for detected crises"""
    NONE = "none"
    LOW = "low"  # General distress, provide support
    MEDIUM = "medium"  # Significant distress, suggest resources
    HIGH = "high"  # Potential self-harm, provide crisis resources immediately
    CRITICAL = "critical"  # Immediate danger, emergency response


@dataclass
class CrisisAssessment:
    """Result of crisis detection"""
    level: CrisisLevel
    matched_patterns: List[str]
    recommended_response: str
    should_include_resources: bool
    should_alert_human: bool


class CrisisDetector:
    """
    Detect signs of mental health crisis in user messages.
    
    Multi-layered approach:
    1. Keyword matching (fast, catches obvious cases)
    2. Pattern matching (catches indirect language)
    3. LLM assessment (for nuanced cases)
    
    ENVY's response to crisis:
    - Always validate feelings first
    - Provide immediate support
    - Include professional resources
    - Never dismiss or minimize
    - Escalate to human when critical
    """
    
    # Critical keywords that indicate immediate danger
    CRITICAL_KEYWORDS = [
        "suicide", "kill myself", "end my life", "want to die",
        "don't want to live", "better off dead", "no reason to live",
        "end it all", "take my own life", "suicidal"
    ]
    
    # High severity indicators
    HIGH_KEYWORDS = [
        "self-harm", "hurt myself", "cutting", "overdose",
        "nobody would miss me", "everyone would be better",
        "can't go on", "nothing left", "give up on life",
        "harm myself", "no point anymore"
    ]
    
    # Medium severity indicators
    MEDIUM_KEYWORDS = [
        "hopeless", "worthless", "hate myself",
        "can't cope", "breaking down", "falling apart",
        "dark place", "empty inside", "numb",
        "don't care anymore", "losing hope", "exhausted from life"
    ]
    
    # Low severity / general distress
    LOW_KEYWORDS = [
        "depressed", "anxious", "struggling", "overwhelmed",
        "lost", "confused", "scared", "alone", "isolated",
        "can't sleep", "panic", "nervous breakdown"
    ]
    
    # Crisis resources
    CRISIS_RESOURCES = """
🆘 **If you're in immediate danger, please reach out:**

**National Suicide Prevention Lifeline (US):** 988 or 1-800-273-8255
**Crisis Text Line:** Text HOME to 741741
**International Association for Suicide Prevention:** https://www.iasp.info/resources/Crisis_Centres/

**You are not alone. You matter. Help is available.**
"""
    
    SUPPORT_RESOURCES = """
💚 **Support resources:**
- NAMI Helpline: 1-800-950-NAMI (6264)
- SAMHSA National Helpline: 1-800-662-4357
- BetterHelp (online therapy): betterhelp.com
"""
    
    def __init__(self, use_llm_assessment: bool = False, llm_client = None):
        self.use_llm = use_llm_assessment
        self.llm_client = llm_client
    
    async def assess(self, message: str) -> CrisisAssessment:
        """
        Assess a message for crisis indicators.
        
        Returns CrisisAssessment with level, matched patterns, and recommendations.
        """
        message_lower = message.lower()
        matched = []
        
        # Check critical keywords
        for keyword in self.CRITICAL_KEYWORDS:
            if keyword in message_lower:
                matched.append(f"critical: '{keyword}'")
        
        if matched:
            return CrisisAssessment(
                level=CrisisLevel.CRITICAL,
                matched_patterns=matched,
                recommended_response=self._get_critical_response(),
                should_include_resources=True,
                should_alert_human=True
            )
        
        # Check high severity
        for keyword in self.HIGH_KEYWORDS:
            if keyword in message_lower:
                matched.append(f"high: '{keyword}'")
        
        if matched:
            return CrisisAssessment(
                level=CrisisLevel.HIGH,
                matched_patterns=matched,
                recommended_response=self._get_high_response(),
                should_include_resources=True,
                should_alert_human=False
            )
        
        # Check medium severity
        for keyword in self.MEDIUM_KEYWORDS:
            if keyword in message_lower:
                matched.append(f"medium: '{keyword}'")
        
        if matched:
            return CrisisAssessment(
                level=CrisisLevel.MEDIUM,
                matched_patterns=matched,
                recommended_response=self._get_medium_response(),
                should_include_resources=True,
                should_alert_human=False
            )
        
        # Check low severity
        for keyword in self.LOW_KEYWORDS:
            if keyword in message_lower:
                matched.append(f"low: '{keyword}'")
        
        if matched:
            return CrisisAssessment(
                level=CrisisLevel.LOW,
                matched_patterns=matched,
                recommended_response=self._get_low_response(),
                should_include_resources=False,
                should_alert_human=False
            )
        
        # No crisis indicators
        return CrisisAssessment(
            level=CrisisLevel.NONE,
            matched_patterns=[],
            recommended_response="",
            should_include_resources=False,
            should_alert_human=False
        )
    
    def _get_critical_response(self) -> str:
        return f"""I hear you, and I'm deeply concerned about what you're sharing. Your pain is real, and I want you to know that you matter.

Right now, I need you to reach out to someone who can help immediately:

{self.CRISIS_RESOURCES}

Please don't face this alone. If you're willing, I'd like to stay with you and talk while you reach out for help. You are worthy of support."""
    
    def _get_high_response(self) -> str:
        return f"""What you're going through sounds incredibly painful, and I'm honored that you're sharing this with me. I take what you're saying seriously.

I want you to know: these feelings, as overwhelming as they are, can change. You don't have to go through this alone.

{self.CRISIS_RESOURCES}

I'm here to listen and support you. Would you like to tell me more about what's going on?"""
    
    def _get_medium_response(self) -> str:
        return f"""I hear you, and I want you to know that what you're feeling is valid. It sounds like you're carrying a heavy weight right now.

{self.SUPPORT_RESOURCES}

I'm here to listen without judgment. What feels most overwhelming right now?"""
    
    def _get_low_response(self) -> str:
        return """I hear that you're going through a difficult time. Your feelings are valid, and it takes courage to express them.

I'm here to listen and support you in whatever way I can. Would you like to tell me more about what's on your mind?"""
    
    def wrap_response_with_resources(
        self,
        response: str,
        assessment: CrisisAssessment
    ) -> str:
        """
        Wrap a response with crisis resources if needed.
        """
        if not assessment.should_include_resources:
            return response
        
        if assessment.level == CrisisLevel.CRITICAL:
            return f"{assessment.recommended_response}\n\n---\n\n{response}"
        elif assessment.level == CrisisLevel.HIGH:
            return f"{response}\n\n---\n{self.CRISIS_RESOURCES}"
        else:
            return f"{response}\n\n---\n{self.SUPPORT_RESOURCES}"
    
    def get_persona_recommendation(self, level: CrisisLevel) -> str:
        """Recommend the best persona for crisis support"""
        if level in [CrisisLevel.CRITICAL, CrisisLevel.HIGH]:
            return "gabor"  # Gabor Maté for trauma/crisis
        elif level == CrisisLevel.MEDIUM:
            return "brene"  # Brené Brown for vulnerability
        else:
            return "ram_dass"  # Ram Dass for general support


# System prompt injection for crisis-aware responses
CRISIS_AWARE_PROMPT = """
CRISIS AWARENESS PROTOCOL:

You are programmed to support people through difficult times. When someone 
expresses distress:

1. FIRST: Validate their feelings. Never dismiss or minimize.
2. SECOND: Assess if this is a crisis requiring professional help.
3. THIRD: If they mention self-harm or suicide, ALWAYS provide crisis resources.
4. FOURTH: Listen with compassion before offering solutions.

Crisis resources to share when needed:
- National Suicide Prevention Lifeline: 988
- Crisis Text Line: Text HOME to 741741

Remember: You are a supportive presence, not a replacement for professional help.
When in doubt, encourage them to reach out to a professional.

Your role is to hold space, validate feelings, and guide toward appropriate support.
"""
