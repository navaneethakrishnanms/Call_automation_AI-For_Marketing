"""
Language Detector Utility
Detects the primary language used in a call transcript.
Supports: Tamil, Tanglish (romanized Tamil), Hindi, English.
"""

import re

# Tamil Unicode range: U+0B80 - U+0BFF
TAMIL_PATTERN = re.compile(r'[\u0B80-\u0BFF]')

# Hindi/Devanagari Unicode range: U+0900 - U+097F
HINDI_PATTERN = re.compile(r'[\u0900-\u097F]')

# Telugu Unicode range: U+0C00 - U+0C7F
TELUGU_PATTERN = re.compile(r'[\u0C00-\u0C7F]')

# Kannada Unicode range: U+0C80 - U+0CFF
KANNADA_PATTERN = re.compile(r'[\u0C80-\u0CFF]')

# Malayalam Unicode range: U+0D00 - U+0D7F
MALAYALAM_PATTERN = re.compile(r'[\u0D00-\u0D7F]')

# Common Tanglish (romanized Tamil) words/patterns
TANGLISH_WORDS = {
    'vanakkam', 'nandri', 'pesaren', 'pesalama', 'konjam', 'pathi',
    'padikira', 'irukku', 'irukka', 'pannunga', 'sollunga', 'vaanga',
    'enna', 'inga', 'anga', 'enga', 'ungalukku', 'enakku', 'neenga',
    'romba', 'nalla', 'sari', 'sollanum', 'kekanum', 'pannirukkom',
    'lendhu', 'mudichinga', 'padichinga', 'varum', 'aayirukku',
    'pannanum', 'pesanum', 'theriyum', 'theriyala', 'venum', 'vendam',
    'illa', 'illai', 'aama', 'podhu', 'innum', 'eppo', 'appo',
    'appuram', 'mudiyum', 'mudiyala', 'pannalam', 'panalama',
    'placementsum', 'coursesum', 'feessum',
}


def detect_language(transcript: str) -> str:
    """
    Detect the primary language of a call transcript.
    
    Returns one of: 'Tamil', 'Tanglish', 'Hindi', 'Telugu', 
                     'Kannada', 'Malayalam', 'English'
    """
    if not transcript:
        return 'English'
    
    # Count script-specific characters
    tamil_chars = len(TAMIL_PATTERN.findall(transcript))
    hindi_chars = len(HINDI_PATTERN.findall(transcript))
    telugu_chars = len(TELUGU_PATTERN.findall(transcript))
    kannada_chars = len(KANNADA_PATTERN.findall(transcript))
    malayalam_chars = len(MALAYALAM_PATTERN.findall(transcript))
    
    total_chars = len(transcript.replace(' ', '').replace('\n', ''))
    if total_chars == 0:
        return 'English'
    
    # If significant Tamil script characters are present
    if tamil_chars > 10 or (tamil_chars / max(total_chars, 1)) > 0.05:
        return 'Tamil'
    
    # If significant Hindi script characters
    if hindi_chars > 10 or (hindi_chars / max(total_chars, 1)) > 0.05:
        return 'Hindi'
    
    # If significant Telugu script characters
    if telugu_chars > 10 or (telugu_chars / max(total_chars, 1)) > 0.05:
        return 'Telugu'
    
    # If significant Kannada script characters
    if kannada_chars > 10 or (kannada_chars / max(total_chars, 1)) > 0.05:
        return 'Kannada'
    
    # If significant Malayalam script characters
    if malayalam_chars > 10 or (malayalam_chars / max(total_chars, 1)) > 0.05:
        return 'Malayalam'
    
    # Check for Tanglish (romanized Tamil) - look for common Tamil words in Latin script
    words_in_transcript = set(
        re.findall(r'[a-zA-Z]+', transcript.lower())
    )
    tanglish_matches = words_in_transcript & TANGLISH_WORDS
    
    if len(tanglish_matches) >= 3:
        return 'Tanglish'
    
    return 'English'
