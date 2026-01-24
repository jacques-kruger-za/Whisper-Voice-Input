"""Spoken punctuation word-to-symbol conversion."""

import re
from ..config.constants import PUNCTUATION_WORDS


def process_spoken_punctuation(text: str) -> str:
    """
    Convert spoken punctuation words to their corresponding symbols.

    Replaces punctuation words (e.g., "period", "comma", "question mark")
    with their symbol equivalents (., , ?) while maintaining proper spacing.
    Multi-word punctuation terms (e.g., "question mark") are handled correctly.

    Performs the following operations:
    - Replaces spoken punctuation words with symbols (case-insensitive)
    - Removes spaces before punctuation symbols
    - Ensures space after punctuation symbols (except at end)
    - Normalizes whitespace (collapses multiple spaces, trims)

    Args:
        text: Text containing spoken punctuation words.
            May contain words like "period", "comma", "question mark", etc.

    Returns:
        Text with punctuation symbols replacing spoken words.
        Returns empty string if input is empty or None-like.

    Example:
        >>> process_spoken_punctuation("hello period how are you")
        'hello. how are you'
        >>> process_spoken_punctuation("what is your name question mark")
        'what is your name?'
        >>> process_spoken_punctuation("hello comma world exclamation mark")
        'hello, world!'
    """
    if not text:
        return ""

    result = text

    # Sort punctuation words by length (longest first) to handle multi-word
    # terms like "question mark" before single words like "mark"
    sorted_punctuation = sorted(
        PUNCTUATION_WORDS.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    # Replace each punctuation word with its symbol
    for word, symbol in sorted_punctuation:
        # Match punctuation word at word boundaries (case-insensitive)
        # Pattern matches the word with optional surrounding spaces
        pattern = rf"\b{re.escape(word)}\b"
        result = re.sub(pattern, symbol, result, flags=re.IGNORECASE)

    # Clean up spaces before punctuation
    result = re.sub(r"\s+([.,!?;:—])", r"\1", result)

    # Ensure space after punctuation (except at end)
    result = re.sub(r"([.,!?;:—])([A-Za-z])", r"\1 \2", result)

    # Clean up multiple spaces
    result = re.sub(r"\s+", " ", result)

    # Remove leading/trailing spaces
    result = result.strip()

    return result
