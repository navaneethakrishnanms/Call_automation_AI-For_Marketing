"""
LLM Service
Integrates with Llama 3.1 8B via Ollama for natural voice conversations.
Optimized for casual, human-like responses (NOT sales-focused).
"""

import logging
import re
from typing import Optional, List, Dict
import httpx

from app.config import settings
from app.utils.prompts import get_conversation_prompt
from app.utils.tts_normalizer import clean_for_voice

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service using Llama 3.1 8B via Ollama."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.host = settings.ollama_host
        self.model = settings.ollama_model  # llama3.1:8b
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
        Generate a natural conversational response.
        
        Args:
            user_message: User's input message
            language: Detected language (english/tamil/tanglish)
            context: Additional context (only used if user asks about products)
            faq_context: Retrieved FAQ (only used if user asks about products)
            conversation_history: Previous conversation turns
            
        Returns:
            Generated response text or None if failed
        """
        try:
            client = await self._get_client()
            
            # Determine if this is first turn
            is_first_turn = not conversation_history or len(conversation_history) == 0
            
            # Get the voice-optimized prompt
            system_prompt = get_conversation_prompt(
                language=language,
                context=context,
                faq_context=faq_context,
                is_first_turn=is_first_turn
            )
            
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (keep last 8 turns for continuity)
            if conversation_history:
                for turn in conversation_history[-8:]:
                    messages.append(turn)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Make request to Ollama
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.8,  # Slightly more creative for natural speech
                    "top_p": 0.9,
                    "num_predict": 100,  # SHORT responses for voice (1-2 sentences)
                }
            }
            
            logger.info(f"Sending request to Ollama ({self.model}) for language: {language}")
            response = await client.post("/api/chat", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "").strip()
                
                # Clean up response for voice output
                content = self._clean_for_voice(content)
                
                logger.info(f"LLM response: {content[:80]}...")
                return content
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return self._get_fallback_response(language)
                
        except httpx.TimeoutException:
            logger.error("Ollama API timeout")
            return self._get_fallback_response(language)
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama - ensure it's running with: ollama serve")
            return self._get_fallback_response(language)
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return self._get_fallback_response(language)
    
    def _clean_for_voice(self, text: str) -> str:
        """Clean LLM response for natural voice output."""
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # Remove bullet points and lists
        text = re.sub(r'^[\-\*\•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+[\.\)]\s*', '', text, flags=re.MULTILINE)
        
        # Remove filler phrases
        filler_patterns = [
            r"I'd be happy to help[^\.\!]*[\.\!]?\s*",
            r"Is there anything else[^\?]*\?\s*",
            r"Feel free to[^\.\!]*[\.\!]?\s*",
            r"Don't hesitate to[^\.\!]*[\.\!]?\s*",
            r"Let me know if[^\.\!]*[\.\!]?\s*",
            r"That's a great question[^\.\!]*[\.\!]?\s*",
            r"I hope this helps[^\.\!]*[\.\!]?\s*",
            r"Absolutely!\s*",
            r"Certainly!\s*",
            r"Of course!\s*(?=\w)",  # Keep "Of course!" at end but remove before other text
        ]
        
        for pattern in filler_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s+([,\.\?\!])', r'\1', text)
        
        # Ensure not too long (truncate to ~2 sentences for voice)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 3:
            text = ' '.join(sentences[:2])
        
        return text
    
    def _get_fallback_response(self, language: str) -> str:
        """Get a short fallback response when LLM fails."""
        fallbacks = {
            "english": "Sorry, I missed that. Can you say it again?",
            "tamil": "மன்னிக்கவும், புரியல. மீண்டும் சொல்லுங்களேன்?",
            "tanglish": "Sorry, puriyala. Munnadi sollungaa?"
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
                model_base = self.model.split(":")[0]
                is_available = any(model_base in name for name in model_names)
                if not is_available:
                    logger.warning(f"Model {self.model} not found. Run: ollama pull {self.model}")
                return is_available
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
