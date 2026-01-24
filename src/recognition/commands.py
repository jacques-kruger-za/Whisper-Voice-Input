"""Voice command detection and classification."""

from difflib import SequenceMatcher

from src.config.constants import COMMAND_DEFINITIONS, COMMAND_THRESHOLD


class CommandResult:
    """Result from command classification."""

    def __init__(
        self,
        command_phrase: str,
        action: str,
        confidence: float,
        original_text: str,
    ):
        self.command_phrase = command_phrase
        self.action = action
        self.confidence = confidence
        self.original_text = original_text
        self.success = bool(command_phrase and action)

    def __repr__(self) -> str:
        return (
            f"CommandResult(phrase={self.command_phrase!r}, "
            f"action={self.action!r}, confidence={self.confidence:.0f})"
        )


def classify_transcription(
    text: str,
    threshold: int | None = None,
) -> tuple[str, CommandResult | None]:
    """
    Classify transcription as either a command or dictation.

    Uses fuzzy matching to detect voice commands from COMMAND_DEFINITIONS.
    Returns a tuple of (classification_type, result) where classification_type
    is either "command" or "dictation".

    Args:
        text: Transcribed text to classify
        threshold: Fuzzy matching score threshold (0-100), defaults to COMMAND_THRESHOLD

    Returns:
        Tuple of ("command", CommandResult) if command detected
        Tuple of ("dictation", None) if no command matched
    """
    if threshold is None:
        threshold = COMMAND_THRESHOLD

    # Normalize input text
    normalized_text = text.strip().lower()

    if not normalized_text:
        return ("dictation", None)

    # Check each defined command
    best_match = None
    best_score = 0.0

    for command_phrase, command_info in COMMAND_DEFINITIONS.items():
        # Calculate similarity score (0.0 to 1.0)
        similarity = SequenceMatcher(
            None,
            normalized_text,
            command_phrase.lower()
        ).ratio()

        # Convert to 0-100 scale
        score = similarity * 100

        if score > best_score:
            best_score = score
            best_match = (command_phrase, command_info)

    # Check if best match exceeds threshold
    if best_match and best_score >= threshold:
        command_phrase, command_info = best_match
        result = CommandResult(
            command_phrase=command_phrase,
            action=command_info["action"],
            confidence=best_score,
            original_text=text,
        )
        return ("command", result)

    return ("dictation", None)
