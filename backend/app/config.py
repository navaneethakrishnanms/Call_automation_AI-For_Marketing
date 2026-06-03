"""
Application Configuration
Manages all environment variables and settings using Pydantic Settings.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/marketing_ai.db"
    
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # Groq (Whisper STT — secondary/fallback)
    groq_api_key: str = ""
    
    # Sarvam AI (STT primary + TTS)
    sarvam_api_key: str = ""
    
    # OpenRouter (no longer used for LLM)
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen2.5-vl-72b-instruct"
    
    # Ollama (Primary + Fallback LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_primary_model: str = "gpt-oss:120b-cloud"
    ollama_model: str = "llama3.1:8b"
    
    # Retell AI
    retell_api_key: str = ""
    retell_agent_id: str = ""
    retell_phone_number: str = ""
    
    # Application
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    secret_key: str = "change-this-in-production"
    
    # FAQ Settings
    faq_similarity_threshold: float = 0.7
    faq_top_k: int = 3
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
