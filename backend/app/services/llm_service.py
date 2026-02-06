"""
LLM Service
Integrates with Mistral-7B-Instruct via Ollama for conversational responses.
"""

import logging
from typing import Optional, List, Dict, Any
import httpx

from app.config import settings
from app.utils.prompts import get_conversation_prompt

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service using Mistral-7B-Instruct via Ollama."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                base_url=self.host
            )
        return self._client
    
    async def generate_response(
        self,
        user_message: str,
        language: str,
        context: Optional[str] = None,
        faq_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """
        Generate a conversational response using Mistral.
        
        Args:
            user_message: User's input message
            language: Detected language (english/tamil/tanglish)
            context: Additional context (campaign info, etc.)
            faq_context: Retrieved FAQ information
            conversation_history: Previous conversation turns
            
        Returns:
            Generated response text or None if failed
        """
        try:
            client = await self._get_client()
            
            # Build the prompt
            system_prompt = get_conversation_prompt(
                language=language,
                context=context,
                faq_context=faq_context
            )
            
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for turn in conversation_history[-6:]:  # Keep last 6 turns
                    messages.append(turn)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Make request to Ollama
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 256,  # Keep responses concise
                }
            }
            
            response = await client.post("/api/chat", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "").strip()
                logger.info(f"LLM response generated: {len(content)} chars")
                return content
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return self._get_fallback_response(language)
                
        except httpx.TimeoutException:
            logger.error("Ollama API timeout")
            return self._get_fallback_response(language)
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama - ensure it's running")
            return self._get_fallback_response(language)
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return self._get_fallback_response(language)
    
    def _get_fallback_response(self, language: str) -> str:
        """Get a fallback response when LLM fails."""
        fallbacks = {
            "english": "I apologize, I'm having a small issue. Could you please repeat that?",
            "tamil": "மன்னிக்கவும், சிறிய சிக்கல் உள்ளது. தயவுசெய்து மீண்டும் சொல்லுங்கள்?",
            "tanglish": "Sorry, konjam issue irukku. Please munnadi sollunga?"
        }
        return fallbacks.get(language, fallbacks["english"])
    
    async def health_check(self) -> bool:
        """Check if Ollama is accessible and model is loaded."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check if our model is available
                return any(self.model.split(":")[0] in name for name in model_names)
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
llm_service = LLMService()
