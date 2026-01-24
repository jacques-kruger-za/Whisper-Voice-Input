"""Custom vocabulary management with JSON persistence."""

import json
from pathlib import Path
from typing import List
from platformdirs import user_data_dir

from ..config.constants import APP_NAME, APP_AUTHOR
from ..config import get_logger

logger = get_logger(__name__)


class VocabularyManager:
    """Manage custom vocabulary with JSON persistence and token limit validation."""

    def __init__(self):
        self._data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
        self._vocab_file = self._data_dir / "vocabulary.json"
        self._vocabulary: List[str] = []
        self._load()

    def _load(self) -> None:
        """Load vocabulary from file or create empty list."""
        self._vocabulary = []

        if self._vocab_file.exists():
            try:
                with open(self._vocab_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Validate entries are strings
                        self._vocabulary = [str(word).strip() for word in data if word]
                    logger.debug(f"Loaded {len(self._vocabulary)} vocabulary terms")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load vocabulary: {e}, using empty list")
                self._vocabulary = []

    def save(self) -> None:
        """Save current vocabulary to file."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._vocab_file, "w", encoding="utf-8") as f:
                json.dump(self._vocabulary, f, indent=2)
            logger.debug(f"Saved {len(self._vocabulary)} vocabulary terms")
        except IOError as e:
            logger.error(f"Failed to save vocabulary: {e}")

    def get_vocabulary(self) -> List[str]:
        """Get the current vocabulary list."""
        return self._vocabulary.copy()

    def add_word(self, word: str) -> bool:
        """
        Add a word to the vocabulary.

        Args:
            word: The word to add (will be stripped and validated)

        Returns:
            True if added, False if invalid or already exists
        """
        if not word:
            return False

        word = word.strip()

        # Validate word (no empty strings, no purely whitespace)
        if not word or len(word) > 100:  # Reasonable max length
            logger.warning(f"Invalid vocabulary word: '{word}'")
            return False

        # Check for duplicates (case-insensitive)
        if any(existing.lower() == word.lower() for existing in self._vocabulary):
            logger.debug(f"Word already in vocabulary: '{word}'")
            return False

        self._vocabulary.append(word)
        self.save()
        logger.info(f"Added vocabulary word: '{word}'")
        return True

    def remove_word(self, word: str) -> bool:
        """
        Remove a word from the vocabulary.

        Args:
            word: The word to remove

        Returns:
            True if removed, False if not found
        """
        try:
            self._vocabulary.remove(word)
            self.save()
            logger.info(f"Removed vocabulary word: '{word}'")
            return True
        except ValueError:
            logger.debug(f"Word not found in vocabulary: '{word}'")
            return False

    def clear(self) -> None:
        """Clear all vocabulary words."""
        self._vocabulary.clear()
        self.save()
        logger.info("Cleared all vocabulary words")

    def generate_initial_prompt(self) -> str:
        """
        Generate initial_prompt for faster-whisper with 224 token limit.

        The initial_prompt parameter in faster-whisper helps guide transcription
        by providing context/vocabulary. It has a hard limit of 224 tokens.

        Returns:
            Formatted prompt string (e.g., "Glossary: Term1, Term2, Term3...")
            or empty string if vocabulary is empty or would exceed limit.
        """
        if not self._vocabulary:
            return ""

        # Format: "Glossary: Term1, Term2, Term3..."
        prefix = "Glossary: "
        terms = ", ".join(self._vocabulary)
        prompt = prefix + terms

        # Enforce 224 character limit (conservative approximation of tokens)
        # In practice, 1 token ≈ 4 characters for English text
        # We use character count as a simple approximation
        if len(prompt) > 224:
            logger.warning(f"Vocabulary prompt exceeds 224 char limit ({len(prompt)} chars), truncating")

            # Truncate terms to fit within limit
            truncated_terms = []
            current_length = len(prefix)

            for term in self._vocabulary:
                # Add ", " separator for all but first term
                separator = ", " if truncated_terms else ""
                term_length = len(separator + term)

                if current_length + term_length <= 224:
                    truncated_terms.append(term)
                    current_length += term_length
                else:
                    break

            if truncated_terms:
                prompt = prefix + ", ".join(truncated_terms)
                logger.info(f"Truncated vocabulary to {len(truncated_terms)}/{len(self._vocabulary)} terms")
            else:
                # Even the first term is too long with prefix
                logger.warning("Cannot fit any vocabulary terms within 224 char limit")
                return ""

        logger.debug(f"Generated initial_prompt ({len(prompt)} chars): {prompt[:50]}...")
        return prompt


# Global vocabulary manager instance
_vocabulary_manager: VocabularyManager | None = None


def get_vocabulary_manager() -> VocabularyManager:
    """Get the global vocabulary manager instance."""
    global _vocabulary_manager
    if _vocabulary_manager is None:
        _vocabulary_manager = VocabularyManager()
    return _vocabulary_manager
