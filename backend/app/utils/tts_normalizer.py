"""
TTS Text Normalization Layer
Cleans text for natural-sounding voice output.
Removes filler phrases, excessive punctuation, and marketing CTAs.
"""

import re
from typing import Optional


# ============================================================================
# FILLER PHRASES TO REMOVE
# ============================================================================

FILLER_PHRASES = [
    # Corporate speak
    r'\bI\'m happy to help\b',
    r'\bI\'d be happy to\b',
    r'\bI would be glad to\b',
    r'\bIs there anything else I can help you with\??\b',
    r'\bIs there anything else\??\b',
    r'\bFeel free to\b',
    r'\bDon\'t hesitate to\b',
    r'\bPlease don\'t hesitate\b',
    r'\bI hope this helps\b',
    r'\bLet me know if you have any questions\b',
    r'\bLet me know if you need anything else\b',
    
    # AI/Bot self-references
    r'\bAs an AI\b',
    r'\bAs a language model\b',
    r'\bAs an assistant\b',
    r'\bI\'m just an AI\b',
    r'\bI don\'t have feelings\b',
    
    # Overly formal
    r'\bI understand your concern\b',
    r'\bI appreciate your patience\b',
    r'\bThank you for your question\b',
    r'\bThat\'s a great question\b',
    r'\bAbsolutely!\s*',
    r'\bCertainly!\s*',
    
    # Marketing CTAs (unless user asks)
    r'\bSchedule a demo\b',
    r'\bBook a call\b',
    r'\bSign up today\b',
    r'\bGet started now\b',
    r'\bContact us at\b',
    r'\bVisit our website\b',
]

# ============================================================================
# PUNCTUATION CLEANUP
# ============================================================================

def _clean_punctuation(text: str) -> str:
    """Remove excessive punctuation for natural speech."""
    # Multiple exclamation/question marks
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r'\?{2,}', '?', text)
    
    # Ellipsis cleanup (keep max one)
    text = re.sub(r'\.{4,}', '...', text)
    
    # Remove asterisks (markdown bold)
    text = re.sub(r'\*+', '', text)
    
    # Remove underscores (markdown italic)
    text = re.sub(r'_+', '', text)
    
    # Remove hashtags
    text = re.sub(r'#\w+', '', text)
    
    # Remove bullet points
    text = re.sub(r'^[\s]*[-•*]\s*', '', text, flags=re.MULTILINE)
    
    # Remove numbered lists
    text = re.sub(r'^[\s]*\d+[\.\)]\s*', '', text, flags=re.MULTILINE)
    
    return text


# ============================================================================
# ABBREVIATION EXPANSION
# ============================================================================

ABBREVIATIONS = {
    r'\bbtw\b': 'by the way',
    r'\bw/': 'with',
    r'\bw/o\b': 'without',
    r'\b&\b': 'and',
    r'\betc\.?': 'etcetera',
    r'\be\.g\.': 'for example',
    r'\bi\.e\.': 'that is',
    r'\basap\b': 'as soon as possible',
    r'\binfo\b': 'information',
}


def _expand_abbreviations(text: str) -> str:
    """Expand common abbreviations for natural speech."""
    for abbrev, expansion in ABBREVIATIONS.items():
        text = re.sub(abbrev, expansion, text, flags=re.IGNORECASE)
    return text


# ============================================================================
# LEGAL SUFFIXES (sound robotic)
# ============================================================================

LEGAL_SUFFIXES = [
    r'\b(Private|Pvt\.?)\s*(Limited|Ltd\.?)\b',
    r'\bLLC\b',
    r'\bLLP\b',
    r'\bInc\.?\b',
    r'\bCorp(oration)?\.?\b',
    r'\bPLC\b',
]


def _remove_legal_suffixes(text: str) -> str:
    """Remove legal suffixes that sound robotic."""
    for pattern in LEGAL_SUFFIXES:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'[,\s]+$', '', text)
    return text


# ============================================================================
# NUMBER FORMATTING
# ============================================================================

def _format_numbers(text: str) -> str:
    """Format numbers for natural spoken output."""
    # Phone numbers: add pauses
    def format_phone(match):
        number = match.group(1)
        if len(number) == 10:
            return f"{number[:3]}, {number[3:6]}, {number[6:]}"
        return number
    
    text = re.sub(r'\b(\d{10,})\b', format_phone, text)
    return text


# ============================================================================
# CAPS NORMALIZATION
# ============================================================================

PRESERVE_ACRONYMS = {'AI', 'IT', 'HR', 'CEO', 'CTO', 'USA', 'UK', 'EU', 'IIT', 'IIM', 'FAQ'}


def _normalize_caps(text: str) -> str:
    """Convert ALL-CAPS to Title Case (prevents TTS spelling out)."""
    words = text.split()
    result = []
    
    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word.upper() in PRESERVE_ACRONYMS:
            result.append(word)
        elif clean_word.isupper() and len(clean_word) > 2:
            result.append(word.title())
        else:
            result.append(word)
    
    return ' '.join(result)


# ============================================================================
# MAIN NORMALIZATION FUNCTIONS
# ============================================================================

def clean_for_voice(text: str) -> str:
    """
    Clean text for natural voice output.
    Removes filler phrases, excessive punctuation, and marketing speak.
    
    Args:
        text: Raw text from LLM
        
    Returns:
        Clean text optimized for TTS
    """
    if not text or not text.strip():
        return text
    
    # Step 1: Remove filler phrases
    for pattern in FILLER_PHRASES:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Step 2: Clean punctuation
    text = _clean_punctuation(text)
    
    # Step 3: Expand abbreviations
    text = _expand_abbreviations(text)
    
    # Step 4: Normalize caps
    text = _normalize_caps(text)
    
    # Step 5: Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+([,\.\?\!])', r'\1', text)
    
    # Step 6: Remove empty sentences
    text = re.sub(r'\.\s*\.', '.', text)
    
    return text


def normalize_for_speech(text: str) -> str:
    """
    Full text normalization for TTS.
    Main function to use before sending to TTS engine.
    
    Args:
        text: Any text to be spoken
        
    Returns:
        Normalized text for natural speech
    """
    text = clean_for_voice(text)
    text = _format_numbers(text)
    text = _remove_legal_suffixes(text)
    return text


def prepare_text_for_tts(
    text: str,
    add_context: bool = False,
    max_name_words: int = 6
) -> str:
    """
    Prepare text for TTS (legacy function for compatibility).
    
    Args:
        text: Input text
        add_context: Whether to add contextual phrases (disabled by default now)
        max_name_words: Unused (kept for compatibility)
    
    Returns:
        Normalized text for TTS
    """
    return normalize_for_speech(text)


def normalize_greeting(
    campaign_name: str,
    greeting_template: str = "Hello! I'm calling from {name}."
) -> str:
    """Generate a natural greeting."""
    normalized_name = normalize_for_speech(campaign_name)
    return greeting_template.format(name=normalized_name)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    test_inputs = [
        "Absolutely! I'd be happy to help you with that. Is there anything else I can help you with?",
        "That's a great question! Let me explain. The price is $99/month. Feel free to reach out if you have more questions!",
        "Sure! Here's what you need to know:\n- First point\n- Second point\n- Third point",
        "**Bold text** and *italic text* should be cleaned.",
        "Contact XYZ Solutions Private Limited for more info!!!",
    ]
    
    print("=" * 60)
    print("TTS VOICE CLEANUP EXAMPLES")
    print("=" * 60)
    
    for text in test_inputs:
        cleaned = normalize_for_speech(text)
        print(f"\nInput:  {text[:60]}...")
        print(f"Output: {cleaned}")
