"""
Language Detection Service
Detects whether input text is English, Tamil, or Tanglish (Tamil written in English).
"""

import re
from typing import Literal
from langdetect import detect, DetectorFactory

# Set seed for reproducibility
DetectorFactory.seed = 0

LanguageType = Literal["english", "tamil", "tanglish"]


class LanguageDetector:
    """Detects language from text input."""
    
    # Common Tanglish patterns (Tamil words written in English)
    TANGLISH_PATTERNS = [
        r'\b(naan|nee|avan|aval|avanga|enna|epdi|yaaruku)\b',
        r'\b(romba|konjam|seri|illa|irukku|vandhen|poren|vaanga)\b',
        r'\b(sollu|kelunga|paaru|paarungal|vareenga|pogalam)\b',
        r'\b(amma|appa|akka|anna|thambi|thangachi)\b',
        r'\b(enaku|unaku|avanuku|avaluku|evanukkum)\b',
        r'\b(pannunga|pannuren|pannitaan|sollunga)\b',
        r'\b(vendaam|venum|mudiyaathu|mudiyum)\b',
        r'\b(eppo|eppadi|enga|yaar|yen|ethu)\b',
        r'\b(nalla|periya|chinna|pudhu|pazhaiya)\b',
        r'\b(thaan|dhaan|pola|maari|kooda)\b',
    ]
    
    # Tamil script Unicode range
    TAMIL_SCRIPT_PATTERN = re.compile(r'[\u0B80-\u0BFF]')
    
    def __init__(self):
        """Initialize the language detector."""
        self._tanglish_regex = re.compile(
            '|'.join(self.TANGLISH_PATTERNS),
            re.IGNORECASE
        )
    
    def detect_language(self, text: str) -> LanguageType:
        """
        Detect the language of the input text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Language type: "english", "tamil", or "tanglish"
        """
        if not text or not text.strip():
            return "english"  # Default to English for empty input
        
        text = text.strip()
        
        # Check for Tamil script (Unicode)
        if self._contains_tamil_script(text):
            return "tamil"
        
        # Check for Tanglish patterns
        if self._is_tanglish(text):
            return "tanglish"
        
        # Use langdetect for other cases
        try:
            detected = detect(text)
            if detected == 'ta':
                return "tamil"
            return "english"
        except Exception:
            # Default to English if detection fails
            return "english"
    
    def _contains_tamil_script(self, text: str) -> bool:
        """Check if text contains Tamil script characters."""
        return bool(self.TAMIL_SCRIPT_PATTERN.search(text))
    
    def _is_tanglish(self, text: str) -> bool:
        """
        Check if text appears to be Tanglish.
        Uses pattern matching for common Tamil words in English script.
        """
        # Count Tanglish word matches
        matches = self._tanglish_regex.findall(text.lower())
        words = text.split()
        
        if not words:
            return False
        
        # If more than 20% of words match Tanglish patterns, consider it Tanglish
        tanglish_ratio = len(matches) / len(words)
        return tanglish_ratio >= 0.2
    
    def get_response_language_instruction(self, language: LanguageType) -> str:
        """
        Get instruction for LLM on how to respond in the detected language.
        
        Args:
            language: Detected language type
            
        Returns:
            Instruction string for the LLM prompt
        """
        instructions = {
            "english": "Respond in natural, conversational English. Use friendly, warm language.",
            "tamil": "Respond in Tamil script (தமிழ்). Use polite, conversational Tamil.",
            "tanglish": "Respond in Tanglish (Tamil written in English letters). Use casual, friendly language mixing Tamil and English naturally. For example: 'Seri, naan unga query-ku help pannuren.'"
        }
        return instructions.get(language, instructions["english"])


# Singleton instance
language_detector = LanguageDetector()
