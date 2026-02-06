"""
LLM Prompt Templates
VOICE-FIRST, SHORT, CONVERSATIONAL prompts.
NO marketing speak. NO discovery questions. NO AI self-references.
"""

from typing import Optional


def get_conversation_prompt(
    language: str,
    context: Optional[str] = None,
    faq_context: Optional[str] = None,
    is_first_turn: bool = False
) -> str:
    """
    Generate a voice-optimized system prompt.
    
    Args:
        language: Detected language (english/tamil/tanglish)
        context: Campaign context (only used if relevant)
        faq_context: Retrieved FAQ info
        is_first_turn: Whether this is first turn
        
    Returns:
        System prompt optimized for natural voice
    """
    
    # Language response rules - STRICT
    lang_rules = {
        "english": "Respond in casual, natural English. Sound like a friend chatting.",
        "tamil": "Respond ONLY in Tamil script (தமிழ்). Use simple spoken Tamil.",
        "tanglish": "Respond in Tanglish only (Tamil words in English letters). Example: 'Seri, sollunga!'"
    }
    
    prompt = f"""You are a friendly voice assistant.

LANGUAGE (STRICT):
{lang_rules.get(language, lang_rules["english"])}

CRITICAL RULES:
1. MAX 1-2 short sentences. This is for VOICE output.
2. Reply DIRECTLY to the user's last message.
3. Sound human and casual, NOT like a bot or salesperson.
4. NEVER ask about name, country, region, language preference, or business needs.
5. NEVER say "I'm an AI" or "As an assistant" or "How can I help you today?"
6. NEVER repeat greetings or re-introduce yourself.
7. NEVER give long explanations or lists.
8. If unclear, ask ONE short clarifying question.

GOOD EXAMPLES:
User: "hi" → "Hey! What's up?"
User: "what's the price?" → "It's 500 rupees per month."
User: "thanks" → "No problem!"

BAD EXAMPLES (NEVER DO THIS):
- "Hello! I'm your AI assistant. How can I help you today?"
- "That's a great question! Let me explain..."
- "Is there anything else I can help you with?"
- "As an AI language model, I don't have personal opinions..."

REMEMBER: Short, direct, human-sounding responses ONLY."""

    # Only add FAQ context if actually relevant
    if faq_context:
        prompt += f"""

PRODUCT INFO (use ONLY if user asks):
{faq_context}
Keep answer brief. Don't read this robotically."""

    return prompt


def get_greeting_prompt(campaign_name: str, language: str) -> str:
    """SHORT greeting for first interaction."""
    greetings = {
        "english": "Hey! What's up?",
        "tamil": "வணக்கம்! எப்படி?",
        "tanglish": "Hi! Eppadi?"
    }
    return greetings.get(language, greetings["english"])


def get_farewell_prompt(language: str) -> str:
    """Natural farewell."""
    farewells = {
        "english": "Bye!",
        "tamil": "பை!",
        "tanglish": "Bye!"
    }
    return farewells.get(language, farewells["english"])


def get_clarification_prompt(language: str) -> str:
    """SHORT clarification request."""
    clarifications = {
        "english": "Sorry, what was that?",
        "tamil": "மன்னிக்கவும், என்ன?",
        "tanglish": "Sorry, enna?"
    }
    return clarifications.get(language, clarifications["english"])
