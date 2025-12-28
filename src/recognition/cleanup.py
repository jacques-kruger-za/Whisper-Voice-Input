"""Text post-processing and cleanup."""

import re
from ..config.constants import FILLER_WORDS


def cleanup_text(text: str) -> str:
    """
    Clean up transcribed text.

    - Remove filler words (um, uh, like, etc.)
    - Fix capitalization
    - Clean up punctuation
    - Normalize whitespace
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
    Add basic punctuation if missing.

    This is a simple heuristic - Whisper usually handles punctuation well.
    """
    if not text:
        return ""

    result = text.strip()

    # Add period at end if no ending punctuation
    if result and result[-1] not in ".!?":
        result += "."

    return result
