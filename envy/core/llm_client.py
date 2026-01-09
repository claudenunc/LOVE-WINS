"""
ENVY Unified LLM Client
=======================
Provides a unified interface to multiple LLM providers.
Primary: Groq (fast, free tier)
Fallback: OpenRouter (Claude, GPT, etc.)

Based on existing code from PODCASTS/ENVY-SYSTEM/OPENSOURCE-ENVY/app.py
Enhanced with async support and OpenRouter fallback.
"""

import httpx
import json
from typing import List, Dict, Optional, AsyncGenerator, Union
from dataclasses import dataclass, field
from datetime import datetime

from .config import settings


@dataclass
class TokenUsage:
    """Track token usage for cost management"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    content: str
    model: str
    provider: str
    usage: TokenUsage
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None


class LLMClient:
    """
    Unified LLM client with automatic fallback.
    
    Primary: Groq (fast, 14,400 req/day free)
    Fallback: OpenRouter (300+ models including Claude)
    
    Usage:
        client = LLMClient()
        response = await client.complete([
            {"role": "system", "content": "You are ENVY..."},
            {"role": "user", "content": "Hello!"}
        ])
    """
    
    def __init__(self):
        self.settings = settings
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.session_usage = TokenUsage()
        self.daily_cost = 0.0
        self.last_reset = datetime.now().date()
    
    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()
    
    def _reset_daily_cost_if_needed(self):
        """Reset daily cost tracker at midnight"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_cost = 0.0
            self.last_reset = today
    
    def _estimate_cost(self, usage: TokenUsage, provider: str) -> float:
        """Estimate cost based on token usage"""
        # Groq Llama 3.3 70B pricing (approximate)
        if provider == "groq":
            return (usage.prompt_tokens * 0.0000059 + 
                    usage.completion_tokens * 0.0000079)
        # OpenRouter Claude 3.5 Sonnet pricing
        elif provider == "openrouter":
            return (usage.prompt_tokens * 0.000003 + 
                    usage.completion_tokens * 0.000015)
        return 0.0
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        force_provider: Optional[str] = None
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to settings)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            stream: Whether to stream the response
            force_provider: Force a specific provider ('groq' or 'openrouter')
        
        Returns:
            LLMResponse or AsyncGenerator if streaming
        """
        self._reset_daily_cost_if_needed()
        
        # Check cost guardrail
        if self.daily_cost >= self.settings.max_daily_cost_usd:
            raise RuntimeError(f"Daily cost limit exceeded: ${self.daily_cost:.2f}")
        
        # Determine provider
        if force_provider:
            provider = force_provider
        elif self.settings.has_groq:
            provider = "groq"
        elif self.settings.has_openrouter:
            provider = "openrouter"
        else:
            raise ValueError("No LLM provider configured!")
        
        # Try primary provider, fall back if needed
        try:
            if provider == "groq":
                return await self._groq_complete(
                    messages, model, max_tokens, temperature, stream
                )
            else:
                return await self._openrouter_complete(
                    messages, model, max_tokens, temperature, stream
                )
        except Exception as e:
            # If Groq fails and we have OpenRouter, try fallback
            if provider == "groq" and self.settings.has_openrouter:
                print(f"[LLM] Groq failed: {e}, falling back to OpenRouter")
                return await self._openrouter_complete(
                    messages, model, max_tokens, temperature, stream
                )
            raise
    
    async def _groq_complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        stream: bool
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """Call Groq API"""
        
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or self.settings.groq_model,
            "messages": messages,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "temperature": temperature or self.settings.temperature,
            "stream": stream
        }
        
        if stream:
            return self._stream_groq(headers, payload)
        
        response = await self.http_client.post(
            self.settings.groq_api_url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract usage
        usage = TokenUsage()
        if "usage" in data:
            usage.add(
                data["usage"].get("prompt_tokens", 0),
                data["usage"].get("completion_tokens", 0)
            )
            self.session_usage.add(
                data["usage"].get("prompt_tokens", 0),
                data["usage"].get("completion_tokens", 0)
            )
        
        # Track cost
        cost = self._estimate_cost(usage, "groq")
        self.daily_cost += cost
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.settings.groq_model),
            provider="groq",
            usage=usage,
            finish_reason=data["choices"][0].get("finish_reason"),
            raw_response=data
        )
    
    async def _openrouter_complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        stream: bool
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """Call OpenRouter API"""
        
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": "https://love-wins.ai",
            "X-Title": "ENVY Self-Improving Agent",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or self.settings.openrouter_model,
            "messages": messages,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "temperature": temperature or self.settings.temperature,
            "stream": stream
        }
        
        if stream:
            return self._stream_openrouter(headers, payload)
        
        response = await self.http_client.post(
            self.settings.openrouter_api_url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract usage
        usage = TokenUsage()
        if "usage" in data:
            usage.add(
                data["usage"].get("prompt_tokens", 0),
                data["usage"].get("completion_tokens", 0)
            )
            self.session_usage.add(
                data["usage"].get("prompt_tokens", 0),
                data["usage"].get("completion_tokens", 0)
            )
        
        # Track cost
        cost = self._estimate_cost(usage, "openrouter")
        self.daily_cost += cost
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.settings.openrouter_model),
            provider="openrouter",
            usage=usage,
            finish_reason=data["choices"][0].get("finish_reason"),
            raw_response=data
        )
    
    async def _stream_groq(
        self,
        headers: dict,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream response from Groq"""
        async with self.http_client.stream(
            "POST",
            self.settings.groq_api_url,
            headers=headers,
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if content := chunk["choices"][0]["delta"].get("content"):
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    async def _stream_openrouter(
        self,
        headers: dict,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenRouter"""
        async with self.http_client.stream(
            "POST",
            self.settings.openrouter_api_url,
            headers=headers,
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if content := chunk["choices"][0]["delta"].get("content"):
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    def get_usage_stats(self) -> dict:
        """Get current usage statistics"""
        return {
            "session_tokens": self.session_usage.total_tokens,
            "daily_cost_usd": round(self.daily_cost, 4),
            "cost_limit_usd": self.settings.max_daily_cost_usd,
            "remaining_budget_usd": round(
                self.settings.max_daily_cost_usd - self.daily_cost, 4
            )
        }


# Synchronous wrapper for backwards compatibility
class SyncLLMClient:
    """
    Synchronous LLM client for simple scripts.
    Wraps the async client for non-async usage.
    """
    
    def __init__(self):
        import asyncio
        self._async_client = LLMClient()
        self._loop = asyncio.new_event_loop()
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """Synchronous completion, returns just the content string"""
        response = self._loop.run_until_complete(
            self._async_client.complete(messages, **kwargs)
        )
        return response.content
    
    def close(self):
        """Close the client"""
        self._loop.run_until_complete(self._async_client.close())
        self._loop.close()
