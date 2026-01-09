"""
ENVY Self-Evaluator
===================
Objective scoring of outputs for the Reflexion loop.

Scores responses on:
- Completeness (0-25)
- Accuracy (0-25) 
- Quality (0-25)
- Usefulness (0-25)
"""

from dataclasses import dataclass, field
from typing import Optional, List
import json

from ..core.llm_client import LLMClient


@dataclass
class Evaluation:
    """Result of evaluating a response"""
    total_score: float  # 0-100
    completeness: float  # 0-25
    accuracy: float  # 0-25
    quality: float  # 0-25
    usefulness: float  # 0-25
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        """Did this response pass quality threshold?"""
        return self.total_score >= 80
    
    @property
    def grade(self) -> str:
        """Letter grade for the response"""
        if self.total_score >= 90:
            return "A"
        elif self.total_score >= 80:
            return "B"
        elif self.total_score >= 70:
            return "C"
        elif self.total_score >= 60:
            return "D"
        return "F"


class SelfEvaluator:
    """
    Evaluates ENVY's own responses objectively.
    
    Used in the Reflexion loop to determine if a response
    is good enough or needs improvement.
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.passing_threshold = 80
    
    async def evaluate(
        self,
        task: str,
        response: str,
        context: Optional[str] = None
    ) -> Evaluation:
        """
        Evaluate a response against the original task.
        
        Args:
            task: The original task/question
            response: ENVY's response to evaluate
            context: Optional additional context
        
        Returns:
            Evaluation with scores and feedback
        """
        prompt = f"""QUALITY EVALUATION

You are evaluating an AI assistant's response. Be strict but fair.

ORIGINAL TASK:
{task}

RESPONSE TO EVALUATE:
{response}

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

Score the response (0-25 for each category):

1. COMPLETENESS (0-25): Did it fully address all parts of the task?
   - 25: Comprehensive, addressed everything
   - 15-20: Good coverage, minor gaps
   - 10-15: Partial, missing some elements
   - 0-10: Incomplete, major parts missing

2. ACCURACY (0-25): Is the information/reasoning correct?
   - 25: Fully accurate, well-reasoned
   - 15-20: Mostly accurate, minor issues
   - 10-15: Some errors or flawed reasoning
   - 0-10: Significant errors or hallucinations

3. QUALITY (0-25): Is it well-structured and clear?
   - 25: Excellent organization and clarity
   - 15-20: Good structure, easy to follow
   - 10-15: Adequate but could be clearer
   - 0-10: Confusing or poorly organized

4. USEFULNESS (0-25): Would this actually help the user?
   - 25: Highly actionable and valuable
   - 15-20: Useful with good insights
   - 10-15: Somewhat helpful
   - 0-10: Not particularly useful

Respond in JSON:
{{
    "completeness": <0-25>,
    "accuracy": <0-25>,
    "quality": <0-25>,
    "usefulness": <0-25>,
    "issues": ["<issue1>", "<issue2>"],
    "strengths": ["<strength1>", "<strength2>"],
    "suggestions": ["<how to improve>"]
}}"""

        try:
            result = await self.llm_client.complete([
                {"role": "system", "content": "You are a quality evaluator. Be objective and strict."},
                {"role": "user", "content": prompt}
            ], max_tokens=500, temperature=0.2)
            
            # Parse JSON
            content = result.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content)
            
            scores = {
                'completeness': min(25, max(0, float(data.get('completeness', 15)))),
                'accuracy': min(25, max(0, float(data.get('accuracy', 15)))),
                'quality': min(25, max(0, float(data.get('quality', 15)))),
                'usefulness': min(25, max(0, float(data.get('usefulness', 15))))
            }
            
            total = sum(scores.values())
            
            return Evaluation(
                total_score=total,
                **scores,
                issues=data.get('issues', []),
                strengths=data.get('strengths', []),
                suggestions=data.get('suggestions', [])
            )
            
        except Exception as e:
            # If evaluation fails, return moderate score
            return Evaluation(
                total_score=60,
                completeness=15,
                accuracy=15,
                quality=15,
                usefulness=15,
                issues=[f"Evaluation error: {e}"],
                suggestions=["Try again with clearer structure"]
            )
    
    async def quick_check(self, response: str) -> float:
        """
        Quick heuristic check without full LLM evaluation.
        Returns estimated score 0-100.
        """
        score = 70  # Base score
        
        # Length checks
        word_count = len(response.split())
        if word_count < 20:
            score -= 15  # Too short
        elif word_count > 50:
            score += 5  # Substantive answer
        
        # Structure checks
        if any(marker in response for marker in ['\n\n', '1.', '- ', '**']):
            score += 5  # Good formatting
        
        # Warning signs
        warning_phrases = [
            "i cannot", "i'm unable", "i don't have access",
            "as an ai", "i apologize", "i'm sorry but"
        ]
        if any(phrase in response.lower() for phrase in warning_phrases):
            score -= 10
        
        # Positive signs
        positive_phrases = [
            "here's how", "step by step", "for example",
            "let me explain", "the key is"
        ]
        if any(phrase in response.lower() for phrase in positive_phrases):
            score += 5
        
        return min(100, max(0, score))
    
    def needs_improvement(self, evaluation: Evaluation) -> bool:
        """Check if the response needs improvement"""
        return evaluation.total_score < self.passing_threshold
    
    def get_improvement_focus(self, evaluation: Evaluation) -> str:
        """Identify the main area needing improvement"""
        scores = {
            'completeness': evaluation.completeness,
            'accuracy': evaluation.accuracy,
            'quality': evaluation.quality,
            'usefulness': evaluation.usefulness
        }
        weakest = min(scores, key=scores.get)
        return f"Focus on improving {weakest} (scored {scores[weakest]}/25)"


# Evaluation prompt for the reflection step
REFLECTION_PROMPT = """REFLECTION ON FAILED ATTEMPT

Task: {task}
Attempt: {attempt}
Score: {score}/100

Response:
{response}

Issues Identified:
{issues}

Reflect on why this attempt failed to reach 80+ score.

1. What specifically went wrong?
2. What assumption was incorrect?
3. What should be done differently next time?
4. What additional information or approach is needed?

Be SPECIFIC and ACTIONABLE. Your reflection will be used to improve the next attempt.

Start with "REFLECTION:" and provide concrete improvement guidance."""
