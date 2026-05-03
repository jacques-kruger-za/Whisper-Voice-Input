"""Voice command classification with wake-word prefix.

Commands are unambiguously triggered by the wake word (default "command")
followed by the command phrase. Anything else is dictation. This eliminates
fuzzy-match false positives — the prefix is the gate, fuzzy matching only
forgives small mishearings of the command word itself ("undue" → "undo").
"""

import re

from rapidfuzz import fuzz

from src.config.constants import (
    COMMAND_DEFINITIONS, COMMAND_THRESHOLD, COMMAND_WAKE_WORD,
)
from ..config import get_logger, get_settings

logger = get_logger(__name__)

_WAKE_WORD_RE = re.compile(
    r"^\s*" + re.escape(COMMAND_WAKE_WORD) + r"\b[\s,.:;!?-]*",
    re.IGNORECASE,
)


def _active_commands() -> dict[str, dict]:
    """Built-in defaults merged with user customs (custom wins on conflict).

    Customs are stored as flat phrase -> keystroke; we wrap them into the
    same shape as COMMAND_DEFINITIONS so the classifier code is uniform.
    """
    try:
        custom = get_settings().custom_commands or {}
    except Exception:
        custom = {}
    merged = dict(COMMAND_DEFINITIONS)
    for phrase, keystroke in custom.items():
        merged[phrase] = {"keystroke": keystroke, "description": "custom"}
    return merged


class CommandResult:
    """Result from command classification."""

    def __init__(
        self,
        command_phrase: str,
        keystroke: str,
        confidence: float,
        original_text: str,
    ):
        self.command_phrase = command_phrase
        self.keystroke = keystroke
        self.confidence = confidence
        self.original_text = original_text
        self.success = bool(command_phrase and keystroke)

    def __repr__(self) -> str:
        return (
            f"CommandResult(phrase={self.command_phrase!r}, "
            f"keystroke={self.keystroke!r}, confidence={self.confidence:.0f})"
        )


def classify_transcription(
    text: str,
    threshold: int | None = None,
    require_wake_word: bool = True,
) -> tuple[str, CommandResult | None]:
    """Classify transcription as command or dictation.

    With ``require_wake_word=True`` (default, legacy mixed-mode path):
      Returns ("command", CommandResult) if text starts with the wake word
      and the suffix fuzzy-matches a defined command above threshold.

    With ``require_wake_word=False`` (command-hotkey capture path):
      The hotkey IS the wake — match the entire utterance directly. No
      prefix needed. Used when commands have their own dedicated hotkey,
      so the user can say just "save" instead of "command save".

    Returns ("dictation", None) when nothing matches.
    """
    if threshold is None:
        threshold = COMMAND_THRESHOLD

    if not text or not text.strip():
        return ("dictation", None)

    # Strip whisper's leading-space convention and trailing punctuation
    # (cleanup hasn't run yet, so utterances often end with "." from Whisper).
    raw = text.strip().rstrip(".!?,;:")

    if require_wake_word:
        match = _WAKE_WORD_RE.match(raw)
        if not match:
            logger.debug("No wake word in %r — dictation", text[:80])
            return ("dictation", None)
        suffix = raw[match.end():].strip().lower()
    else:
        suffix = raw.strip().lower()

    if not suffix:
        logger.debug("Empty command suffix — dictation")
        return ("dictation", None)

    # Fuzzy-match the suffix against known command phrases
    best_phrase = None
    best_info = None
    best_score = 0.0
    for phrase, info in _active_commands().items():
        score = fuzz.ratio(suffix, phrase.lower())
        if score > best_score:
            best_score = score
            best_phrase = phrase
            best_info = info

    if best_phrase and best_score >= threshold:
        logger.info(
            "Command detected: %r -> %r (confidence=%.0f)",
            best_phrase, best_info["keystroke"], best_score,
        )
        return ("command", CommandResult(
            command_phrase=best_phrase,
            keystroke=best_info["keystroke"],
            confidence=best_score,
            original_text=text,
        ))

    logger.info(
        "Wake word matched but no command (suffix=%r, best=%r score=%.0f) — discarding",
        suffix, best_phrase, best_score,
    )
    # Wake word present but no matching command — return as command with
    # empty keystroke so the app can show "unknown command" rather than
    # injecting the literal text "command save us all".
    return ("command", CommandResult(
        command_phrase=f"unknown ({suffix})",
        keystroke="",
        confidence=best_score,
        original_text=text,
    ))
