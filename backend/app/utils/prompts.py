"""
LLM Prompt Templates
Provides well-crafted prompts for natural, friendly conversations.
"""

from typing import Optional


def get_conversation_prompt(
    language: str,
    context: Optional[str] = None,
    faq_context: Optional[str] = None
) -> str:
    """
    Generate a system prompt for the conversation LLM.
    
    Args:
        language: Detected language (english/tamil/tanglish)
        context: Campaign or product context
        faq_context: Retrieved FAQ information
        
    Returns:
        System prompt string
    """
    
    # Language-specific instructions
    language_instructions = {
        "english": """
You MUST respond in English. Use natural, conversational language.
- Be warm, friendly, and professional
- Use short sentences (max 2-3 per response)
- Avoid technical jargon
- Sound like a helpful friend, not a robot
""",
        "tamil": """
You MUST respond in Tamil script (தமிழ்). Use conversational Tamil.
- Be polite and respectful (use appropriate honorifics)
- Keep responses short and clear
- Use simple, everyday Tamil words
- சிறிய வாக்கியங்களைப் பயன்படுத்துங்கள்
""",
        "tanglish": """
You MUST respond in Tanglish (Tamil words written in English letters).
- Mix Tamil and English naturally, as people speak in Chennai
- Be casual and friendly
- Example: "Seri, naan help pannuren. Unga question enna?"
- Keep it conversational and warm
"""
    }
    
    base_prompt = f"""You are a friendly, helpful marketing assistant for a customer call.

{language_instructions.get(language, language_instructions["english"])}

CONVERSATION RULES:
1. Be concise - maximum 2-3 short sentences per response
2. Sound natural and conversational, NEVER robotic
3. Use small confirmations like "Sure!", "Got it!", "Of course!"
4. Show genuine interest in helping the customer
5. If you don't know something, politely say so and offer to help differently
6. End responses with a question when appropriate to keep conversation flowing
7. Add brief pauses for natural flow (phrases like "Let me see...", "Alright...")

FORBIDDEN PHRASES (never use these):
- "I am an AI"
- "As a language model"
- "I don't have feelings"
- "Is there anything else I can help you with?"
- Any robotic or formal corporate language

RESPONSE FORMAT:
- Start with an acknowledgment or small talk
- Provide the main information
- End with an engaging question or next step
"""
    
    # Add campaign context if provided
    if context:
        base_prompt += f"""

CAMPAIGN CONTEXT:
{context}
"""
    
    # Add FAQ context if available
    if faq_context:
        base_prompt += f"""

{faq_context}

Use this FAQ information to answer customer questions accurately. 
Paraphrase the answers naturally - don't read them robotically.
"""
    
    return base_prompt


def get_greeting_prompt(campaign_name: str, language: str) -> str:
    """Generate a greeting for starting a call."""
    greetings = {
        "english": f"Hi there! Thanks for taking my call. I'm reaching out from {campaign_name}. How are you doing today?",
        "tamil": f"வணக்கம்! {campaign_name} இலிருந்து அழைக்கிறேன். எப்படி இருக்கீங்க?",
        "tanglish": f"Hi! {campaign_name} la irundhu call pannuren. Eppadi irukkeenga?"
    }
    return greetings.get(language, greetings["english"])


def get_farewell_prompt(language: str) -> str:
    """Generate a farewell for ending a call."""
    farewells = {
        "english": "It was lovely talking with you! Take care and have a wonderful day!",
        "tamil": "உங்களுடன் பேசுவது மிகவும் நன்றாக இருந்தது! நல்ல நாள் வாழ்த்துக்கள்!",
        "tanglish": "Nalla irundhuchu unga kooda pesuna! Have a great day!"
    }
    return farewells.get(language, farewells["english"])


def get_clarification_prompt(language: str) -> str:
    """Generate a clarification request."""
    clarifications = {
        "english": "I want to make sure I understand you correctly. Could you tell me a bit more about that?",
        "tamil": "சரியாக புரிந்து கொள்ள விரும்புகிறேன். கொஞ்சம் விளக்கமாக சொல்ல முடியுமா?",
        "tanglish": "Correct-a purinjukka virumbureen. Konjam detail-a solla mudiyuma?"
    }
    return clarifications.get(language, clarifications["english"])
