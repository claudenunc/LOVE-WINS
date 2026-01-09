"""
ENVY Resource Manager
=====================
Track and manage resource consumption (tokens, costs, time).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime, date
from ..core.config import settings


@dataclass
class ResourceUsage:
    """Track resource usage"""
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    api_calls: int = 0


@dataclass
class DailyUsage:
    """Daily resource tracking"""
    date: date
    total_tokens: int = 0
    total_cost: float = 0.0
    total_requests: int = 0


class ResourceManager:
    """
    Track and limit resource consumption.
    Provides allocation, usage reporting, and budget enforcement.
    """
    
    def __init__(self):
        self.daily_usage: Dict[str, DailyUsage] = {}
        self.session_usage: Dict[str, ResourceUsage] = {}
        self.max_daily_cost = settings.max_daily_cost_usd
        self.max_tokens_session = settings.max_tokens_per_session
    
    def _get_today_key(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")
    
    def _ensure_daily_record(self):
        """Ensure today's record exists"""
        key = self._get_today_key()
        if key not in self.daily_usage:
            self.daily_usage[key] = DailyUsage(date=datetime.now().date())
    
    def allocate(
        self,
        agent_id: str,
        estimated_tokens: int,
        estimated_cost: float
    ) -> bool:
        """
        Request resource allocation before consuming.
        Returns True if resources available, False if would exceed budget.
        """
        self._ensure_daily_record()
        today = self.daily_usage[self._get_today_key()]
        
        # Check daily cost limit
        if today.total_cost + estimated_cost > self.max_daily_cost:
            return False
        
        # Check session token limit
        session = self.session_usage.get(agent_id, ResourceUsage())
        if session.tokens_used + estimated_tokens > self.max_tokens_session:
            return False
        
        return True
    
    def report_usage(
        self,
        agent_id: str,
        tokens: int,
        cost: float,
        duration: float = 0.0
    ):
        """Report actual usage after operation completes"""
        self._ensure_daily_record()
        
        # Update daily totals
        today = self.daily_usage[self._get_today_key()]
        today.total_tokens += tokens
        today.total_cost += cost
        today.total_requests += 1
        
        # Update session totals
        if agent_id not in self.session_usage:
            self.session_usage[agent_id] = ResourceUsage()
        
        session = self.session_usage[agent_id]
        session.tokens_used += tokens
        session.cost_usd += cost
        session.duration_seconds += duration
        session.api_calls += 1
    
    def get_remaining_budget(self) -> float:
        """Get remaining daily budget in USD"""
        self._ensure_daily_record()
        today = self.daily_usage[self._get_today_key()]
        return max(0, self.max_daily_cost - today.total_cost)
    
    def get_remaining_tokens(self, agent_id: str) -> int:
        """Get remaining session tokens for an agent"""
        session = self.session_usage.get(agent_id, ResourceUsage())
        return max(0, self.max_tokens_session - session.tokens_used)
    
    def get_daily_summary(self) -> dict:
        """Get today's usage summary"""
        self._ensure_daily_record()
        today = self.daily_usage[self._get_today_key()]
        return {
            "date": today.date.isoformat(),
            "total_tokens": today.total_tokens,
            "total_cost_usd": round(today.total_cost, 4),
            "total_requests": today.total_requests,
            "remaining_budget_usd": round(self.get_remaining_budget(), 4),
            "budget_used_percent": round(today.total_cost / self.max_daily_cost * 100, 1)
        }
    
    def get_session_summary(self, agent_id: str) -> dict:
        """Get session summary for an agent"""
        session = self.session_usage.get(agent_id, ResourceUsage())
        return {
            "agent_id": agent_id,
            "tokens_used": session.tokens_used,
            "cost_usd": round(session.cost_usd, 4),
            "duration_seconds": round(session.duration_seconds, 2),
            "api_calls": session.api_calls,
            "remaining_tokens": self.get_remaining_tokens(agent_id)
        }
    
    def estimate_cost(self, tokens: int, model: str = "groq") -> float:
        """Estimate cost for a given number of tokens"""
        # Approximate pricing (per 1K tokens)
        pricing = {
            "groq": {"input": 0.0000059, "output": 0.0000079},
            "claude": {"input": 0.000003, "output": 0.000015},
            "gpt-4": {"input": 0.00003, "output": 0.00006},
            "openrouter": {"input": 0.000003, "output": 0.000015}  # Default to Claude pricing
        }
        
        prices = pricing.get(model, pricing["openrouter"])
        # Assume 30% input, 70% output
        return (tokens * 0.3 * prices["input"] + tokens * 0.7 * prices["output"])
    
    def reset_session(self, agent_id: str):
        """Reset session tracking for an agent"""
        if agent_id in self.session_usage:
            del self.session_usage[agent_id]
    
    def is_budget_critical(self) -> bool:
        """Check if we're in critical budget territory (>90% used)"""
        self._ensure_daily_record()
        today = self.daily_usage[self._get_today_key()]
        return today.total_cost >= self.max_daily_cost * 0.9
    
    def format_usage_message(self) -> str:
        """Format a human-readable usage message"""
        summary = self.get_daily_summary()
        return f"""📊 Resource Usage:
• Tokens: {summary['total_tokens']:,}
• Cost: ${summary['total_cost_usd']:.4f} / ${self.max_daily_cost:.2f}
• Requests: {summary['total_requests']}
• Budget Used: {summary['budget_used_percent']}%"""


# Global resource manager instance
resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager"""
    return resource_manager
