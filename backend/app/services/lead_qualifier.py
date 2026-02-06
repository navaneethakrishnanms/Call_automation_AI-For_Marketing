"""
Lead Qualifier
Analyzes conversations to classify leads as hot, warm, or cold.
"""

import re
import logging
from typing import List, Dict, Literal

logger = logging.getLogger(__name__)

LeadLevel = Literal["hot", "warm", "cold"]


class LeadQualifier:
    """Qualifies leads based on conversation analysis."""
    
    # Positive signals indicating interest
    POSITIVE_SIGNALS = [
        # Purchase intent
        r'\b(buy|purchase|order|get|want to try|interested)\b',
        r'\b(how much|price|cost|discount|offer)\b',
        r'\b(sign up|register|subscribe|join)\b',
        
        # Engagement
        r'\b(tell me more|explain|details|information)\b',
        r'\b(sounds good|great|excellent|perfect|love it)\b',
        r'\b(yes|yeah|sure|okay|definitely)\b',
        
        # Urgency
        r'\b(today|now|soon|asap|immediately|urgent)\b',
        r'\b(when can|how soon|available)\b',
        
        # Decision making
        r'\b(decide|thinking|consider|option)\b',
        r'\b(compare|better|best)\b',
    ]
    
    # Negative signals indicating disinterest
    NEGATIVE_SIGNALS = [
        r'\b(not interested|no thanks|dont want|don\'t need)\b',
        r'\b(too expensive|cant afford|can\'t afford)\b',
        r'\b(already have|using another|competitor)\b',
        r'\b(stop calling|remove|unsubscribe)\b',
        r'\b(busy|bad time|call later|not now)\b',
        r'\b(hang up|goodbye|bye)\b',
    ]
    
    # Question depth signals (more questions = more interest)
    QUESTION_PATTERNS = [
        r'\?',
        r'\b(what|how|when|where|why|which|who)\b.*\?',
    ]
    
    def __init__(self):
        """Initialize the lead qualifier."""
        self._positive_regex = [
            re.compile(p, re.IGNORECASE) for p in self.POSITIVE_SIGNALS
        ]
        self._negative_regex = [
            re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_SIGNALS
        ]
        self._question_regex = [
            re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS
        ]
    
    def extract_signals(self, text: str) -> List[str]:
        """
        Extract interest signals from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected signal types
        """
        signals = []
        
        # Check positive signals
        for pattern in self._positive_regex:
            if pattern.search(text):
                signals.append(f"positive:{pattern.pattern}")
        
        # Check negative signals
        for pattern in self._negative_regex:
            if pattern.search(text):
                signals.append(f"negative:{pattern.pattern}")
        
        # Check questions
        question_count = sum(
            len(pattern.findall(text)) for pattern in self._question_regex
        )
        if question_count > 0:
            signals.append(f"questions:{question_count}")
        
        return signals
    
    def qualify_lead(
        self,
        transcript: List[str],
        signals: List[str]
    ) -> Dict[str, any]:
        """
        Qualify a lead based on conversation signals.
        
        Args:
            transcript: List of conversation turns
            signals: Extracted signals from the conversation
            
        Returns:
            Dict with qualification level and score
        """
        positive_count = sum(1 for s in signals if s.startswith("positive:"))
        negative_count = sum(1 for s in signals if s.startswith("negative:"))
        question_count = sum(
            int(s.split(":")[1]) for s in signals if s.startswith("questions:")
        )
        
        # Calculate base score
        score = 0.5  # Start neutral
        
        # Positive signals boost score
        score += positive_count * 0.1
        
        # Negative signals reduce score
        score -= negative_count * 0.15
        
        # Questions indicate engagement (positive)
        score += min(question_count * 0.05, 0.2)
        
        # Conversation length factor
        user_turns = len([t for t in transcript if t.startswith("User:")])
        if user_turns >= 5:
            score += 0.1  # Longer engagement is positive
        
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        # Determine qualification level
        if score >= 0.7:
            qualification = "hot"
        elif score >= 0.4:
            qualification = "warm"
        else:
            qualification = "cold"
        
        logger.info(
            f"Lead qualified: {qualification} (score: {score:.2f}, "
            f"+{positive_count}/-{negative_count}, {question_count} questions)"
        )
        
        return {
            "qualification": qualification,
            "score": round(score, 2),
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "question_count": question_count,
            "conversation_turns": user_turns
        }
    
    def get_qualification_summary(
        self,
        qualification: LeadLevel
    ) -> str:
        """Get a human-readable summary for a qualification level."""
        summaries = {
            "hot": "High-intent lead showing strong purchase signals",
            "warm": "Interested lead requiring nurturing",
            "cold": "Low-interest lead, may need re-engagement later"
        }
        return summaries.get(qualification, "Unknown")


# Singleton instance
lead_qualifier = LeadQualifier()
