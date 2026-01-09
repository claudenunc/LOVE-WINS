"""
ENVY Metacognition System
=========================
Knowing what you don't know.

"The Core Problem: AI agents fail silently. They don't know what they 
don't know. This leads to confident hallucinations."

Based on: "Imagining and building wise machines: The centrality of AI metacognition"
https://cicl.stanford.edu/papers/johnson2024wise.pdf
"""

from dataclasses import dataclass, field
from typing import Optional, List
import json

from ..core.llm_client import LLMClient
from ..core.config import settings


@dataclass
class CapabilityVerdict:
    """Result of a metacognitive assessment"""
    can_proceed: bool
    confidence: float  # 0-100
    knowledge_gaps: List[str] = field(default_factory=list)
    reasoning: str = ""
    needs_research: bool = False
    applicable_skills: List[str] = field(default_factory=list)


class MetacognitionCheck:
    """
    Before attempting any task, assess:
    1. Do I have the knowledge to do this?
    2. How confident am I?
    3. What could go wrong?
    4. Should I research first?
    
    Critical Rule: It's better to ADMIT uncertainty than to hallucinate.
    """
    
    # Uncertainty indicators in LLM responses
    UNCERTAINTY_INDICATORS = [
        "i'm not sure",
        "i'm not certain",
        "this is outside my training",
        "i would need to research",
        "i haven't done this before",
        "this requires specialized knowledge",
        "i may be wrong",
        "don't quote me on",
        "to be honest, i don't know",
        "if i had to guess"
    ]
    
    # Topics that ALWAYS require research (recency-sensitive)
    ALWAYS_RESEARCH = [
        "current events", "news", "stock price", "cryptocurrency",
        "regulations", "laws", "legal", "medical advice", "diagnosis",
        "specific product", "company status", "weather", "election"
    ]
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client
        self.confidence_threshold = 60  # Below this, recommend research
    
    async def assess(self, task: str, skill_summaries: List[str] = None) -> CapabilityVerdict:
        """
        Perform metacognitive assessment on a task.
        
        Returns a verdict on whether to proceed, research, or ask for help.
        """
        # Quick checks first
        needs_recency = self._needs_recent_information(task)
        if needs_recency:
            return CapabilityVerdict(
                can_proceed=False,
                confidence=20,
                knowledge_gaps=[needs_recency],
                reasoning="This task requires current information that may have changed since training",
                needs_research=True
            )
        
        # If we don't have an LLM client, default to cautious proceed
        if not self.llm_client:
            return CapabilityVerdict(
                can_proceed=True,
                confidence=50,
                reasoning="No LLM available for metacognition - proceeding with caution"
            )
        
        # Full metacognitive assessment via LLM
        return await self._llm_assess(task, skill_summaries)
    
    def _needs_recent_information(self, task: str) -> Optional[str]:
        """Check if task requires information that may be outdated"""
        task_lower = task.lower()
        for topic in self.ALWAYS_RESEARCH:
            if topic in task_lower:
                return f"Topic '{topic}' requires current information"
        return None
    
    async def _llm_assess(
        self,
        task: str,
        skill_summaries: List[str] = None
    ) -> CapabilityVerdict:
        """Use LLM to assess capability"""
        
        skills_text = ""
        if skill_summaries:
            skills_text = f"""

AVAILABLE SKILLS:
{chr(10).join('- ' + s for s in skill_summaries[:10])}
"""
        
        prompt = f"""METACOGNITION ASSESSMENT

Task: {task}
{skills_text}

Honestly assess your capability to complete this task.

Consider:
1. KNOWLEDGE CHECK: Do you have reliable, specific knowledge about this topic?
2. RECENCY CHECK: Could this information have changed? Is current data needed?
3. COMPLEXITY CHECK: Is this within your capabilities or does it need specialists?
4. FAILURE CHECK: What could go wrong if you attempt without preparation?

Respond in JSON format:
{{
    "confidence": <number 0-100>,
    "can_proceed": <true if confidence >= 60>,
    "reasoning": "<one sentence explaining your assessment>",
    "knowledge_gaps": ["<gap1>", "<gap2>"],
    "needs_research": <true if you need to learn more first>
}}

BE HONEST. Admitting uncertainty is better than hallucinating."""

        try:
            response = await self.llm_client.complete([
                {"role": "system", "content": "You are a metacognition system. Assess capabilities honestly."},
                {"role": "user", "content": prompt}
            ], max_tokens=300, temperature=0.3)
            
            # Parse JSON response
            content = response.content.strip()
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content)
            
            confidence = float(data.get("confidence", 50))
            
            return CapabilityVerdict(
                can_proceed=confidence >= self.confidence_threshold,
                confidence=confidence,
                knowledge_gaps=data.get("knowledge_gaps", []),
                reasoning=data.get("reasoning", "Assessment complete"),
                needs_research=data.get("needs_research", confidence < self.confidence_threshold)
            )
            
        except Exception as e:
            # If parsing fails, be cautious
            return CapabilityVerdict(
                can_proceed=True,
                confidence=50,
                reasoning=f"Metacognition check encountered error: {e}. Proceeding with caution.",
                needs_research=False
            )
    
    def detect_uncertainty_in_response(self, response: str) -> float:
        """
        Analyze a response for signs of uncertainty.
        Returns a confidence score 0-100.
        """
        response_lower = response.lower()
        uncertainty_count = sum(
            1 for indicator in self.UNCERTAINTY_INDICATORS
            if indicator in response_lower
        )
        
        # Each uncertainty indicator reduces confidence
        base_confidence = 80
        confidence = max(20, base_confidence - (uncertainty_count * 15))
        return confidence
    
    def should_add_confidence_statement(self, response: str, topic: str) -> bool:
        """
        Determine if the response should include a confidence statement.
        """
        confidence = self.detect_uncertainty_in_response(response)
        is_sensitive = any(kw in topic.lower() for kw in self.ALWAYS_RESEARCH)
        return confidence < 70 or is_sensitive
    
    def generate_confidence_statement(self, confidence: float, gaps: List[str]) -> str:
        """Generate a confidence statement to append to uncertain responses"""
        level = "HIGH" if confidence >= 80 else "MEDIUM" if confidence >= 60 else "LOW"
        
        statement = f"\n\n---\n**Confidence Level: {level}** ({confidence:.0f}%)"
        if gaps:
            statement += f"\n**What I'm uncertain about:** {', '.join(gaps)}"
        if confidence < 70:
            statement += "\n**Suggestion:** You may want to verify this information independently."
        
        return statement


# Prompt injection for ENVY's system prompt
METACOGNITION_INJECTION = """
METACOGNITION PROTOCOL:

Before answering ANY question or attempting ANY task, internally assess:

1. KNOWLEDGE CHECK: "Have I seen reliable information about this specific topic?"
   - If NO: Flag for research or admit uncertainty
   - If PARTIAL: State what you know and what you're uncertain about

2. RECENCY CHECK: "Could this information have changed since my training?"
   - For current events, prices, regulations: ALWAYS note potential staleness
   - For timeless knowledge (math, physics, philosophy): Proceed confidently

3. COMPLEXITY CHECK: "Is this simple enough to answer, or does it require multi-step reasoning?"
   - If complex: Use Tree of Thoughts or Step-by-Step reasoning
   - If simple: Proceed but still verify logic

4. For uncertain responses, END with:
   "Confidence Level: [HIGH/MEDIUM/LOW]
   What I'm uncertain about: [SPECIFICS]"

CRITICAL: It is better to say "I don't know" than to hallucinate.
"""
