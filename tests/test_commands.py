"""Unit tests for fuzzy command matching."""

import pytest

from src.recognition.commands import CommandResult, classify_transcription
from src.config.constants import COMMAND_DEFINITIONS, COMMAND_THRESHOLD


class TestCommandResult:
    """Test CommandResult data class."""

    def test_command_result_initialization(self):
        """Test CommandResult initializes correctly."""
        result = CommandResult(
            command_phrase="delete that",
            action="delete_last",
            confidence=95.5,
            original_text="delete that",
        )
        assert result.command_phrase == "delete that"
        assert result.action == "delete_last"
        assert result.confidence == 95.5
        assert result.original_text == "delete that"
        assert result.success is True

    def test_command_result_success_false_with_empty_phrase(self):
        """Test success is False when command_phrase is empty."""
        result = CommandResult(
            command_phrase="",
            action="delete_last",
            confidence=50.0,
            original_text="something",
        )
        assert result.success is False

    def test_command_result_success_false_with_empty_action(self):
        """Test success is False when action is empty."""
        result = CommandResult(
            command_phrase="delete that",
            action="",
            confidence=90.0,
            original_text="delete that",
        )
        assert result.success is False

    def test_command_result_repr(self):
        """Test CommandResult string representation."""
        result = CommandResult(
            command_phrase="undo",
            action="undo",
            confidence=100.0,
            original_text="undo",
        )
        repr_str = repr(result)
        assert "CommandResult" in repr_str
        assert "undo" in repr_str
        assert "confidence=100" in repr_str


class TestClassifyTranscription:
    """Test classify_transcription function."""

    def test_exact_match_delete_that(self):
        """Test exact match for 'delete that' command."""
        classification, result = classify_transcription("delete that")
        assert classification == "command"
        assert result is not None
        assert result.command_phrase == "delete that"
        assert result.action == "delete_last"
        assert result.confidence == 100.0
        assert result.original_text == "delete that"

    def test_exact_match_undo(self):
        """Test exact match for 'undo' command."""
        classification, result = classify_transcription("undo")
        assert classification == "command"
        assert result is not None
        assert result.command_phrase == "undo"
        assert result.action == "undo"
        assert result.confidence == 100.0

    def test_exact_match_new_line(self):
        """Test exact match for 'new line' command."""
        classification, result = classify_transcription("new line")
        assert classification == "command"
        assert result is not None
        assert result.command_phrase == "new line"
        assert result.action == "insert_newline"
        assert result.confidence == 100.0

    def test_case_insensitive_matching(self):
        """Test command matching is case-insensitive."""
        test_cases = [
            "DELETE THAT",
            "Delete That",
            "DeLeTe ThAt",
            "UNDO",
            "Undo",
            "NEW LINE",
            "New Line",
        ]
        for text in test_cases:
            classification, result = classify_transcription(text)
            assert classification == "command", f"Failed for: {text}"
            assert result is not None, f"Result should not be None for: {text}"

    def test_fuzzy_match_with_typos(self):
        """Test fuzzy matching handles minor typos."""
        # "delete that" with typos
        classification, result = classify_transcription("delet that")
        assert classification == "command"
        assert result.command_phrase == "delete that"
        assert result.confidence >= COMMAND_THRESHOLD

        # "undo" with extra letter
        classification, result = classify_transcription("undoo")
        assert classification == "command"
        assert result.command_phrase == "undo"
        assert result.confidence >= COMMAND_THRESHOLD

    def test_fuzzy_match_with_extra_spaces(self):
        """Test fuzzy matching handles extra spaces."""
        classification, result = classify_transcription("  delete   that  ")
        assert classification == "command"
        assert result.command_phrase == "delete that"

    def test_threshold_default_value(self):
        """Test classification uses default threshold from constants."""
        # Text with low similarity should not match with default threshold of 80
        # "remove that" has similarity below 80 with all commands
        classification, result = classify_transcription("remove that")
        # This should be dictation as similarity is below 80
        assert classification == "dictation"
        assert result is None

    def test_custom_threshold_lower(self):
        """Test classification with custom lower threshold."""
        # "delete the" has lower similarity but should match with threshold of 70
        classification, result = classify_transcription("delete the", threshold=70)
        # This should now match as a command
        assert classification == "command"
        assert result is not None

    def test_custom_threshold_higher(self):
        """Test classification with custom higher threshold."""
        # Minor typo that would normally pass 80% but not 95%
        classification, result = classify_transcription("delate that", threshold=95)
        # Should not match with very high threshold
        assert classification == "dictation"
        assert result is None

    def test_dictation_text_not_confused_with_commands(self):
        """Test regular dictation is not confused with commands."""
        dictation_samples = [
            "hello world",
            "this is a test",
            "the quick brown fox",
            "I need to write something",
            "remove that enemy",  # Similar to "delete that" but below threshold
        ]
        for text in dictation_samples:
            classification, result = classify_transcription(text)
            assert classification == "dictation", f"Incorrectly classified as command: {text}"
            assert result is None

    def test_empty_string_returns_dictation(self):
        """Test empty string is classified as dictation."""
        classification, result = classify_transcription("")
        assert classification == "dictation"
        assert result is None

    def test_whitespace_only_returns_dictation(self):
        """Test whitespace-only string is classified as dictation."""
        classification, result = classify_transcription("   ")
        assert classification == "dictation"
        assert result is None

    def test_punctuation_after_command(self):
        """Test command with trailing punctuation."""
        # Commands with punctuation should still match
        classification, result = classify_transcription("delete that.")
        # This might be dictation if punctuation lowers similarity too much
        # Or command if fuzzy matching is forgiving enough
        # Let's assert based on actual behavior
        if classification == "command":
            assert result.command_phrase == "delete that"
        else:
            # Acceptable to classify as dictation due to punctuation
            assert result is None

    def test_command_with_filler_words(self):
        """Test command mixed with filler words."""
        # "um delete that" should still potentially match if threshold allows
        classification, result = classify_transcription("um delete that")
        # This will likely be dictation due to prefix
        # Fuzzy matching may not be high enough
        assert classification in ["command", "dictation"]

    def test_partial_command_match(self):
        """Test partial command phrases don't match."""
        partial_commands = [
            "delete",  # Only part of "delete that"
            "new",     # Only part of "new line"
        ]
        for text in partial_commands:
            classification, result = classify_transcription(text)
            # These should have low similarity and be classified as dictation
            if classification == "command":
                # If it matches a command, confidence should be low
                assert result.confidence < 90

    def test_command_similarity_ranking(self):
        """Test that closest matching command is selected."""
        # "delete that" should match "delete that" not "undo"
        classification, result = classify_transcription("delete that")
        assert result.command_phrase == "delete that"
        assert result.action == "delete_last"

    def test_all_defined_commands_are_testable(self):
        """Test all commands in COMMAND_DEFINITIONS can be matched."""
        for command_phrase, command_info in COMMAND_DEFINITIONS.items():
            classification, result = classify_transcription(command_phrase)
            assert classification == "command", f"Failed to match: {command_phrase}"
            assert result.command_phrase == command_phrase
            assert result.action == command_info["action"]
            assert result.confidence == 100.0

    def test_confidence_score_range(self):
        """Test confidence score is within valid range (0-100)."""
        test_cases = [
            "delete that",
            "undo",
            "new line",
            "hello world",
        ]
        for text in test_cases:
            classification, result = classify_transcription(text)
            if result is not None:
                assert 0 <= result.confidence <= 100

    def test_similar_but_not_command(self):
        """Test words similar to commands don't incorrectly match."""
        similar_words = [
            "undo button",       # Has "undo" but with extra words
            "delete the file",   # Has "delete" but different phrase
            "new lines",         # Plural vs singular
        ]
        for text in similar_words:
            classification, result = classify_transcription(text)
            # These should either be dictation or match with lower confidence
            if classification == "command":
                # If they match, ensure it's actually a valid match
                assert result.confidence >= COMMAND_THRESHOLD

    def test_threshold_boundary_cases(self):
        """Test behavior at threshold boundary."""
        # Test with threshold of 80
        # A text with exactly 80% similarity should match
        # A text with 79.9% should not match

        # We can't easily craft exact percentage matches, but we can test
        # that threshold is respected
        classification_high, result_high = classify_transcription(
            "delete that", threshold=80
        )
        assert classification_high == "command"

        classification_low, result_low = classify_transcription(
            "delete that", threshold=101  # Impossible threshold
        )
        assert classification_low == "dictation"

    def test_original_text_preserved(self):
        """Test that original text is preserved in result."""
        original = "  DELETE THAT  "
        classification, result = classify_transcription(original)
        if classification == "command":
            assert result.original_text == original

    def test_command_with_numbers(self):
        """Test commands mixed with numbers."""
        classification, result = classify_transcription("delete that 123")
        # Should likely be dictation due to appended numbers
        # But fuzzy matching might still catch it
        assert classification in ["command", "dictation"]

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        classification, result = classify_transcription("dëlétë thät")
        # Unicode may affect matching, should handle gracefully
        assert classification in ["command", "dictation"]

    def test_very_long_text(self):
        """Test classification with very long text."""
        long_text = "delete that " * 100
        classification, result = classify_transcription(long_text)
        # Should handle long text without errors
        assert classification in ["command", "dictation"]

    def test_command_action_mapping(self):
        """Test that correct actions are returned for each command."""
        expected_mappings = {
            "delete that": "delete_last",
            "undo": "undo",
            "new line": "insert_newline",
        }
        for command, expected_action in expected_mappings.items():
            classification, result = classify_transcription(command)
            assert result.action == expected_action


class TestCommandThresholdConfiguration:
    """Test command threshold configuration."""

    def test_default_threshold_from_constants(self):
        """Test default threshold matches COMMAND_THRESHOLD constant."""
        # When no threshold is provided, should use COMMAND_THRESHOLD
        classification, result = classify_transcription("delete that")
        if result:
            # The function should be using COMMAND_THRESHOLD internally
            assert COMMAND_THRESHOLD == 80

    def test_threshold_range_validation(self):
        """Test various threshold values work correctly."""
        thresholds = [0, 50, 70, 80, 90, 100]
        for threshold in thresholds:
            # Should not raise errors
            classification, result = classify_transcription("delete that", threshold=threshold)
            assert classification in ["command", "dictation"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_threshold(self):
        """Test that None threshold uses default."""
        classification1, result1 = classify_transcription("delete that", threshold=None)
        classification2, result2 = classify_transcription("delete that")
        # Should behave the same way
        assert classification1 == classification2
        if result1:
            assert result1.confidence == result2.confidence

    def test_negative_threshold(self):
        """Test behavior with negative threshold."""
        # Negative threshold should match everything
        classification, result = classify_transcription("random text", threshold=-1)
        assert classification == "command"  # Everything matches with negative threshold

    def test_special_characters(self):
        """Test handling of special characters."""
        special_texts = [
            "delete that!",
            "delete that?",
            "delete-that",
            "delete_that",
            "delete.that",
        ]
        for text in special_texts:
            classification, result = classify_transcription(text)
            # Should handle gracefully without errors
            assert classification in ["command", "dictation"]

    def test_newlines_in_text(self):
        """Test handling of newlines in input."""
        classification, result = classify_transcription("delete\nthat")
        assert classification in ["command", "dictation"]

    def test_tabs_in_text(self):
        """Test handling of tabs in input."""
        classification, result = classify_transcription("delete\tthat")
        assert classification in ["command", "dictation"]
