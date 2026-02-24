"""
LLM Service
============
Uses Ollama gpt-oss:120b-cloud as primary LLM for voice conversations.
Fallback chain: Ollama (gpt-oss:120b-cloud) → Ollama (llama3.1:8b)
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
    """LLM service with Groq primary, Ollama fallback."""
    
    GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(self):
        """Initialize the LLM service."""
        self.ollama_host = settings.ollama_host
        self.ollama_primary_model = settings.ollama_primary_model  # gpt-oss:120b-cloud
        self.ollama_fallback_model = settings.ollama_model           # llama3.1:8b
        self.groq_key = getattr(settings, 'groq_api_key', None)
        self._client: Optional[httpx.AsyncClient] = None
        
        if self.groq_key:
            logger.info(f"LLM Service: Groq ({self.GROQ_MODEL}) — PRIMARY")
        logger.info(f"LLM Service: Ollama ({self.ollama_primary_model}) — FALLBACK 1")
        logger.info(f"LLM Service: Ollama ({self.ollama_fallback_model}) — FALLBACK 2")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
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
        Tries: Groq (cloud, fast) → Ollama primary → Ollama fallback
        """
        # PRIMARY: Groq (cloud — fast and always available)
        if self.groq_key:
            result = await self._generate_groq(
                user_message, language, context, faq_context, conversation_history
            )
            if result:
                return result
            logger.warning("Groq failed, trying Ollama...")
        
        # FALLBACK 1: Ollama gpt-oss:120b-cloud
        result = await self._generate_ollama(
            user_message, language, context, faq_context, conversation_history,
            model=self.ollama_primary_model
        )
        if result:
            return result
        logger.warning("Ollama primary failed, trying fallback model...")
        
        # FALLBACK 2: Ollama llama3.1:8b
        result = await self._generate_ollama(
            user_message, language, context, faq_context, conversation_history,
            model=self.ollama_fallback_model
        )
        if result:
            return result
        logger.warning("All LLM backends failed")
        
        return self._get_fallback_response(language)
    
    async def _generate_openrouter(
        self,
        user_message: str,
        language: str,
        context: Optional[str] = None,
        faq_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """Generate response using OpenRouter (Qwen 2.5 VL 72B)."""
        try:
            client = await self._get_client()
            
            messages = self._build_messages(
                user_message, language, context, faq_context, conversation_history
            )
            
            payload = {
                "model": self.openrouter_model,
                "messages": messages,
                "temperature": 0.9,
                "top_p": 0.85,
                "max_tokens": 200,
                "frequency_penalty": 0.4,
                "presence_penalty": 0.3,
                "stop": ["\n\n", "Q:", "Note:", "Additionally"],
            }
            
            logger.info(f"Sending request to OpenRouter ({self.openrouter_model}) for language: {language}")
            response = await client.post(
                self.OPENROUTER_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Marketing AI Voice Bot"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                content = self._clean_for_voice(content)
                logger.info(f"OpenRouter LLM response: {content[:80]}...")
                return content
            else:
                logger.error(f"OpenRouter error: {response.status_code} - {response.text[:200]}")
                return None
                
        except httpx.TimeoutException:
            logger.error("OpenRouter timeout")
            return None
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return None
    
    async def _generate_groq(
        self,
        user_message: str,
        language: str,
        context: Optional[str] = None,
        faq_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """Generate response using Groq (Llama 3.3 70B)."""
        try:
            client = await self._get_client()
            
            messages = self._build_messages(
                user_message, language, context, faq_context, conversation_history
            )
            
            payload = {
                "model": self.GROQ_MODEL,
                "messages": messages,
                "temperature": 0.9,
                "top_p": 0.85,
                "max_tokens": 200,
                "stop": ["\n\n", "Q:", "Note:", "Additionally"],
            }
            
            logger.info(f"Sending request to Groq ({self.GROQ_MODEL}) for language: {language}")
            response = await client.post(
                self.GROQ_CHAT_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                content = self._clean_for_voice(content)
                logger.info(f"Groq LLM response: {content[:80]}...")
                return content
            else:
                logger.error(f"Groq LLM error: {response.status_code} - {response.text[:200]}")
                return None
                
        except httpx.TimeoutException:
            logger.error("Groq LLM timeout")
            return None
        except Exception as e:
            logger.error(f"Groq LLM error: {e}")
            return None
    
    async def _generate_ollama(
        self,
        user_message: str,
        language: str,
        context: Optional[str] = None,
        faq_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None
    ) -> Optional[str]:
        """Generate response using local Ollama."""
        model = model or self.ollama_primary_model
        try:
            client = await self._get_client()
            
            messages = self._build_messages(
                user_message, language, context, faq_context, conversation_history
            )
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.85,
                    "top_p": 0.9,
                    "num_predict": 256,
                    "repeat_penalty": 1.2,
                }
            }
            
            logger.info(f"Sending request to Ollama ({model}) for language: {language}")
            response = await client.post(
                f"{self.ollama_host}/api/chat",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "").strip()
                content = self._clean_for_voice(content)
                logger.info(f"Ollama ({model}) response: {content[:80]}...")
                # Reject empty, ellipsis-only, or too-short responses
                stripped = content.strip('.!? \t\n')
                if not stripped or len(stripped) < 5:
                    logger.warning(f"Ollama ({model}) returned unusable response: '{content}'")
                    return None
                return content
            else:
                logger.error(f"Ollama ({model}) error: {response.status_code} - {response.text}")
                return None
                
        except httpx.TimeoutException:
            logger.error(f"Ollama ({model}) timeout")
            return None
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama for {model}")
            return None
        except Exception as e:
            logger.error(f"Ollama ({model}) failed: {str(e)}")
            return None
    
    def _build_messages(
        self,
        user_message: str,
        language: str,
        context: Optional[str] = None,
        faq_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> list:
        """Build the messages array for the LLM."""
        is_first_turn = not conversation_history or len(conversation_history) == 0
        
        system_prompt = get_conversation_prompt(
            language=language,
            context=context,
            faq_context=faq_context,
            is_first_turn=is_first_turn
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for turn in conversation_history[-8:]:
                messages.append(turn)
        
        messages.append({"role": "user", "content": user_message})
        return messages
    
    def _clean_for_voice(self, text: str) -> str:
        """Clean LLM response for natural TN voice output.
        Handles both English and Tamil script properly.
        """
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # Remove bullet points and lists
        text = re.sub(r'^[\-\*\•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+[\.\\)]\s*', '', text, flags=re.MULTILINE)
        
        # Remove English AI-isms
        ai_patterns = [
            r"I'd be happy to help[^\.!]*[\.!]?\s*",
            r"Is there anything else[^\?]*\?\s*",
            r"Feel free to[^\.!]*[\.!]?\s*",
            r"Don't hesitate to[^\.!]*[\.!]?\s*",
            r"Let me know if[^\.!]*[\.!]?\s*",
            r"How (may|can) I (assist|help) you[^\?]*\?\s*",
            r"I'm here to help[^\.!]*[\.!]?\s*",
            r"Certainly[!,.]?\s*",
            r"Absolutely[!,.]?\s*",
            r"Of course[!,.]?\s*",
            r"Great question[!,.]?\s*",
            r"That's a (great|good) question[!,.]?\s*",
        ]
        
        # Remove Tamil AI-isms
        tamil_ai_patterns = [
            r"வரவேற்கிறோம்[^\.!]*[\.!]?\s*",
            r"உதவி செய்ய[^\.!]*[\.!]?\s*",
            r"வேறு ஏதாவது[^\?]*\?\s*",
            r"மேலும் ஏதாவது[^\?]*\?\s*",
            r"உங்களுக்கு உதவ[^\.!]*[\.!]?\s*",
        ]
        
        for pattern in ai_patterns + tamil_ai_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove emoji (TTS can't speak them)
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s+([,\.\?\!])', r'\1', text)
        
        # Smart sentence truncation (works for Tamil + English)
        # Split on sentence endings: . ! ? and Tamil purna viram ।
        sentences = re.split(r'(?<=[.!?।])\s+', text)
        if len(sentences) > 2:
            text = ' '.join(sentences[:2])
        
        # CRITICAL: If text was cut mid-word by max_tokens, trim to last complete word
        # Check if text ends without proper punctuation (sign of truncation)
        if text and text[-1] not in '.!?।,':
            # Find last punctuation or natural break
            last_good = max(
                text.rfind('.'), text.rfind('!'), text.rfind('?'),
                text.rfind(','), text.rfind('।')
            )
            if last_good > len(text) * 0.5:
                # Trim to last complete sentence/clause
                text = text[:last_good + 1]
            else:
                # No good break point found — just add period to end cleanly
                text = text.rstrip() + '.'
        
        return text
    
    def _get_fallback_response(self, language: str) -> str:
        """Get a short TN-natural fallback response when all LLMs fail."""
        fallbacks = {
            "english": "Sorry da, network issue. Say that again?",
            "tamil": "சாரி, network problem. மீண்டும் சொல்லுங்க?",
            "tanglish": "Sorry da, network issue. Munnadi sollunga?"
        }
        return fallbacks.get(language, fallbacks["english"])
    
    async def health_check(self) -> bool:
        """Check if LLM services are accessible."""
        if self.groq_key:
            try:
                client = await self._get_client()
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {self.groq_key}"}
                )
                if response.status_code == 200:
                    logger.info("Groq health check: OK")
                    return True
            except Exception as e:
                logger.error(f"Groq health check failed: {e}")
        
        # Check Ollama
        try:
            client = await self._get_client()
            response = await client.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                logger.info("Ollama health check: OK")
                return True
        except Exception:
            pass
        
        return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
llm_service = LLMService()
