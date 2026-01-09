"""
ENVY Configuration System
=========================
Manages all settings with environment variable support.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from typing import Optional


class Settings(BaseSettings):
    """
    ENVY System Configuration
    
    All settings can be overridden via environment variables.
    """
    
    # ===== LLM PROVIDERS =====
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_api_url: str = "https://api.groq.com/openai/v1/chat/completions"
    groq_model: str = "llama-3.3-70b-versatile"
    
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    
    @model_validator(mode='after')
    def clean_api_keys(self):
        if self.groq_api_key:
            self.groq_api_key = self.groq_api_key.strip()
        if self.openrouter_api_key:
            self.openrouter_api_key = self.openrouter_api_key.strip()
        return self

    # ===== DATABASE =====
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    
    # ===== VOICE =====
    elevenlabs_api_key: str = Field(default="", env="ELEVENLABS_API_KEY")
    
    # ===== MODEL SETTINGS =====
    default_model: str = Field(default="llama-3.3-70b-versatile", env="DEFAULT_MODEL")
    fallback_model: str = Field(default="anthropic/claude-3.5-sonnet", env="FALLBACK_MODEL")
    temperature: float = 0.7
    max_tokens: int = 4096
    context_window: int = 8192
    
    # ===== REASONING SETTINGS =====
    enable_tree_of_thoughts: bool = True
    enable_self_critique: bool = True
    enable_chain_of_thought: bool = True
    tot_branches: int = 3
    
    # ===== GUARDRAILS =====
    max_iterations_per_task: int = 10
    max_tokens_per_session: int = Field(default=500000, env="MAX_TOKENS_PER_SESSION")
    max_agent_spawns: int = Field(default=5, env="MAX_AGENT_SPAWNS")
    max_reflexion_attempts: int = Field(default=3, env="MAX_REFLEXION_ATTEMPTS")
    max_daily_cost_usd: float = Field(default=10.0, env="MAX_DAILY_COST_USD")
    max_task_cost_usd: float = 1.0
    session_timeout_minutes: int = 120
    
    # ===== MEMORY SETTINGS =====
    max_history_messages: int = 20
    memory_dir: Path = Path("memory")
    
    # ===== PERSONA SETTINGS =====
    default_persona: str = "omni_link"  # Default to Polymorphic Companion
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def has_groq(self) -> bool:
        """Check if Groq API is configured"""
        return bool(self.groq_api_key)
    
    @property
    def has_openrouter(self) -> bool:
        """Check if OpenRouter API is configured"""
        return bool(self.openrouter_api_key)
    
    @property
    def has_supabase(self) -> bool:
        """Check if Supabase is configured"""
        return bool(self.supabase_url and self.supabase_anon_key)
    
    def validate_and_print(self) -> str:
        """Validate configuration and print status, return primary provider"""
        print("\n" + "=" * 60)
        print("   ENVY Self-Improving AI - Configuration Status")
        print("=" * 60)
        
        if self.has_groq:
            print(f"   [OK] Groq API: Configured ({len(self.groq_api_key)} chars)")
            print(f"       Model: {self.groq_model}")
            print(f"       FREE tier: 14,400 requests/day")
        else:
            print("   [X] Groq API: NOT CONFIGURED")
        
        if self.has_openrouter:
            print(f"   [OK] OpenRouter API: Configured (fallback)")
            print(f"       Model: {self.openrouter_model}")
        else:
            print("   [X] OpenRouter API: NOT CONFIGURED")
        
        if self.has_supabase:
            print(f"   [OK] Supabase: Configured")
        else:
            print("   [X] Supabase: NOT CONFIGURED (using local memory)")
        
        print("=" * 60 + "\n")
        
        if self.has_groq:
            return "groq"
        elif self.has_openrouter:
            return "openrouter"
        else:
            raise ValueError("No LLM provider configured! Set GROQ_API_KEY or OPENROUTER_API_KEY")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings
