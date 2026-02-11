"""Input validation for idea submissions — catches gibberish and profanity."""

import re

# Profanity / slur blocklist (matched as whole words, case-insensitive)
_BLOCKED_WORDS = {
    "fuck", "shit", "ass", "bitch", "damn", "cunt", "dick", "cock",
    "pussy", "whore", "slut", "bastard", "nigger", "nigga", "faggot",
    "retard", "retarded",
}

# 5+ consecutive consonants — catches keyboard mash like "wfkpsdf", "bcdfgh"
_CONSONANT_MASH = re.compile(r"[bcdfghjklmnpqrstvwxyz]{5,}", re.IGNORECASE)

# Same character repeated 3+ times — catches "aaaaaaa", "lllll"
_REPEATED_CHARS = re.compile(r"(.)\1{2,}")

_VOWELS = set("aeiouAEIOU")


def check_profanity(text: str) -> str | None:
    """Return error message if text contains blocked words, else None."""
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    found = words & _BLOCKED_WORDS
    if found:
        return "please keep your input appropriate"
    return None


def check_gibberish(text: str) -> str | None:
    """Return error message if text looks like keyboard mash, else None."""
    words = text.strip().split()
    if not words:
        return "please describe your idea in at least a few words"

    gibberish_count = 0
    for word in words:
        # Skip short words (2-3 chars) — too many legit short words/acronyms
        if len(word) <= 3:
            continue
        # Check for consonant clusters
        if _CONSONANT_MASH.search(word):
            gibberish_count += 1
        # Check for repeated characters
        elif _REPEATED_CHARS.search(word):
            gibberish_count += 1
        # Check vowel ratio — real English words have ~35%+ vowels.
        # Catches separator tricks like "b_c_d_f_g" that dodge consonant regex.
        else:
            letters = [c for c in word if c.isalpha()]
            if len(letters) >= 5:
                vowel_ratio = sum(1 for c in letters if c in _VOWELS) / len(letters)
                if vowel_ratio < 0.15:
                    gibberish_count += 1

    # If more than half of substantial words look like gibberish, reject
    substantial_words = [w for w in words if len(w) > 3]
    if substantial_words and gibberish_count / len(substantial_words) > 0.3:
        return "your input doesn't look like a real idea — please try again"

    return None


def validate_idea_input(text: str) -> str | None:
    """Run all checks. Returns first error message found, or None if clean."""
    return check_profanity(text) or check_gibberish(text)
