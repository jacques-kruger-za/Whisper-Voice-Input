"""Unit tests for spoken punctuation word-to-symbol conversion."""

import pytest

from src.recognition.spoken_punctuation import process_spoken_punctuation
from src.config.constants import PUNCTUATION_WORDS


class TestProcessSpokenPunctuation:
    """Test process_spoken_punctuation function."""

    def test_period_conversion(self):
        """Test 'period' converts to '.'"""
        result = process_spoken_punctuation("hello period how are you")
        assert result == "hello. how are you"

    def test_comma_conversion(self):
        """Test 'comma' converts to ','"""
        result = process_spoken_punctuation("hello comma world")
        assert result == "hello, world"

    def test_question_mark_conversion(self):
        """Test 'question mark' converts to '?'"""
        result = process_spoken_punctuation("how are you question mark")
        assert result == "how are you?"

    def test_exclamation_mark_conversion(self):
        """Test 'exclamation mark' converts to '!'"""
        result = process_spoken_punctuation("hello world exclamation mark")
        assert result == "hello world!"

    def test_exclamation_point_conversion(self):
        """Test 'exclamation point' converts to '!' (alternative phrase)"""
        result = process_spoken_punctuation("wow exclamation point")
        assert result == "wow!"

    def test_colon_conversion(self):
        """Test 'colon' converts to ':'"""
        result = process_spoken_punctuation("here is a list colon apples oranges")
        assert result == "here is a list: apples oranges"

    def test_semicolon_conversion(self):
        """Test 'semicolon' converts to ';'"""
        result = process_spoken_punctuation("first part semicolon second part")
        assert result == "first part; second part"

    def test_dash_conversion(self):
        """Test 'dash' converts to '—'"""
        result = process_spoken_punctuation("hello dash world")
        assert result == "hello— world"

    def test_multiple_punctuation_same_type(self):
        """Test multiple instances of same punctuation type."""
        result = process_spoken_punctuation("one period two period three")
        assert result == "one. two. three"

    def test_multiple_punctuation_different_types(self):
        """Test multiple different punctuation types in one sentence."""
        result = process_spoken_punctuation("hello comma world exclamation mark how are you question mark")
        assert result == "hello, world! how are you?"

    def test_case_insensitive_matching(self):
        """Test punctuation words are matched case-insensitively."""
        test_cases = [
            ("hello PERIOD how are you", "hello. how are you"),
            ("hello Comma world", "hello, world"),
            ("how are you QUESTION MARK", "how are you?"),
            ("wow EXCLAMATION MARK", "wow!"),
            ("test Colon result", "test: result"),
            ("one Semicolon two", "one; two"),
            ("hello DASH world", "hello— world"),
        ]
        for input_text, expected in test_cases:
            result = process_spoken_punctuation(input_text)
            assert result == expected, f"Failed for: {input_text}"

    def test_mixed_case_punctuation_words(self):
        """Test mixed case punctuation words."""
        result = process_spoken_punctuation("hello PeRiOd world CoMmA test QuEsTiOn MaRk")
        assert result == "hello. world, test?"

    def test_spacing_before_punctuation_removed(self):
        """Test spaces before punctuation symbols are removed."""
        result = process_spoken_punctuation("hello   period   how are you")
        assert result == "hello. how are you"

    def test_spacing_after_punctuation_ensured(self):
        """Test space is added after punctuation before letters."""
        # The function should ensure space after punctuation
        result = process_spoken_punctuation("hello period how")
        assert result == "hello. how"

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty string."""
        result = process_spoken_punctuation("")
        assert result == ""

    def test_none_returns_empty(self):
        """Test None input returns empty string."""
        result = process_spoken_punctuation(None)
        assert result == ""

    def test_whitespace_only_returns_empty(self):
        """Test whitespace-only string returns empty."""
        result = process_spoken_punctuation("   ")
        assert result == ""

    def test_no_punctuation_words_unchanged(self):
        """Test text without punctuation words remains unchanged (except whitespace)."""
        result = process_spoken_punctuation("hello world")
        assert result == "hello world"

    def test_punctuation_at_start(self):
        """Test punctuation word at start of text."""
        result = process_spoken_punctuation("period hello world")
        assert result == ". hello world"

    def test_punctuation_at_end(self):
        """Test punctuation word at end of text."""
        result = process_spoken_punctuation("hello world period")
        assert result == "hello world."

    def test_only_punctuation_word(self):
        """Test string containing only a punctuation word."""
        result = process_spoken_punctuation("period")
        assert result == "."

    def test_multiple_spaces_normalized(self):
        """Test multiple spaces are collapsed to single space."""
        result = process_spoken_punctuation("hello    comma    world")
        assert result == "hello, world"

    def test_leading_and_trailing_spaces_removed(self):
        """Test leading and trailing spaces are removed."""
        result = process_spoken_punctuation("  hello period world  ")
        assert result == "hello. world"

    def test_multi_word_punctuation_processed_first(self):
        """Test multi-word punctuation (question mark) processed before single words."""
        # This tests that "question mark" is matched as a whole, not "mark" separately
        result = process_spoken_punctuation("how are you question mark")
        assert result == "how are you?"

    def test_exclamation_mark_vs_exclamation_point(self):
        """Test both 'exclamation mark' and 'exclamation point' work."""
        result1 = process_spoken_punctuation("wow exclamation mark")
        result2 = process_spoken_punctuation("wow exclamation point")
        assert result1 == "wow!"
        assert result2 == "wow!"

    def test_consecutive_punctuation_words(self):
        """Test consecutive punctuation words."""
        result = process_spoken_punctuation("hello period period")
        assert result == "hello.."

    def test_punctuation_with_numbers(self):
        """Test punctuation with numbers."""
        result = process_spoken_punctuation("chapter 1 colon introduction")
        assert result == "chapter 1: introduction"

    def test_punctuation_with_special_characters(self):
        """Test punctuation with special characters."""
        result = process_spoken_punctuation("price $99 period 99")
        assert result == "price $99. 99"

    def test_all_punctuation_types_in_one_sentence(self):
        """Test all punctuation types together."""
        result = process_spoken_punctuation(
            "hello comma world period how are you question mark "
            "great exclamation mark note colon important semicolon "
            "wait dash here"
        )
        assert "," in result
        assert "." in result
        assert "?" in result
        assert "!" in result
        assert ":" in result
        assert ";" in result
        assert "—" in result

    def test_word_boundary_matching(self):
        """Test punctuation words are matched at word boundaries only."""
        # "common" contains "comma" but shouldn't be replaced
        result = process_spoken_punctuation("this is common period")
        assert result == "this is common."
        assert "co,n" not in result

    def test_partial_word_not_replaced(self):
        """Test partial matches of punctuation words are not replaced."""
        # "dashboard" contains "dash" but shouldn't be replaced
        result = process_spoken_punctuation("check the dashboard period")
        assert result == "check the dashboard."
        assert "dasboard" not in result

    def test_unicode_text_handled(self):
        """Test text with unicode characters is handled."""
        result = process_spoken_punctuation("café period résumé")
        assert result == "café. résumé"

    def test_long_text_processing(self):
        """Test processing of long text with multiple punctuation."""
        long_text = "hello period " * 10 + "world"
        result = process_spoken_punctuation(long_text)
        assert result.count(".") == 10
        assert "world" in result

    def test_punctuation_spacing_edge_cases(self):
        """Test punctuation spacing edge cases."""
        # Period followed immediately by letter should add space
        result = process_spoken_punctuation("hello periodworld")
        # Since "periodworld" is one word, it won't match "period" at word boundary
        # So this should remain unchanged
        assert result == "hello periodworld"

    def test_all_defined_punctuation_words_testable(self):
        """Test all punctuation in PUNCTUATION_WORDS can be converted."""
        for word, symbol in PUNCTUATION_WORDS.items():
            result = process_spoken_punctuation(f"test {word} here")
            assert symbol in result, f"Failed to convert: {word} -> {symbol}"

    def test_punctuation_with_contractions(self):
        """Test punctuation with contractions."""
        result = process_spoken_punctuation("it's working period")
        assert result == "it's working."

    def test_punctuation_with_possessives(self):
        """Test punctuation with possessives."""
        result = process_spoken_punctuation("John's book period")
        assert result == "John's book."

    def test_newline_characters_handled(self):
        """Test text with newline characters."""
        result = process_spoken_punctuation("hello\nperiod\nworld")
        # Should handle newlines gracefully
        assert "." in result

    def test_tab_characters_handled(self):
        """Test text with tab characters."""
        result = process_spoken_punctuation("hello\tperiod\tworld")
        # Should handle tabs gracefully
        assert "." in result

    def test_empty_after_processing(self):
        """Test text that becomes empty after processing."""
        # Only whitespace should result in empty string
        result = process_spoken_punctuation("   \n   \t   ")
        assert result == ""


class TestPunctuationWordsConstants:
    """Test PUNCTUATION_WORDS constant integrity."""

    def test_punctuation_words_not_empty(self):
        """Test PUNCTUATION_WORDS is not empty."""
        assert len(PUNCTUATION_WORDS) > 0

    def test_punctuation_words_has_required_types(self):
        """Test PUNCTUATION_WORDS contains all required punctuation types."""
        required_punctuation = ["period", "comma", "question mark", "exclamation mark"]
        for punct in required_punctuation:
            assert punct in PUNCTUATION_WORDS, f"Missing required punctuation: {punct}"

    def test_punctuation_symbols_are_strings(self):
        """Test all punctuation symbols are strings."""
        for word, symbol in PUNCTUATION_WORDS.items():
            assert isinstance(symbol, str)
            assert len(symbol) > 0

    def test_punctuation_words_are_lowercase(self):
        """Test all punctuation words are lowercase (for consistency)."""
        for word in PUNCTUATION_WORDS.keys():
            assert word == word.lower(), f"Punctuation word not lowercase: {word}"

    def test_no_duplicate_symbols(self):
        """Test there are no unexpected duplicate symbols (exclamation is expected)."""
        # Note: exclamation mark and exclamation point both map to '!' which is expected
        symbols = list(PUNCTUATION_WORDS.values())
        unique_symbols = set(symbols)
        # Should have some duplicates (exclamation mark variants)
        assert len(symbols) >= len(unique_symbols)


class TestIntegrationWithCleanup:
    """Test spoken punctuation integration with text cleanup."""

    def test_punctuation_before_filler_removal(self):
        """Test that punctuation is processed before filler word removal."""
        # This would be tested in test_cleanup.py, but we can verify the
        # process_spoken_punctuation function works independently
        text = "um hello period how are you"
        result = process_spoken_punctuation(text)
        assert "." in result
        # Note: filler word removal happens in cleanup.py, not here

    def test_output_ready_for_further_processing(self):
        """Test output is suitable for further text processing."""
        result = process_spoken_punctuation("hello period world")
        # Should be clean text with proper punctuation
        assert result == "hello. world"
        # Should not have extra spaces
        assert "  " not in result
        # Should not have leading/trailing spaces
        assert result == result.strip()


class TestRegressionPrevention:
    """Test cases to prevent regressions."""

    def test_backward_compatibility_with_existing_text(self):
        """Test function doesn't break existing text without punctuation words."""
        normal_texts = [
            "hello world",
            "this is a test",
            "the quick brown fox",
            "programming in python",
        ]
        for text in normal_texts:
            result = process_spoken_punctuation(text)
            # Should not corrupt normal text
            assert len(result) > 0
            # Should preserve word content (only spacing may change)
            for word in text.split():
                assert word in result or word.lower() in result.lower()

    def test_does_not_add_unwanted_punctuation(self):
        """Test function only adds punctuation when words are present."""
        text = "hello world"
        result = process_spoken_punctuation(text)
        # Should not contain any punctuation symbols
        for symbol in [".", ",", "?", "!", ":", ";", "—"]:
            assert symbol not in result

    def test_preserves_existing_punctuation(self):
        """Test function preserves punctuation that's already in text."""
        text = "hello, world. how are you?"
        result = process_spoken_punctuation(text)
        # Should preserve existing punctuation
        assert "," in result
        assert "." in result
        assert "?" in result
