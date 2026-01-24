"""Text post-processing and cleanup."""

import re
from ..config.constants import FILLER_WORDS


def cleanup_text(text: str) -> str:
    """
    Clean up transcribed text by removing filler words and normalizing formatting.

    Performs the following cleanup operations:
    - Removes filler words (um, uh, like, etc.) defined in FILLER_WORDS
    - Normalizes whitespace (collapses multiple spaces, trims)
    - Fixes punctuation spacing (removes space before, ensures space after)
    - Capitalizes first letter and letters after sentence-ending punctuation
    - Removes duplicate punctuation and orphan punctuation at start

    Args:
        text: Raw transcribed text from speech recognition engine.
            May contain filler words, inconsistent spacing, or formatting issues.

    Returns:
        Cleaned text with proper capitalization, spacing, and punctuation.
        Returns empty string if input is empty or None-like.

    Example:
        >>> cleanup_text("um, hello  there ,  how are you")
        'Hello there, how are you'
    """
    if not text:
        return ""

    result = text

    # Remove filler words (case-insensitive, word boundaries)
    for filler in FILLER_WORDS:
        # Match filler word at word boundaries, optionally followed by comma
        pattern = rf"\b{re.escape(filler)}\b,?\s*"
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    # Clean up multiple spaces
    result = re.sub(r"\s+", " ", result)

    # Clean up spaces before punctuation
    result = re.sub(r"\s+([.,!?;:])", r"\1", result)

    # Ensure space after punctuation (except at end)
    result = re.sub(r"([.,!?;:])([A-Za-z])", r"\1 \2", result)

    # Remove leading/trailing spaces
    result = result.strip()

    # Capitalize first letter
    if result:
        result = result[0].upper() + result[1:]

    # Capitalize after sentence-ending punctuation
    result = re.sub(
        r"([.!?]\s+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        result,
    )

    # Clean up any double punctuation
    result = re.sub(r"([.,!?;:])\1+", r"\1", result)

    # Remove orphan punctuation at start
    result = re.sub(r"^[.,!?;:\s]+", "", result)

    return result


def add_punctuation(text: str) -> str:
    """
    Add ending punctuation to text if missing.

    A simple heuristic that adds a period at the end of text if no
    sentence-ending punctuation (., !, ?) is present. Whisper usually
    handles punctuation well, so this is primarily a safety fallback.

    Args:
        text: Text that may be missing ending punctuation.
            Whitespace is trimmed before checking.

    Returns:
        Text with guaranteed ending punctuation (period added if missing).
        Returns empty string if input is empty or None-like.

    Example:
        >>> add_punctuation("Hello world")
        'Hello world.'
        >>> add_punctuation("Hello world!")
        'Hello world!'
    """
    if not text:
        return ""

    result = text.strip()

    # Add period at end if no ending punctuation
    if result and result[-1] not in ".!?":
        result += "."

    return result
