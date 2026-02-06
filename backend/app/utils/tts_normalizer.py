"""
TTS Text Normalization Layer
============================
Converts formal text into natural spoken language for TTS engines.

This module solves the problem of TTS engines spelling out long,
uncommon proper nouns character-by-character instead of pronouncing
them naturally.

Heuristics Used:
1. Break long formal names with commas for natural pauses
2. Add contextual phrases ("a company", "an institute") for clarity
3. Remove legal suffixes that sound robotic (Pvt Ltd, LLC, etc.)
4. Normalize ALL-CAPS to title case
5. Add soft introductions for long proper nouns
6. Preserve common conversational phrases unchanged
"""

import re
from typing import Optional

# ============================================================================
# PATTERNS FOR DETECTION
# ============================================================================

# Legal/formal suffixes that sound robotic when spoken
LEGAL_SUFFIXES = [
    r'\b(Private|Pvt\.?)\s*(Limited|Ltd\.?)\b',
    r'\bLLC\b',
    r'\bLLP\b',
    r'\bInc\.?\b',
    r'\bCorp(oration)?\.?\b',
    r'\bCo\.?\b',
    r'\bPLC\b',
    r'\b(Registered|Regd\.?)\b',
]

# Institution keywords that help identify formal names
INSTITUTION_KEYWORDS = [
    'institute', 'university', 'college', 'school', 
    'academy', 'foundation', 'centre', 'center',
    'hospital', 'medical', 'polytechnic'
]

# Business keywords 
BUSINESS_KEYWORDS = [
    'solutions', 'services', 'systems', 'technologies',
    'enterprises', 'industries', 'manufacturing', 'automation',
    'consulting', 'analytics', 'ventures', 'labs'
]

# Common conversational words that should NOT be modified
COMMON_WORDS = {
    'marketing', 'ai', 'hello', 'welcome', 'thank', 'help',
    'today', 'call', 'about', 'regarding', 'from', 'with'
}


# ============================================================================
# CORE NORMALIZATION FUNCTION
# ============================================================================

def prepare_text_for_tts(
    text: str,
    add_context: bool = True,
    max_name_words: int = 6
) -> str:
    """
    Prepare text for TTS to sound natural and human-like.
    
    This function applies heuristics to make formal/proper nouns
    sound conversational instead of robotic.
    
    Args:
        text: Input text (can be any campaign name, greeting, etc.)
        add_context: Whether to add contextual phrases for long names
        max_name_words: Names longer than this get special treatment
    
    Returns:
        Normalized text optimized for natural TTS pronunciation
    
    Examples:
        >>> prepare_text_for_tts("Bannari Amman Institute of Technology")
        "Bannari Amman Institute of Technology, an educational institute"
        
        >>> prepare_text_for_tts("XYZ Advanced Manufacturing Solutions Private Limited")
        "XYZ Advanced Manufacturing Solutions, a technology company"
    """
    if not text or not text.strip():
        return text
    
    # Step 1: Normalize ALL-CAPS to Title Case (prevents spelling out)
    text = _normalize_caps(text)
    
    # Step 2: Remove legal suffixes that sound robotic
    text = _remove_legal_suffixes(text)
    
    # Step 3: Add breathing pauses for long proper nouns
    text = _add_natural_pauses(text, max_name_words)
    
    # Step 4: Add contextual phrases if the name is formal
    if add_context:
        text = _add_contextual_phrase(text)
    
    # Step 5: Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _normalize_caps(text: str) -> str:
    """
    Convert ALL-CAPS words to Title Case.
    
    TTS engines often spell out ALL-CAPS words letter by letter.
    Example: "ABC COMPANY" -> "Abc Company"
    
    Preserves common acronyms like AI, IT, HR, etc.
    """
    # Common acronyms to preserve
    preserve_acronyms = {'AI', 'IT', 'HR', 'CEO', 'CTO', 'USA', 'UK', 'EU', 'IIT', 'IIM', 'NIT'}
    
    words = text.split()
    result = []
    
    for word in words:
        # Strip punctuation for checking
        clean_word = re.sub(r'[^\w]', '', word)
        
        if clean_word.upper() in preserve_acronyms:
            # Keep known acronyms as-is
            result.append(word)
        elif clean_word.isupper() and len(clean_word) > 2:
            # Convert ALL-CAPS words (except short ones) to Title Case
            result.append(word.title())
        else:
            result.append(word)
    
    return ' '.join(result)


def _remove_legal_suffixes(text: str) -> str:
    """
    Remove legal/formal suffixes that sound robotic when spoken.
    
    Example: "ABC Solutions Private Limited" -> "ABC Solutions"
    """
    for pattern in LEGAL_SUFFIXES:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Clean up trailing commas or periods
    text = re.sub(r'[,\s]+$', '', text)
    
    return text


def _add_natural_pauses(text: str, max_words: int = 6) -> str:
    """
    Add commas to create natural breathing pauses in long names.
    
    Long proper nouns without pauses sound rushed and robotic.
    Adding a comma after the main name creates a natural breath.
    
    Example: "Bannari Amman Institute of Technology located in Tamil Nadu"
          -> "Bannari Amman Institute of Technology, located in Tamil Nadu"
    """
    words = text.split()
    
    # Only process if it's a long formal name without existing pauses
    if len(words) > max_words and ',' not in text:
        # Find a good break point (after "of", "for", "and", or institution keyword)
        break_after = ['of', 'for', 'and', 'in']
        
        for i, word in enumerate(words):
            lower_word = word.lower().rstrip('.,')
            
            # Check for institution/business keywords
            if lower_word in INSTITUTION_KEYWORDS or lower_word in BUSINESS_KEYWORDS:
                # Add comma after the keyword + next word if exists
                if i + 1 < len(words) and i + 1 >= 3:
                    words[i] = word.rstrip(',') + ','
                    break
            
            # Check for connecting words as break points
            if lower_word in break_after and i > 2:
                if i + 1 < len(words):
                    # Add comma after the next word
                    j = i + 1
                    words[j] = words[j].rstrip(',') + ','
                    break
    
    return ' '.join(words)


def _add_contextual_phrase(text: str) -> str:
    """
    Add contextual phrases to help TTS understand the type of entity.
    
    This helps the TTS pronounce names more naturally by providing
    context about what kind of entity it is.
    
    Example: "Bannari Amman Institute of Technology"
          -> "Bannari Amman Institute of Technology, an educational institute"
    """
    text_lower = text.lower()
    
    # Check if it's already conversational (has common words)
    common_word_count = sum(1 for word in COMMON_WORDS if word in text_lower)
    if common_word_count >= 2:
        # Already sounds conversational, don't modify
        return text
    
    # Check if context is already present
    has_context = any(phrase in text_lower for phrase in [
        'a company', 'an institute', 'a college', 'regarding',
        'about', 'called', 'known as'
    ])
    if has_context:
        return text
    
    # Detect entity type and add appropriate context
    if any(kw in text_lower for kw in ['institute', 'university', 'college', 'school', 'academy']):
        if not text.rstrip().endswith(','):
            text = text.rstrip() + ','
        text += ' an educational institute'
    
    elif any(kw in text_lower for kw in ['hospital', 'medical', 'clinic', 'healthcare']):
        if not text.rstrip().endswith(','):
            text = text.rstrip() + ','
        text += ' a healthcare organization'
    
    elif any(kw in text_lower for kw in BUSINESS_KEYWORDS):
        if not text.rstrip().endswith(','):
            text = text.rstrip() + ','
        text += ' a technology company'
    
    # For very long names without identifiable keywords, add a soft intro
    elif len(text.split()) > 5:
        # Could be a product or brand name
        if not text.rstrip().endswith(','):
            text = text.rstrip() + ','
        text += ' a leading organization'
    
    return text


# ============================================================================
# SENTENCE-LEVEL NORMALIZATION
# ============================================================================

def normalize_greeting(
    campaign_name: str,
    greeting_template: str = "Hello! I'm calling from {name}."
) -> str:
    """
    Generate a natural-sounding greeting for any campaign.
    
    Args:
        campaign_name: The name of the campaign/company
        greeting_template: Template with {name} placeholder
    
    Returns:
        Natural greeting ready for TTS
    
    Example:
        >>> normalize_greeting("Bannari Amman Institute of Technology")
        "Hello! I'm calling from Bannari Amman Institute of Technology, an educational institute."
    """
    normalized_name = prepare_text_for_tts(campaign_name)
    return greeting_template.format(name=normalized_name)


def normalize_for_speech(text: str) -> str:
    """
    Full text normalization for any speech content.
    
    This is the main function to use for all TTS content.
    It handles greetings, campaign names, and general text.
    
    Args:
        text: Any text that will be spoken via TTS
    
    Returns:
        Normalized text optimized for natural speech
    """
    # Handle numbers that might be spelled out
    text = _normalize_numbers(text)
    
    # Handle the main text
    text = prepare_text_for_tts(text)
    
    return text


def _normalize_numbers(text: str) -> str:
    """
    Ensure numbers are formatted for natural speech.
    
    Example: "Call us at 1800123456" -> "Call us at 1 8 0 0, 1 2 3 4 5 6"
    """
    # Phone numbers: add spaces for digit-by-digit reading
    def format_phone(match):
        number = match.group(1)
        # Group digits for natural reading
        if len(number) == 10:
            return f"{number[:3]}, {number[3:6]}, {number[6:]}"
        return ', '.join(number[i:i+3] for i in range(0, len(number), 3))
    
    # Match phone-like numbers (10+ digits)
    text = re.sub(r'\b(\d{10,})\b', format_phone, text)
    
    return text


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Test cases
    test_inputs = [
        "Bannari Amman Institute of Technology",
        "XYZ Advanced Manufacturing Solutions Private Limited",
        "ABC Super Premium Smart Home Automation System",
        "NATIONAL INSTITUTE OF TECHNOLOGY",
        "Hello! Welcome to Marketing AI",
        "IIT Madras Research Foundation",
        "Acme Corp Technologies LLC",
        "Dr. John's Advanced Healthcare Solutions Private Limited",
    ]
    
    print("=" * 60)
    print("TTS TEXT NORMALIZATION EXAMPLES")
    print("=" * 60)
    
    for text in test_inputs:
        normalized = prepare_text_for_tts(text)
        print(f"\nInput:  {text}")
        print(f"Output: {normalized}")
    
    print("\n" + "=" * 60)
    print("GREETING EXAMPLES")
    print("=" * 60)
    
    for name in test_inputs[:3]:
        greeting = normalize_greeting(name)
        print(f"\nCampaign: {name}")
        print(f"Greeting: {greeting}")
