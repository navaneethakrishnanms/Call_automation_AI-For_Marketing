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
    database_url: str = "sqlite+aiosqlite:///./marketing_ai.db"
    
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # Groq (for Whisper STT)
    groq_api_key: str = ""
    
    # ElevenLabs (English TTS)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default voice
    
    # Sarvam AI (Tamil TTS)
    sarvam_api_key: str = ""
    
    # Ollama (Local LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    
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
