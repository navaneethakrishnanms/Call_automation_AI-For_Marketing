"""
Test script to verify TTS bug fixes.
Run: python tests/test_tts_bugs.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.tts_normalizer import (
    clean_for_voice, normalize_for_speech, _clean_punctuation,
    _expand_abbreviations, _normalize_caps, _format_numbers,
    _remove_legal_suffixes
)

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    ok = actual == expected
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        print(f"        expected: {expected!r}")
        print(f"        got:      {actual!r}")

print("=" * 60)
print("BUG 1: Empty text after filler removal -> returns original")
print("=" * 60)
# A sentence made entirely of filler phrases
text1 = "Absolutely! I'm happy to help. Is there anything else?"
result1 = clean_for_voice(text1)
check("filler-only text returns original (non-empty)", bool(result1.strip()), True)

print()
print("=" * 60)
print("BUG 2: Underscores preserved in non-markdown text")
print("=" * 60)
check("markdown italic stripped", _clean_punctuation("_italic text_"), "italic text")
check("underscore in word kept", _clean_punctuation("my_variable_name"), "my_variable_name")

print()
print("=" * 60)
print("BUG 3: w/ abbreviation anchored properly")
print("=" * 60)
check("w/ expanded", _expand_abbreviations("Come w/ me"), "Come with me")
# Should not break inside compound text without space after /
check("kw/hr not broken", _expand_abbreviations("It uses 5 kw/hr"), "It uses 5 kw/hr")

print()
print("=" * 60)
print("BUG 4: 2-letter all-caps converted to Title Case")
print("=" * 60)
check("NO -> No", _normalize_caps("NO WAY"), "No Way")
check("OK preserved as Ok", _normalize_caps("OK FINE"), "Ok Fine")
check("AI preserved (acronym)", _normalize_caps("AI is great"), "AI is great")
check("IT preserved (acronym)", _normalize_caps("IT department"), "IT department")

print()
print("=" * 60)
print("BUG 5: Pipeline order -- legal suffixes before numbers")  
print("=" * 60)
text5 = "Call Acme Inc. at 9876543210"
result5 = normalize_for_speech(text5)
check("phone not truncated after legal suffix removal", "987" in result5, True)
check("Inc removed", "Inc" not in result5, True)

print()
print("=" * 60)
print("BUG 6: Phone regex — only exactly 10 digits")
print("=" * 60)
check("10-digit formatted", _format_numbers("Call 9876543210"), "Call 987, 654, 3210")
check("12-digit NOT formatted", _format_numbers("ID 123456789012"), "ID 123456789012")
check("9-digit NOT formatted", _format_numbers("Zip 123456789"), "Zip 123456789")

print()
print("=" * 60)
print("BUG 9: Long sentence splitter — no double spaces")
print("=" * 60)
# Test via the TTS service preprocessor
from app.services.tts_service import TTSService
svc = TTSService.__new__(TTSService)
long_text = "This is a very long sentence that has many words and should be split into two parts for natural speech"
processed = svc._preprocess_for_speech(long_text)
check("no double spaces", "  " not in processed, True)
check("comma attached to word", ", " in processed or "," in processed, True)

print()
print("=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("=" * 60)
sys.exit(1 if failed else 0)
