"""
Lead Qualifier
Analyzes conversations to classify leads - ONLY when explicit intent is detected.
"""

import re
import logging
from typing import List, Dict, Literal, Optional

logger = logging.getLogger(__name__)

LeadLevel = Literal["hot", "warm", "cold", "none"]


class LeadQualifier:
    """
    Qualifies leads based on EXPLICIT business intent signals.
    Does NOT trigger on casual conversation.
    """
    
    # EXPLICIT business intent signals (must be clear interest)
    BUSINESS_INTENT_SIGNALS = [
        # Pricing/Cost (clear buying intent)
        r'\b(price|pricing|cost|how much|quote|rate|fee)s?\b',
        r'\b(discount|offer|deal|package)s?\b',
        
        # Demo/Trial (evaluation intent)
        r'\b(demo|trial|free trial|test|try it|see it)(\s|$)',
        r'\b(show me|walk me through|demonstrate)\b',
        
        # Features/Product (research intent)
        r'\b(feature|capability|what can|does it|can it)\b',
        r'\b(plan|tier|version|edition)s?\b',
        
        # Business help (marketing/growth intent)
        r'\b(marketing help|grow my|business growth|get more)\b',
        r'\b(lead generation|customer acquisition|sales help)\b',
        
        # Purchase signals
        r'\b(buy|purchase|subscribe|sign up|get started)\b',
        r'\b(interested in|want to know about|tell me about)\s+(your|the)\s+(product|service|solution)\b',
    ]
    
    # Negative signals (disinterest)
    NEGATIVE_SIGNALS = [
        r'\b(not interested|no thanks?|don\'?t want|don\'?t need)\b',
        r'\b(too expensive|can\'?t afford|out of budget)\b',
        r'\b(stop|remove|unsubscribe|don\'?t call)\b',
        r'\b(already have|using another|happy with)\b',
        r'\b(bye|goodbye|hang up|gotta go)\b',
    ]
    
    # CASUAL conversation (should NOT trigger lead scoring)
    CASUAL_PATTERNS = [
        r'^(hi|hello|hey|yo)(\s|$|!|\?)',
        r'\b(how are you|what\'?s up|how\'?s it going)\b',
        r'\b(good|fine|great|okay|alright)\s*(thanks?)?\b',
        r'\b(what\'?s your name|who are you)\b',
        r'\b(weather|time|day|today)\b',
        r'\b(thanks?|thank you|cool|nice)\b',
    ]
    
    def __init__(self):
        """Initialize the lead qualifier."""
        self._intent_regex = [
            re.compile(p, re.IGNORECASE) for p in self.BUSINESS_INTENT_SIGNALS
        ]
        self._negative_regex = [
            re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_SIGNALS
        ]
        self._casual_regex = [
            re.compile(p, re.IGNORECASE) for p in self.CASUAL_PATTERNS
        ]
    
    def is_casual_conversation(self, text: str) -> bool:
        """Check if the text is casual conversation (not business intent)."""
        text = text.strip().lower()
        
        # Short messages are usually casual
        if len(text.split()) <= 3:
            for pattern in self._casual_regex:
                if pattern.search(text):
                    return True
        
        return False
    
    def has_business_intent(self, text: str) -> bool:
        """Check if user shows explicit business intent."""
        for pattern in self._intent_regex:
            if pattern.search(text):
                return True
        return False
    
    def extract_signals(self, text: str) -> List[str]:
        """
        Extract interest signals from text.
        Only extracts signals if there's business intent.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected signal types (empty if casual conversation)
        """
        # Skip casual conversation
        if self.is_casual_conversation(text):
            return []
        
        signals = []
        
        # Check business intent signals
        for pattern in self._intent_regex:
            if pattern.search(text):
                signals.append(f"intent:{pattern.pattern[:30]}")
        
        # Check negative signals
        for pattern in self._negative_regex:
            if pattern.search(text):
                signals.append(f"negative:{pattern.pattern[:30]}")
        
        return signals
    
    def should_qualify(self, transcript: List[str]) -> bool:
        """
        Determine if lead qualification should run.
        Only qualifies if user has shown explicit business intent.
        
        Args:
            transcript: List of conversation turns
            
        Returns:
            True if qualification should run
        """
        # Need at least 2 user turns with business intent
        user_turns = [t for t in transcript if t.startswith("User:")]
        
        intent_count = 0
        for turn in user_turns:
            text = turn.replace("User:", "").strip()
            if self.has_business_intent(text):
                intent_count += 1
        
        # Only qualify if there's clear intent (at least 1 explicit signal)
        return intent_count >= 1
    
    def qualify_lead(
        self,
        transcript: List[str],
        signals: List[str]
    ) -> Dict[str, any]:
        """
        Qualify a lead based on conversation signals.
        Returns "none" if no business intent detected.
        
        Args:
            transcript: List of conversation turns
            signals: Extracted signals from the conversation
            
        Returns:
            Dict with qualification level and score
        """
        # Check if we should even qualify
        if not self.should_qualify(transcript):
            logger.debug("No business intent detected - skipping qualification")
            return {
                "qualification": "none",
                "score": 0.0,
                "reason": "No explicit business intent detected"
            }
        
        intent_count = sum(1 for s in signals if s.startswith("intent:"))
        negative_count = sum(1 for s in signals if s.startswith("negative:"))
        
        # Calculate score based on intent strength
        score = 0.3  # Start low
        
        # Each intent signal adds to score
        score += intent_count * 0.15
        
        # Negative signals reduce score
        score -= negative_count * 0.2
        
        # Conversation depth bonus (more engagement = more interest)
        user_turns = len([t for t in transcript if t.startswith("User:")])
        if user_turns >= 4:
            score += 0.1
        
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        # Determine qualification level
        if negative_count > intent_count:
            qualification = "cold"
        elif score >= 0.6:
            qualification = "hot"
        elif score >= 0.35:
            qualification = "warm"
        else:
            qualification = "cold"
        
        logger.info(
            f"Lead qualified: {qualification} (score: {score:.2f}, "
            f"intent: {intent_count}, negative: {negative_count})"
        )
        
        return {
            "qualification": qualification,
            "score": round(score, 2),
            "intent_signals": intent_count,
            "negative_signals": negative_count,
            "conversation_turns": user_turns
        }
    
    def get_qualification_summary(self, qualification: LeadLevel) -> str:
        """Get a human-readable summary for a qualification level."""
        summaries = {
            "hot": "Strong purchase intent - ready to convert",
            "warm": "Showing interest - needs nurturing",
            "cold": "Low interest - may re-engage later",
            "none": "No business intent detected"
        }
        return summaries.get(qualification, "Unknown")


# Singleton instance
lead_qualifier = LeadQualifier()
