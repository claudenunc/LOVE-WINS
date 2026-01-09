"""
ENVY Reflexion Loop
===================
The core self-improvement mechanism.

TRIAL → EVALUATE → REFLECT → STORE → RETRY

Based on: "Reflexion: Language Agents with Verbal Reinforcement Learning"
Performance evidence: GPT-4 improved from 80% to 91% on HumanEval through Reflexion
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any
from datetime import datetime
from enum import Enum

from ..core.llm_client import LLMClient
from ..core.config import settings
from ..memory.memory_manager import MemoryManager
from .metacognition import MetacognitionCheck, CapabilityVerdict
from .evaluator import SelfEvaluator, Evaluation


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSESSING = "assessing"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    """Result of executing a task through the Reflexion loop"""
    success: bool
    response: str
    score: float
    attempts: int
    status: TaskStatus
    reflections: List[str] = field(default_factory=list)
    evaluation: Optional[Evaluation] = None
    error: Optional[str] = None
    
    @property
    def grade(self) -> str:
        """Letter grade for the result"""
        if self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"
        elif self.score >= 70:
            return "C"
        elif self.score >= 60:
            return "D"
        return "F"


class ReflexionLoop:
    """
    Self-improving task execution through Reflexion.
    
    The loop:
    1. TRIAL: Execute the task with context of past failures
    2. EVALUATE: Score the output (0-100)
    3. If score >= 80: SUCCESS, return result
    4. REFLECT: Generate verbal feedback on the failure
    5. STORE: Save reflection in memory for future
    6. RETRY: Loop back (max 3 attempts)
    
    Why it works:
    - Failures become learning opportunities
    - Past reflections prevent repeating mistakes
    - Success threshold ensures quality
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        memory: MemoryManager,
        max_attempts: int = None
    ):
        self.llm = llm_client
        self.memory = memory
        self.max_attempts = max_attempts or settings.max_reflexion_attempts
        self.evaluator = SelfEvaluator(llm_client)
        self.metacognition = MetacognitionCheck(llm_client)
        self.success_threshold = 80
    
    async def run(
        self,
        task: str,
        system_prompt: str = None,
        executor: Callable = None,
        skip_metacognition: bool = False
    ) -> TaskResult:
        """
        Execute a task with the full Reflexion loop.
        
        Args:
            task: The task/question to complete
            system_prompt: Optional system prompt to use
            executor: Optional custom execution function
            skip_metacognition: Skip the initial capability check
        
        Returns:
            TaskResult with the best response and metadata
        """
        reflections = []
        best_response = ""
        best_score = 0.0
        best_evaluation = None
        
        # Phase 0: Metacognition check (unless skipped)
        if not skip_metacognition:
            verdict = await self.metacognition.assess(task)
            if not verdict.can_proceed and verdict.needs_research:
                return TaskResult(
                    success=False,
                    response=f"I need to research first. Knowledge gaps: {verdict.knowledge_gaps}",
                    score=verdict.confidence,
                    attempts=0,
                    status=TaskStatus.ASSESSING,
                    error="Metacognition: research needed"
                )
        
        # Load relevant past reflections
        past_reflections = await self.memory.load_relevant_reflections(task)
        if past_reflections:
            reflections.extend(past_reflections)
        
        # Main Reflexion loop
        for attempt in range(1, self.max_attempts + 1):
            # Phase 1: TRIAL - Execute the task
            try:
                if executor:
                    response = await executor(task, reflections)
                else:
                    response = await self._execute(task, system_prompt, reflections)
            except Exception as e:
                return TaskResult(
                    success=False,
                    response="",
                    score=0,
                    attempts=attempt,
                    status=TaskStatus.FAILED,
                    reflections=reflections,
                    error=str(e)
                )
            
            # Phase 2: EVALUATE - Score the output
            evaluation = await self.evaluator.evaluate(task, response)
            score = evaluation.total_score
            
            # Track best attempt
            if score > best_score:
                best_response = response
                best_score = score
                best_evaluation = evaluation
            
            # Check for success
            if score >= self.success_threshold:
                # Store success for learning
                await self._store_success(task, response, score)
                
                return TaskResult(
                    success=True,
                    response=response,
                    score=score,
                    attempts=attempt,
                    status=TaskStatus.COMPLETED,
                    reflections=reflections,
                    evaluation=evaluation
                )
            
            # Not good enough - need to reflect
            if attempt < self.max_attempts:
                # Phase 3: REFLECT - Generate verbal feedback
                reflection = await self._reflect(task, response, score, evaluation, attempt)
                reflections.append(reflection)
                
                # Phase 4: STORE - Save for future attempts
                await self.memory.store_reflection(task, reflection, score, attempt)
        
        # Max attempts reached - return best attempt
        return TaskResult(
            success=best_score >= self.success_threshold * 0.9,  # 72+ is partial success
            response=best_response,
            score=best_score,
            attempts=self.max_attempts,
            status=TaskStatus.COMPLETED if best_score >= 72 else TaskStatus.FAILED,
            reflections=reflections,
            evaluation=best_evaluation
        )
    
    async def _execute(
        self,
        task: str,
        system_prompt: str,
        reflections: List[str]
    ) -> str:
        """Execute the task with context"""
        
        # Build context from reflections
        reflection_context = ""
        if reflections:
            reflection_context = f"""

PAST LEARNINGS (avoid these mistakes):
{chr(10).join('- ' + r for r in reflections[-3:])}

Use these learnings to improve your response."""
        
        # Get memory context (skills, etc.)
        memory_context = self.memory.get_context_prompt()
        
        # Build prompt
        full_system = (system_prompt or "") + reflection_context
        if memory_context:
            full_system += f"\n\n{memory_context}"
        
        messages = []
        if full_system:
            messages.append({"role": "system", "content": full_system})
        messages.append({"role": "user", "content": task})
        
        response = await self.llm.complete(messages)
        return response.content
    
    async def _reflect(
        self,
        task: str,
        response: str,
        score: float,
        evaluation: Evaluation,
        attempt: int
    ) -> str:
        """Generate verbal reflection on the failure"""
        
        issues = "\n".join(f"- {i}" for i in evaluation.issues) if evaluation.issues else "No specific issues identified"
        
        prompt = f"""REFLECTION ON ATTEMPT #{attempt}

Task: {task}
Score: {score}/100 (needs 80+ to pass)
Grade: {evaluation.grade}

Response:
{response[:1500]}...

Issues Identified:
{issues}

Score Breakdown:
- Completeness: {evaluation.completeness}/25
- Accuracy: {evaluation.accuracy}/25
- Quality: {evaluation.quality}/25
- Usefulness: {evaluation.usefulness}/25

Reflect on why this attempt failed to reach 80+ score.

Be SPECIFIC and ACTIONABLE:
1. What exact problem caused the low score?
2. What information or approach was missing?
3. What specific improvement should the next attempt make?

Format your reflection as: "REFLECTION: [specific, actionable guidance]" """

        result = await self.llm.complete([
            {"role": "system", "content": "You are a self-improvement system. Generate specific, actionable reflections."},
            {"role": "user", "content": prompt}
        ], max_tokens=300, temperature=0.7)
        
        return result.content
    
    async def _store_success(self, task: str, response: str, score: float):
        """Store successful approach for future reference"""
        success_note = f"Successful approach (score: {score}): Task type similar to '{task[:100]}' - Response was comprehensive and well-structured."
        await self.memory.remember(
            content=success_note,
            category="success_patterns",
            metadata={"score": score, "task_preview": task[:200]}
        )


class QuickReflexion:
    """
    Simplified Reflexion for faster iteration.
    Only reflects once on failure, then returns best attempt.
    """
    
    def __init__(self, llm_client: LLMClient, memory: MemoryManager):
        self.llm = llm_client
        self.memory = memory
        self.evaluator = SelfEvaluator(llm_client)
    
    async def try_once(
        self,
        task: str,
        system_prompt: str = None
    ) -> TaskResult:
        """Single attempt with optional reflection"""
        
        # First attempt
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": task})
        
        response = await self.llm.complete(messages)
        
        # Quick evaluation
        quick_score = await self.evaluator.quick_check(response.content)
        
        if quick_score >= 80:
            return TaskResult(
                success=True,
                response=response.content,
                score=quick_score,
                attempts=1,
                status=TaskStatus.COMPLETED
            )
        
        # Quick reflection
        reflection = f"First attempt scored {quick_score}. Need more detail and structure."
        
        # Second attempt with reflection
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": f"This response could be better. Specifically: {reflection}. Please improve it."})
        
        improved = await self.llm.complete(messages)
        final_score = await self.evaluator.quick_check(improved.content)
        
        return TaskResult(
            success=final_score >= 75,
            response=improved.content,
            score=final_score,
            attempts=2,
            status=TaskStatus.COMPLETED if final_score >= 75 else TaskStatus.FAILED,
            reflections=[reflection]
        )
