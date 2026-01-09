"""
ENVY Configuration System v2.0
==============================
Manages all settings with environment variable support.
Fully integrated with the Master Blueprint and External Services.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from typing import Optional
from urllib.parse import urlparse


class Settings(BaseSettings):
    """
    ENVY System C    python -c "from envy.core.config import settings; print('GROQ:', settings.has_groq, 'OPENROUTER:', settings.has_openrouter, 'DIFY:', settings.has_dify)"onfiguration
    
    All settings can be overridden via environment variables.
    """
    
    # ==========================================
    # 1. CORE INTELLIGENCE (LLMs)
    # ==========================================
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_api_url: str = "https://api.groq.com/openai/v1/chat/completions"
    groq_model: str = "llama-3.3-70b-versatile"
    
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    openrouter_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    
    huggingface_token: str = Field(default="", env="HUGGINGSFACE_ACCESS_TOKEN")
    
    # ==========================================
    # 2. KNOWLEDGE SPINE (Database & Dify)
    # ==========================================
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    
    dify_url: str = Field(default="", env="DIFY_URL")
    dify_api_key: str = Field(default="", env="DIFY_INTAKE_API_KEY")
    dify_dataset_api_key: str = Field(default="", env="DIFY_DATASET_API_KEY")

    # ==========================================
    # 3. IDENTITY & SOCIAL
    # ==========================================
    envy_email: str = Field(default="", env="ENVY_EMAIL")
    envy_email_password: str = Field(default="", env="ENVY_EMAIL_PASSWORD")
    
    github_client_id: str = Field(default="", env="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", env="GITHUB_CLIENT_SECRET")
    
    youtube_api_key: str = Field(default="", env="YOUTUBE_API_KEY")
    youtube_channel_id: str = Field(default="", env="YOUTUBE_CHANNEL_ID")

    # ==========================================
    # 4. CAPABILITIES
    # ==========================================
    elevenlabs_api_key: str = Field(default="", env="ELEVENLABS_API_KEY")
    serp_api_key: str = Field(default="", env="SERP_API")
    hostinger_api_key: str = Field(default="", env="HOSTINGER_API")
    runpod_api_key: str = Field(default="", env="RUNPOD_API")
    printful_api_key: str = Field(default="", env="PRINTFUL_API_KEY")

    # ==========================================
    # 5. FINANCE
    # ==========================================
    stripe_secret_key: str = Field(default="", env="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(default="", env="STRIPE_PUBLISHABLE_KEY")
    gumroad_access_token: str = Field(default="", env="GUMROAD_ACCESS_TOKEN")
    
    # ==========================================
    # SYSTEM DEFAULTS
    # ==========================================
    default_model: str = Field(default="llama-3.3-70b-versatile", env="DEFAULT_MODEL")
    max_tokens: int = 4096
    # LLM generation parameters
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    top_p: float = Field(default=1.0, env="TOP_P")
    # Resource limits
    max_daily_cost_usd: float = Field(default=10.0, env="MAX_DAILY_COST_USD")
    max_tokens_per_session: int = Field(default=20000, env="MAX_TOKENS_PER_SESSION")
    # Guardrail / agent limits
    max_iterations_per_task: int = Field(default=10, env="MAX_ITERATIONS_PER_TASK")
    max_agent_spawns: int = Field(default=5, env="MAX_AGENT_SPAWNS")
    max_reflexion_attempts: int = Field(default=3, env="MAX_REFLEXION_ATTEMPTS")
    max_task_cost_usd: float = Field(default=5.0, env="MAX_TASK_COST_USD")
    session_timeout_minutes: int = Field(default=120, env="SESSION_TIMEOUT_MINUTES")
    
    @model_validator(mode='after')
    def clean_api_keys(self):
        if self.groq_api_key: self.groq_api_key = self.groq_api_key.strip()
        if self.openrouter_api_key: self.openrouter_api_key = self.openrouter_api_key.strip()
        # Strip whitespace/newlines from service URLs to avoid InvalidURL errors
        if self.supabase_url: self.supabase_url = self.supabase_url.strip()
        if self.groq_api_url: self.groq_api_url = self.groq_api_url.strip()
        if self.openrouter_api_url: self.openrouter_api_url = self.openrouter_api_url.strip()
        if self.dify_url: self.dify_url = self.dify_url.strip()
        # Validate common service URLs to fail fast on malformed values
        def _valid_url(v: Optional[str]) -> bool:
            if not v:
                return True
            parsed = urlparse(v)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)

        urls_to_check = {
            'supabase_url': self.supabase_url,
            'groq_api_url': self.groq_api_url,
            'openrouter_api_url': self.openrouter_api_url,
            'dify_url': self.dify_url,
        }

        for name, val in urls_to_check.items():
            if val and not _valid_url(val):
                raise ValueError(f"Invalid URL for {name}: {val}")

        return self
    
    @property
    def has_groq(self) -> bool: return bool(self.groq_api_key)
    
    @property
    def has_openrouter(self) -> bool: return bool(self.openrouter_api_key)
    
    @property
    def has_supabase(self) -> bool: return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def has_dify(self) -> bool: return bool(self.dify_url and self.dify_api_key)

    @property
    def has_github(self) -> bool: return bool(self.github_client_id and self.github_client_secret)
    
    def validate_and_print(self) -> str:
        """Validate configuration and print status"""
        print("\n" + "=" * 60)
        print("   ENVY v6.0 - Configuration Status")
        print("=" * 60 + "\n")
        
        print(f"   [LLM] Groq: {'✅' if self.has_groq else '❌'}")
        print(f"   [LLM] OpenRouter: {'✅' if self.has_openrouter else '❌'}")
        print(f"   [MEM] Supabase: {'✅' if self.has_supabase else '❌'}")
        print(f"   [KNOW] Dify: {'✅' if self.has_dify else '❌'}")
        print(f"   [CODE] GitHub: {'✅' if self.has_github else '❌'}")
        print(f"   [HOST] Hostinger: {'✅' if self.hostinger_api_key else '❌'}")
        print(f"   [PAY] Stripe: {'✅' if self.stripe_secret_key else '❌'}")
        
        print("=" * 60 + "\n")
        
        if self.has_groq: return "groq"
        elif self.has_openrouter: return "openrouter"
        else: return "none"
        
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    return settings