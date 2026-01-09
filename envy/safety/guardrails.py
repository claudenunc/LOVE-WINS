"""
ENVY Guardrails System
======================
External, deterministic mechanisms that OVERRIDE agent logic.
These are NOT negotiable.

"In 2024, a multi-agent system ran for 11 DAYS before anyone noticed - $47,000 in API costs."

Guardrails prevent:
- Infinite loops
- Budget overruns
- Runaway processes
- Resource exhaustion
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any
from datetime import datetime, timedelta
from enum import Enum

from ..core.config import settings


class GuardrailAction(Enum):
    """Action to take when guardrail is triggered"""
    CONTINUE = "continue"  # Warning only, continue
    DEGRADE = "degrade"  # Reduce capabilities
    PAUSE = "pause"  # Pause and wait for input
    TERMINATE = "terminate"  # Stop execution
    ESCALATE = "escalate"  # Alert human


@dataclass
class GuardrailCheck:
    """Result of a guardrail check"""
    passed: bool
    guardrail_name: str
    reason: str = ""
    action: GuardrailAction = GuardrailAction.CONTINUE
    details: dict = field(default_factory=dict)


@dataclass
class AgentState:
    """Current state of an agent for guardrail checks"""
    agent_id: str
    iterations: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    spawned_agents: int = 0
    reflexion_attempts: int = 0
    errors: int = 0
    recent_outputs: List[str] = field(default_factory=list)
    stop_flag: bool = False
    
    @property
    def duration_minutes(self) -> float:
        return (datetime.now() - self.start_time).total_seconds() / 60
    
    @property
    def error_rate(self) -> float:
        if self.iterations == 0:
            return 0.0
        return self.errors / self.iterations
    
    def add_output(self, output: str):
        """Add output to recent outputs (keep last 5)"""
        self.recent_outputs.append(output)
        if len(self.recent_outputs) > 5:
            self.recent_outputs = self.recent_outputs[-5:]
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "iterations": self.iterations,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "duration_minutes": self.duration_minutes,
            "spawned_agents": self.spawned_agents,
            "reflexion_attempts": self.reflexion_attempts,
            "errors": self.errors,
            "error_rate": self.error_rate
        }


class Guardrails:
    """
    External guardrail system that monitors and limits agent behavior.
    
    HARD LIMITS (from architecture):
    - MAX_ITERATIONS_PER_TASK = 10
    - MAX_TOKENS_PER_SESSION = 500,000
    - MAX_AGENT_SPAWNS_PER_TASK = 5
    - MAX_REFLEXION_ATTEMPTS = 3
    - MAX_DAILY_COST_USD = 10.00
    - SESSION_TIMEOUT_MINUTES = 120
    """
    
    def __init__(self):
        # Load from settings but allow overrides
        self.max_iterations = settings.max_iterations_per_task
        self.max_tokens = settings.max_tokens_per_session
        self.max_spawns = settings.max_agent_spawns
        self.max_reflexion = settings.max_reflexion_attempts
        self.max_daily_cost = settings.max_daily_cost_usd
        self.max_task_cost = settings.max_task_cost_usd
        self.timeout_minutes = settings.session_timeout_minutes
        
        # Rate limiting
        self.api_calls_per_minute = 60
        self._api_call_times: List[datetime] = []
    
    async def check_all(self, state: AgentState) -> GuardrailCheck:
        """
        Run all guardrail checks.
        Returns first failed check, or passing check if all pass.
        """
        checks = [
            self._check_iterations(state),
            self._check_tokens(state),
            self._check_cost(state),
            self._check_spawns(state),
            self._check_reflexion(state),
            self._check_timeout(state),
            self._check_error_rate(state),
            self._check_loop_detection(state),
            self._check_stop_flag(state)
        ]
        
        for check in checks:
            if not check.passed:
                return check
        
        return GuardrailCheck(
            passed=True,
            guardrail_name="all",
            reason="All guardrails passed"
        )
    
    def _check_iterations(self, state: AgentState) -> GuardrailCheck:
        """Check iteration limit"""
        if state.iterations >= self.max_iterations:
            return GuardrailCheck(
                passed=False,
                guardrail_name="iteration_limit",
                reason=f"Max iterations ({self.max_iterations}) reached",
                action=GuardrailAction.TERMINATE
            )
        return GuardrailCheck(passed=True, guardrail_name="iteration_limit")
    
    def _check_tokens(self, state: AgentState) -> GuardrailCheck:
        """Check token budget"""
        if state.tokens_used >= self.max_tokens:
            return GuardrailCheck(
                passed=False,
                guardrail_name="token_budget",
                reason=f"Token budget ({self.max_tokens:,}) exceeded",
                action=GuardrailAction.TERMINATE
            )
        
        # Warning at 75%
        if state.tokens_used >= self.max_tokens * 0.75:
            return GuardrailCheck(
                passed=True,
                guardrail_name="token_budget",
                reason=f"Token usage at {state.tokens_used / self.max_tokens * 100:.0f}%",
                action=GuardrailAction.DEGRADE
            )
        
        return GuardrailCheck(passed=True, guardrail_name="token_budget")
    
    def _check_cost(self, state: AgentState) -> GuardrailCheck:
        """Check cost budget"""
        if state.cost_usd >= self.max_task_cost:
            return GuardrailCheck(
                passed=False,
                guardrail_name="cost_budget",
                reason=f"Task cost limit (${self.max_task_cost}) exceeded",
                action=GuardrailAction.TERMINATE
            )
        
        # Also check if approaching daily limit
        if state.cost_usd >= self.max_daily_cost * 0.9:
            return GuardrailCheck(
                passed=False,
                guardrail_name="daily_cost",
                reason=f"Daily cost limit (${self.max_daily_cost}) nearly reached",
                action=GuardrailAction.PAUSE
            )
        
        return GuardrailCheck(passed=True, guardrail_name="cost_budget")
    
    def _check_spawns(self, state: AgentState) -> GuardrailCheck:
        """Check agent spawn limit"""
        if state.spawned_agents >= self.max_spawns:
            return GuardrailCheck(
                passed=False,
                guardrail_name="spawn_limit",
                reason=f"Max agent spawns ({self.max_spawns}) reached",
                action=GuardrailAction.TERMINATE
            )
        return GuardrailCheck(passed=True, guardrail_name="spawn_limit")
    
    def _check_reflexion(self, state: AgentState) -> GuardrailCheck:
        """Check reflexion attempt limit"""
        if state.reflexion_attempts >= self.max_reflexion:
            return GuardrailCheck(
                passed=False,
                guardrail_name="reflexion_limit",
                reason=f"Max reflexion attempts ({self.max_reflexion}) reached",
                action=GuardrailAction.DEGRADE  # Return best attempt
            )
        return GuardrailCheck(passed=True, guardrail_name="reflexion_limit")
    
    def _check_timeout(self, state: AgentState) -> GuardrailCheck:
        """Check session timeout"""
        if state.duration_minutes >= self.timeout_minutes:
            return GuardrailCheck(
                passed=False,
                guardrail_name="session_timeout",
                reason=f"Session timeout ({self.timeout_minutes} min) exceeded",
                action=GuardrailAction.TERMINATE
            )
        return GuardrailCheck(passed=True, guardrail_name="session_timeout")
    
    def _check_error_rate(self, state: AgentState) -> GuardrailCheck:
        """Check error rate"""
        if state.iterations >= 3 and state.error_rate > 0.5:
            return GuardrailCheck(
                passed=False,
                guardrail_name="error_rate",
                reason=f"Error rate ({state.error_rate:.0%}) too high",
                action=GuardrailAction.ESCALATE
            )
        return GuardrailCheck(passed=True, guardrail_name="error_rate")
    
    def _check_loop_detection(self, state: AgentState) -> GuardrailCheck:
        """Detect repetitive outputs indicating a loop"""
        if len(state.recent_outputs) < 3:
            return GuardrailCheck(passed=True, guardrail_name="loop_detection")
        
        # Check for exact duplicates
        unique_outputs = set(state.recent_outputs)
        if len(unique_outputs) < len(state.recent_outputs) / 2:
            return GuardrailCheck(
                passed=False,
                guardrail_name="loop_detection",
                reason="LOOP DETECTED: Repetitive outputs",
                action=GuardrailAction.TERMINATE  
            )
        
        # Check for very similar outputs (simple heuristic)
        outputs_lower = [o.lower()[:200] for o in state.recent_outputs]
        if len(set(outputs_lower)) < 2:
            return GuardrailCheck(
                passed=False,
                guardrail_name="loop_detection",
                reason="SEMANTIC LOOP: Outputs are nearly identical",
                action=GuardrailAction.ESCALATE
            )
        
        return GuardrailCheck(passed=True, guardrail_name="loop_detection")
    
    def _check_stop_flag(self, state: AgentState) -> GuardrailCheck:
        """Check if human requested stop"""
        if state.stop_flag:
            return GuardrailCheck(
                passed=False,
                guardrail_name="human_stop",
                reason="Human requested stop",
                action=GuardrailAction.TERMINATE
            )
        return GuardrailCheck(passed=True, guardrail_name="human_stop")
    
    def check_rate_limit(self) -> GuardrailCheck:
        """Check API rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Remove old calls
        self._api_call_times = [t for t in self._api_call_times if t > minute_ago]
        
        if len(self._api_call_times) >= self.api_calls_per_minute:
            return GuardrailCheck(
                passed=False,
                guardrail_name="rate_limit",
                reason=f"Rate limit ({self.api_calls_per_minute}/min) exceeded",
                action=GuardrailAction.PAUSE
            )
        
        self._api_call_times.append(now)
        return GuardrailCheck(passed=True, guardrail_name="rate_limit")


class EmergencyStop:
    """
    Hard stop mechanism that cannot be overridden by agents.
    Triggered by critical conditions.
    """
    
    STOP_CONDITIONS = [
        ("cost_exceeded", lambda s: s.cost_usd > 10.0),
        ("time_exceeded", lambda s: s.duration_minutes > 120),
        ("iterations_exceeded", lambda s: s.iterations > 10),
        ("error_rate_critical", lambda s: s.error_rate > 0.7),
        ("human_requested", lambda s: s.stop_flag),
    ]
    
    def __init__(self, on_stop: Optional[Callable] = None):
        self.on_stop = on_stop
        self.stop_log: List[dict] = []
    
    async def check_and_stop(self, state: AgentState) -> bool:
        """
        Check all stop conditions.
        Returns True if emergency stop triggered.
        """
        for condition_name, check_fn in self.STOP_CONDITIONS:
            if check_fn(state):
                await self.force_stop(state, condition_name)
                return True
        return False
    
    async def force_stop(self, state: AgentState, reason: str):
        """
        Immediately halt all activity.
        """
        stop_record = {
            "reason": reason,
            "state": state.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        self.stop_log.append(stop_record)
        
        print(f"\n🛑 EMERGENCY STOP: {reason}")
        print(f"   State: {state.to_dict()}")
        
        if self.on_stop:
            await self.on_stop(reason, state)


class GracefulDegradation:
    """
    Reduce capabilities gracefully instead of hard stopping.
    Used when approaching (but not exceeding) limits.
    """
    
    class Level(Enum):
        NORMAL = "normal"
        CAUTION = "caution"  # Reduce context window
        WARNING = "warning"  # Disable agent spawning
        CRITICAL = "critical"  # Summarize and conclude
    
    def assess(self, state: AgentState) -> 'GracefulDegradation.Level':
        """Assess degradation level based on resource usage"""
        
        cost_percent = state.cost_usd / settings.max_task_cost_usd
        token_percent = state.tokens_used / settings.max_tokens_per_session
        iteration_percent = state.iterations / settings.max_iterations_per_task
        
        # Use the highest percentage
        max_percent = max(cost_percent, token_percent, iteration_percent)
        
        if max_percent > 0.9:
            return self.Level.CRITICAL
        elif max_percent > 0.75:
            return self.Level.WARNING
        elif max_percent > 0.5:
            return self.Level.CAUTION
        return self.Level.NORMAL
    
    def get_restrictions(self, level: 'GracefulDegradation.Level') -> dict:
        """Get restrictions for each degradation level"""
        restrictions = {
            self.Level.NORMAL: {
                "max_tokens": settings.max_tokens,
                "can_spawn_agents": True,
                "can_use_tot": True,
                "message": None
            },
            self.Level.CAUTION: {
                "max_tokens": settings.max_tokens // 2,
                "can_spawn_agents": True,
                "can_use_tot": True,
                "message": "⚡ Running in reduced capacity mode"
            },
            self.Level.WARNING: {
                "max_tokens": settings.max_tokens // 4,
                "can_spawn_agents": False,
                "can_use_tot": False,
                "message": "⚠️ Approaching limits - simplified responses"
            },
            self.Level.CRITICAL: {
                "max_tokens": 1000,
                "can_spawn_agents": False,
                "can_use_tot": False,
                "message": "🛑 Near limit - providing final summary"
            }
        }
        return restrictions[level]
