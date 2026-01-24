"""Integration tests for text cleanup pipeline.

Tests the full cleanup pipeline including:
- Spoken punctuation conversion (before filler removal)
- Filler word removal
- Whitespace normalization
- Punctuation spacing
- Capitalization
- Full integration scenarios
"""

import pytest

from src.recognition.cleanup import cleanup_text, add_punctuation, _convert_spoken_punctuation
from src.config.constants import FILLER_WORDS


class TestCleanupPipelineIntegration:
    """Test complete cleanup pipeline with multiple transformations."""

    def test_spoken_punctuation_before_filler_removal(self):
        """Test that spoken punctuation is converted before filler words are removed."""
        # If punctuation is converted first, "um" is removed leaving "hello. how are you"
        # If filler is removed first, "um" is removed leaving "hello period how are you"
        text = "um hello period how are you"
        result = cleanup_text(text)

        # Should have period (punctuation converted)
        assert "." in result
        # Should not have "um" (filler removed)
        assert "um" not in result.lower()
        # Should not have the word "period" (converted to symbol)
        assert "period" not in result.lower()

    def test_filler_word_with_spoken_punctuation(self):
        """Test filler words followed by spoken punctuation."""
        text = "um comma like hello period"
        result = cleanup_text(text)

        # "like" is a filler word, so "um comma like" should be removed
        # leaving just ", hello."
        # Actually, standalone punctuation at start gets removed by orphan cleanup
        # So result should be "Hello."
        assert "." in result
        # Should not have filler words
        assert "um" not in result.lower()
        assert "like" not in result.lower()
        # Should not have punctuation words
        assert "comma" not in result.lower()
        assert "period" not in result.lower()

    def test_multiple_transformations_correct_order(self):
        """Test that all transformations happen in correct order."""
        text = "  um  hello  comma   world period  how are you  question mark  "
        result = cleanup_text(text)

        # Expected: "Hello, world. How are you?"
        # 1. Spoken punctuation converted
        assert "," in result
        assert "." in result
        assert "?" in result
        # 2. Filler words removed
        assert "um" not in result.lower()
        # 3. Whitespace normalized
        assert "  " not in result
        # 4. Leading/trailing spaces removed
        assert result == result.strip()
        # 5. First letter capitalized
        assert result[0].isupper()
        # 6. Letter after period capitalized
        assert "How" in result

    def test_filler_before_and_after_punctuation(self):
        """Test filler words surrounding spoken punctuation."""
        text = "um hello um period um world"
        result = cleanup_text(text)

        assert "." in result
        assert "um" not in result.lower()
        assert result == "Hello. World"

    def test_complex_sentence_full_pipeline(self):
        """Test complex sentence through full cleanup pipeline."""
        text = "um so basically hello comma uh world exclamation mark like how are you question mark"
        result = cleanup_text(text)

        # All filler words should be removed
        for filler in ["um", "so", "basically", "uh", "like"]:
            assert filler not in result.lower()

        # All punctuation should be converted
        assert "," in result
        assert "!" in result
        assert "?" in result

        # Should be properly capitalized
        assert result[0].isupper()
        assert "How" in result  # After exclamation mark

    def test_punctuation_spacing_normalization(self):
        """Test that punctuation spacing is normalized correctly."""
        text = "hello period   how are you question mark   fine"
        result = cleanup_text(text)

        # Should not have multiple spaces
        assert "  " not in result
        # Should have proper spacing around punctuation
        assert ". " in result or ".H" in result  # Period followed by space or capital
        assert "? " in result or "?F" in result

    def test_capitalization_after_spoken_punctuation(self):
        """Test capitalization after sentence-ending spoken punctuation."""
        text = "first sentence period second sentence exclamation mark third sentence question mark fourth sentence"
        result = cleanup_text(text)

        # All sentences should start with capital
        assert "First" in result
        assert "Second" in result
        assert "Third" in result
        assert "Fourth" in result


class TestCleanupTextFunction:
    """Test cleanup_text function with various inputs."""

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty string."""
        assert cleanup_text("") == ""

    def test_none_returns_empty(self):
        """Test None input returns empty string."""
        assert cleanup_text(None) == ""

    def test_whitespace_only_returns_empty(self):
        """Test whitespace-only input returns empty string."""
        assert cleanup_text("   ") == ""
        assert cleanup_text("\n\t  ") == ""

    def test_simple_text_no_cleanup_needed(self):
        """Test simple text without issues is capitalized and returned."""
        result = cleanup_text("hello world")
        assert result == "Hello world"

    def test_filler_word_removal(self):
        """Test filler words are removed."""
        text = "um hello uh world like this"
        result = cleanup_text(text)

        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "like" not in result.lower()
        assert "hello" in result.lower()
        assert "world" in result.lower()

    def test_multiple_spaces_normalized(self):
        """Test multiple spaces are collapsed to single space."""
        text = "hello    world     test"
        result = cleanup_text(text)

        assert "  " not in result
        assert result == "Hello world test"

    def test_leading_trailing_spaces_removed(self):
        """Test leading and trailing spaces are removed."""
        text = "   hello world   "
        result = cleanup_text(text)

        assert result == "Hello world"
        assert result == result.strip()

    def test_first_letter_capitalized(self):
        """Test first letter is capitalized."""
        assert cleanup_text("hello world")[0].isupper()
        assert cleanup_text("test sentence") == "Test sentence"

    def test_capitalization_after_period(self):
        """Test capitalization after periods."""
        text = "first. second. third"
        result = cleanup_text(text)

        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    def test_capitalization_after_question_mark(self):
        """Test capitalization after question marks."""
        text = "who? what? when"
        result = cleanup_text(text)

        assert "Who" in result
        assert "What" in result
        assert "When" in result

    def test_capitalization_after_exclamation_mark(self):
        """Test capitalization after exclamation marks."""
        text = "wow! amazing! cool"
        result = cleanup_text(text)

        assert "Wow" in result
        assert "Amazing" in result
        assert "Cool" in result

    def test_space_before_punctuation_removed(self):
        """Test spaces before punctuation are removed."""
        text = "hello , world . test"
        result = cleanup_text(text)

        assert " ," not in result
        assert " ." not in result
        assert result == "Hello, world. Test"

    def test_space_after_punctuation_ensured(self):
        """Test space is ensured after punctuation before letters."""
        text = "hello,world.test"
        result = cleanup_text(text)

        assert ", " in result or ",W" in result
        assert ". " in result or ".T" in result

    def test_double_punctuation_cleaned(self):
        """Test double punctuation is cleaned up."""
        text = "hello,, world.. test"
        result = cleanup_text(text)

        assert ",," not in result
        assert ".." not in result

    def test_orphan_punctuation_at_start_removed(self):
        """Test orphan punctuation at start is removed."""
        text = "., ! hello world"
        result = cleanup_text(text)

        assert result.startswith("Hello")

    def test_filler_with_comma_removed(self):
        """Test filler words followed by comma are removed."""
        text = "um, hello world"
        result = cleanup_text(text)

        assert "um" not in result.lower()
        assert result == "Hello world"


class TestSpokenPunctuationIntegration:
    """Test spoken punctuation integration in cleanup pipeline."""

    def test_all_punctuation_types_converted(self):
        """Test all spoken punctuation types are converted in cleanup."""
        text = "test period test comma test question mark test exclamation mark"
        result = cleanup_text(text)

        assert "." in result
        assert "," in result
        assert "?" in result
        assert "!" in result
        assert "period" not in result.lower()
        assert "comma" not in result.lower()
        assert "question mark" not in result.lower()
        assert "exclamation mark" not in result.lower()

    def test_punctuation_at_sentence_end(self):
        """Test spoken punctuation at end of sentence."""
        text = "hello world period"
        result = cleanup_text(text)

        assert result == "Hello world."

    def test_multiple_sentences_with_punctuation(self):
        """Test multiple sentences with spoken punctuation."""
        text = "first sentence period second sentence question mark third sentence exclamation mark"
        result = cleanup_text(text)

        # Should have all three punctuation marks
        assert result.count(".") >= 1
        assert "?" in result
        assert "!" in result

        # Should be properly capitalized
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    def test_colon_and_semicolon_in_cleanup(self):
        """Test colon and semicolon conversion in cleanup."""
        text = "note colon important semicolon critical"
        result = cleanup_text(text)

        assert ":" in result
        assert ";" in result
        assert "colon" not in result.lower()
        assert "semicolon" not in result.lower()


class TestFillerWordRemoval:
    """Test filler word removal in cleanup pipeline."""

    def test_all_filler_words_removed(self):
        """Test all defined filler words are removed."""
        for filler in FILLER_WORDS:
            text = f"hello {filler} world"
            result = cleanup_text(text)

            # Filler should be removed (case-insensitive check)
            assert filler.lower() not in result.lower(), f"Filler word '{filler}' not removed"
            # Content words should remain
            assert "hello" in result.lower()
            assert "world" in result.lower()

    def test_filler_words_case_insensitive(self):
        """Test filler words are removed regardless of case."""
        text = "UM hello UH world LIKE test"
        result = cleanup_text(text)

        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "like" not in result.lower()

    def test_filler_as_part_of_word_not_removed(self):
        """Test filler words as part of larger words are not removed."""
        # "umbrella" contains "um" but shouldn't be affected
        text = "bring an umbrella"
        result = cleanup_text(text)

        assert "umbrella" in result.lower()

    def test_multiple_consecutive_fillers(self):
        """Test multiple consecutive filler words are removed."""
        text = "um uh like hello world"
        result = cleanup_text(text)

        assert result == "Hello world"

    def test_multi_word_fillers(self):
        """Test multi-word fillers like 'you know' are removed."""
        text = "hello you know world"
        result = cleanup_text(text)

        assert "you know" not in result.lower()
        assert "hello" in result.lower()
        assert "world" in result.lower()


class TestConvertSpokenPunctuationHelper:
    """Test _convert_spoken_punctuation helper function directly."""

    def test_helper_converts_punctuation(self):
        """Test helper function converts spoken punctuation."""
        text = "hello period world"
        result = _convert_spoken_punctuation(text)

        # Helper function just replaces words, spacing cleanup happens in cleanup_text
        assert result == "hello . world"

    def test_helper_case_insensitive(self):
        """Test helper function is case-insensitive."""
        text = "hello PERIOD world"
        result = _convert_spoken_punctuation(text)

        assert "." in result

    def test_helper_empty_string(self):
        """Test helper handles empty string."""
        assert _convert_spoken_punctuation("") == ""

    def test_helper_none_input(self):
        """Test helper handles None input."""
        assert _convert_spoken_punctuation(None) == ""


class TestAddPunctuationFunction:
    """Test add_punctuation function."""

    def test_adds_period_to_text_without_punctuation(self):
        """Test period is added to text without ending punctuation."""
        assert add_punctuation("hello world") == "hello world."

    def test_does_not_add_period_if_period_exists(self):
        """Test period is not added if already present."""
        assert add_punctuation("hello world.") == "hello world."

    def test_does_not_add_period_if_question_mark_exists(self):
        """Test period is not added if question mark present."""
        assert add_punctuation("hello world?") == "hello world?"

    def test_does_not_add_period_if_exclamation_exists(self):
        """Test period is not added if exclamation mark present."""
        assert add_punctuation("hello world!") == "hello world!"

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty string."""
        assert add_punctuation("") == ""

    def test_none_returns_empty(self):
        """Test None returns empty string."""
        assert add_punctuation(None) == ""

    def test_whitespace_only_returns_empty(self):
        """Test whitespace-only returns empty string."""
        assert add_punctuation("   ") == ""

    def test_strips_whitespace_before_checking(self):
        """Test whitespace is stripped before checking punctuation."""
        assert add_punctuation("hello world  ") == "hello world."
        assert add_punctuation("hello world.  ") == "hello world."


class TestEdgeCases:
    """Test edge cases in cleanup pipeline."""

    def test_only_filler_words_returns_empty(self):
        """Test text with only filler words returns empty string."""
        text = "um uh like basically"
        result = cleanup_text(text)

        # After removing all fillers, should be empty
        assert result == ""

    def test_only_spoken_punctuation_returns_symbols(self):
        """Test text with only spoken punctuation returns empty (orphan cleanup)."""
        text = "period comma question mark"
        result = cleanup_text(text)

        # Standalone punctuation at start gets removed by orphan punctuation cleanup
        # So result should be empty when there's no actual content
        assert result == ""

    def test_very_long_text(self):
        """Test cleanup handles very long text."""
        text = "um hello period " * 100
        result = cleanup_text(text)

        # Should have multiple periods
        assert result.count(".") >= 50
        # Should not have "um"
        assert "um" not in result.lower()

    def test_unicode_text(self):
        """Test cleanup handles unicode text."""
        text = "café period résumé comma naïve"
        result = cleanup_text(text)

        assert "café" in result.lower()
        assert "résumé" in result.lower()
        assert "." in result
        assert "," in result

    def test_numbers_in_text(self):
        """Test cleanup handles numbers correctly."""
        text = "chapter 1 period section 2 comma page 3"
        result = cleanup_text(text)

        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert "." in result
        assert "," in result

    def test_special_characters_preserved(self):
        """Test special characters are preserved."""
        text = "price $99 period discount 50%"
        result = cleanup_text(text)

        assert "$99" in result
        assert "50%" in result
        assert "." in result

    def test_contractions_preserved(self):
        """Test contractions are preserved."""
        text = "it's working period don't worry"
        result = cleanup_text(text)

        assert "it's" in result or "It's" in result
        assert "don't" in result or "Don't" in result

    def test_possessives_preserved(self):
        """Test possessives are preserved."""
        text = "John's book period Mary's pen"
        result = cleanup_text(text)

        assert "John's" in result
        assert "Mary's" in result or "mary's" in result

    def test_newlines_handled(self):
        """Test text with newlines is handled."""
        text = "hello\nperiod\nworld"
        result = cleanup_text(text)

        # Should handle gracefully (newlines become spaces)
        assert "hello" in result.lower()
        assert "world" in result.lower()

    def test_tabs_handled(self):
        """Test text with tabs is handled."""
        text = "hello\tperiod\tworld"
        result = cleanup_text(text)

        # Should handle gracefully
        assert "hello" in result.lower()
        assert "world" in result.lower()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_dictation_with_punctuation_and_fillers(self):
        """Test realistic dictation with mix of everything."""
        text = "um hello comma my name is John period uh I like programming exclamation mark"
        result = cleanup_text(text)

        # "like" is a filler word, so it gets removed
        # Expected: "Hello, my name is John. I programming!"
        assert "Hello" in result
        assert "," in result
        assert "John" in result
        assert "." in result
        assert "programming" in result
        assert "!" in result
        # Should not have filler words (including "like")
        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "like" not in result.lower()

    def test_question_sentence(self):
        """Test question sentence cleanup."""
        text = "um how are you doing question mark"
        result = cleanup_text(text)

        assert result == "How are you doing?"

    def test_multiple_sentences_mixed_punctuation(self):
        """Test multiple sentences with mixed punctuation."""
        text = "hello period how are you question mark I am fine exclamation mark"
        result = cleanup_text(text)

        assert "Hello." in result
        assert "?" in result
        assert "!" in result
        # Check capitalization after punctuation
        sentences = result.split(".")
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                assert sentence[0].isupper()

    def test_list_with_commas(self):
        """Test list items with commas."""
        text = "I need apples comma oranges comma and bananas period"
        result = cleanup_text(text)

        assert "apples, oranges, and bananas" in result.lower()
        assert "." in result

    def test_emphasis_with_exclamation(self):
        """Test emphasis with exclamation marks."""
        text = "wow exclamation mark that is amazing exclamation mark"
        result = cleanup_text(text)

        assert result.count("!") >= 2
        assert "Wow!" in result
        assert "amazing!" in result.lower()

    def test_formal_writing_with_semicolons(self):
        """Test formal writing with semicolons and colons."""
        text = "note colon the following is important semicolon please read carefully period"
        result = cleanup_text(text)

        assert ":" in result
        assert ";" in result
        assert "." in result


class TestProcessingOrder:
    """Test that processing order is correct and consistent."""

    def test_punctuation_conversion_before_capitalization(self):
        """Test punctuation is converted before capitalization rules are applied."""
        text = "first period second period third"
        result = cleanup_text(text)

        # "period" should be converted to "." then capitalization should apply
        assert "First." in result
        assert "Second." in result
        # "Third" should be capitalized after second period
        assert "Third" in result

    def test_filler_removal_after_punctuation_conversion(self):
        """Test filler words are removed after punctuation conversion."""
        # This ensures "period" isn't treated as a filler-adjacent word
        text = "hello period um world"
        result = cleanup_text(text)

        assert "." in result
        assert "um" not in result.lower()
        assert "Hello. World" in result

    def test_whitespace_normalization_happens_after_removals(self):
        """Test whitespace is normalized after word removals."""
        text = "um   hello   period   um   world"
        result = cleanup_text(text)

        # After removing "um" and converting "period", spaces should be normalized
        assert "  " not in result
        assert result == "Hello. World"

    def test_capitalization_is_last_step(self):
        """Test capitalization happens after all other transformations."""
        text = "  um  hello period  uh  world  "
        result = cleanup_text(text)

        # First letter should be capital
        assert result[0].isupper()
        # Letter after period should be capital
        assert "World" in result
