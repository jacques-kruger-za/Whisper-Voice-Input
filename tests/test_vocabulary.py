"""Unit tests for vocabulary management."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.recognition.vocabulary import VocabularyManager, get_vocabulary_manager


class TestVocabularyManagerInitialization:
    """Test VocabularyManager initialization and file loading."""

    def test_vocabulary_manager_initialization(self, tmp_path):
        """Test VocabularyManager initializes with empty vocabulary."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            assert vm.get_vocabulary() == []

    def test_load_existing_vocabulary_file(self, tmp_path):
        """Test loading vocabulary from existing file."""
        vocab_file = tmp_path / "vocabulary.json"
        test_vocab = ["PyQt6", "faster-whisper", "platformdirs"]
        vocab_file.write_text(json.dumps(test_vocab))

        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            assert vm.get_vocabulary() == test_vocab

    def test_load_empty_vocabulary_file(self, tmp_path):
        """Test loading empty vocabulary list from file."""
        vocab_file = tmp_path / "vocabulary.json"
        vocab_file.write_text(json.dumps([]))

        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            assert vm.get_vocabulary() == []

    def test_load_invalid_json_file(self, tmp_path):
        """Test handling of invalid JSON in vocabulary file."""
        vocab_file = tmp_path / "vocabulary.json"
        vocab_file.write_text("{ invalid json }")

        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Should fallback to empty list on JSON error
            assert vm.get_vocabulary() == []

    def test_load_non_list_json(self, tmp_path):
        """Test handling of non-list JSON data."""
        vocab_file = tmp_path / "vocabulary.json"
        vocab_file.write_text(json.dumps({"key": "value"}))

        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Should handle non-list data gracefully
            assert vm.get_vocabulary() == []

    def test_load_vocabulary_with_empty_strings(self, tmp_path):
        """Test loading vocabulary behavior with empty and whitespace strings."""
        vocab_file = tmp_path / "vocabulary.json"
        # Mix of valid words, empty string, and whitespace-only string
        test_vocab = ["word1", "", "word2", "   ", "word3"]
        vocab_file.write_text(json.dumps(test_vocab))

        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            loaded = vm.get_vocabulary()
            # Valid words should be loaded
            assert "word1" in loaded
            assert "word2" in loaded
            assert "word3" in loaded
            # Originally empty strings ("") are filtered out by 'if word' check
            # Whitespace-only strings ("   ") pass 'if word', then strip() to ""
            # This means one empty string may exist from whitespace-only input
            # Count total words (should have word1, word2, word3, and possibly empty from whitespace)
            assert len(loaded) == 4  # word1, word2, empty from whitespace, word3


class TestAddWord:
    """Test VocabularyManager.add_word functionality."""

    def test_add_single_word(self, tmp_path):
        """Test adding a single word to vocabulary."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            result = vm.add_word("PyQt6")
            assert result is True
            assert "PyQt6" in vm.get_vocabulary()

    def test_add_multiple_words(self, tmp_path):
        """Test adding multiple words to vocabulary."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("PyQt6")
            vm.add_word("faster-whisper")
            vm.add_word("platformdirs")
            vocab = vm.get_vocabulary()
            assert len(vocab) == 3
            assert "PyQt6" in vocab
            assert "faster-whisper" in vocab
            assert "platformdirs" in vocab

    def test_add_word_with_whitespace(self, tmp_path):
        """Test adding word with leading/trailing whitespace."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            result = vm.add_word("  PyQt6  ")
            assert result is True
            assert "PyQt6" in vm.get_vocabulary()
            assert "  PyQt6  " not in vm.get_vocabulary()

    def test_add_empty_string(self, tmp_path):
        """Test adding empty string is rejected."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            result = vm.add_word("")
            assert result is False
            assert len(vm.get_vocabulary()) == 0

    def test_add_whitespace_only(self, tmp_path):
        """Test adding whitespace-only string is rejected."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            result = vm.add_word("   ")
            assert result is False
            assert len(vm.get_vocabulary()) == 0

    def test_add_none(self, tmp_path):
        """Test adding None is rejected."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            result = vm.add_word(None)
            assert result is False
            assert len(vm.get_vocabulary()) == 0

    def test_add_duplicate_word_case_sensitive(self, tmp_path):
        """Test adding exact duplicate is rejected."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("PyQt6")
            result = vm.add_word("PyQt6")
            assert result is False
            assert vm.get_vocabulary().count("PyQt6") == 1

    def test_add_duplicate_word_case_insensitive(self, tmp_path):
        """Test duplicate detection is case-insensitive."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("PyQt6")
            result = vm.add_word("pyqt6")
            assert result is False
            result2 = vm.add_word("PYQT6")
            assert result2 is False
            assert len(vm.get_vocabulary()) == 1

    def test_add_word_max_length(self, tmp_path):
        """Test adding word exceeding max length (100 chars) is rejected."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            long_word = "a" * 101
            result = vm.add_word(long_word)
            assert result is False
            assert len(vm.get_vocabulary()) == 0

    def test_add_word_exactly_max_length(self, tmp_path):
        """Test adding word at max length (100 chars) is accepted."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            max_word = "a" * 100
            result = vm.add_word(max_word)
            assert result is True
            assert max_word in vm.get_vocabulary()

    def test_add_word_with_special_characters(self, tmp_path):
        """Test adding words with special characters."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            special_words = ["C++", "C#", "socket.io", "three.js", "vue.js"]
            for word in special_words:
                result = vm.add_word(word)
                assert result is True
            vocab = vm.get_vocabulary()
            for word in special_words:
                assert word in vocab

    def test_add_word_with_unicode(self, tmp_path):
        """Test adding words with unicode characters."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            unicode_words = ["café", "naïve", "résumé", "北京"]
            for word in unicode_words:
                result = vm.add_word(word)
                assert result is True
            vocab = vm.get_vocabulary()
            for word in unicode_words:
                assert word in vocab


class TestRemoveWord:
    """Test VocabularyManager.remove_word functionality."""

    def test_remove_existing_word(self, tmp_path):
        """Test removing an existing word."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("PyQt6")
            result = vm.remove_word("PyQt6")
            assert result is True
            assert "PyQt6" not in vm.get_vocabulary()

    def test_remove_non_existing_word(self, tmp_path):
        """Test removing a word that doesn't exist."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            result = vm.remove_word("NonExistent")
            assert result is False

    def test_remove_from_multiple_words(self, tmp_path):
        """Test removing one word from multiple words."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("word1")
            vm.add_word("word2")
            vm.add_word("word3")
            vm.remove_word("word2")
            vocab = vm.get_vocabulary()
            assert "word1" in vocab
            assert "word2" not in vocab
            assert "word3" in vocab

    def test_remove_all_words_individually(self, tmp_path):
        """Test removing all words one by one."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            words = ["word1", "word2", "word3"]
            for word in words:
                vm.add_word(word)
            for word in words:
                vm.remove_word(word)
            assert len(vm.get_vocabulary()) == 0


class TestClearVocabulary:
    """Test VocabularyManager.clear functionality."""

    def test_clear_empty_vocabulary(self, tmp_path):
        """Test clearing empty vocabulary."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.clear()
            assert len(vm.get_vocabulary()) == 0

    def test_clear_with_words(self, tmp_path):
        """Test clearing vocabulary with words."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("word1")
            vm.add_word("word2")
            vm.clear()
            assert len(vm.get_vocabulary()) == 0

    def test_add_after_clear(self, tmp_path):
        """Test adding words after clearing."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("old_word")
            vm.clear()
            vm.add_word("new_word")
            vocab = vm.get_vocabulary()
            assert "old_word" not in vocab
            assert "new_word" in vocab
            assert len(vocab) == 1


class TestGetVocabulary:
    """Test VocabularyManager.get_vocabulary functionality."""

    def test_get_vocabulary_returns_copy(self, tmp_path):
        """Test get_vocabulary returns a copy, not reference."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("test")
            vocab1 = vm.get_vocabulary()
            vocab1.append("modified")
            vocab2 = vm.get_vocabulary()
            # Original should not be modified
            assert "modified" not in vocab2
            assert len(vocab2) == 1

    def test_get_vocabulary_empty(self, tmp_path):
        """Test getting empty vocabulary."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vocab = vm.get_vocabulary()
            assert vocab == []
            assert isinstance(vocab, list)


class TestGenerateInitialPrompt:
    """Test VocabularyManager.generate_initial_prompt functionality."""

    def test_generate_prompt_empty_vocabulary(self, tmp_path):
        """Test generating prompt with empty vocabulary returns empty string."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            prompt = vm.generate_initial_prompt()
            assert prompt == ""

    def test_generate_prompt_single_word(self, tmp_path):
        """Test generating prompt with single word."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("PyQt6")
            prompt = vm.generate_initial_prompt()
            assert prompt == "Glossary: PyQt6"
            assert len(prompt) <= 224

    def test_generate_prompt_multiple_words(self, tmp_path):
        """Test generating prompt with multiple words."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            words = ["PyQt6", "faster-whisper", "platformdirs"]
            for word in words:
                vm.add_word(word)
            prompt = vm.generate_initial_prompt()
            assert prompt.startswith("Glossary: ")
            for word in words:
                assert word in prompt
            assert len(prompt) <= 224

    def test_generate_prompt_format(self, tmp_path):
        """Test prompt format is 'Glossary: word1, word2, word3'."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("word1")
            vm.add_word("word2")
            prompt = vm.generate_initial_prompt()
            assert prompt == "Glossary: word1, word2"

    def test_generate_prompt_224_character_limit(self, tmp_path):
        """Test prompt respects 224 character limit."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Add many words to exceed 224 chars
            for i in range(50):
                vm.add_word(f"word{i:02d}")
            prompt = vm.generate_initial_prompt()
            assert len(prompt) <= 224

    def test_generate_prompt_truncates_when_exceeding_limit(self, tmp_path):
        """Test prompt truncates vocabulary when exceeding 224 char limit."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Add words that will exceed limit
            long_words = ["verylongwordnumber" + str(i).zfill(3) for i in range(20)]
            for word in long_words:
                vm.add_word(word)
            prompt = vm.generate_initial_prompt()
            assert len(prompt) <= 224
            # Should still start with Glossary:
            assert prompt.startswith("Glossary: ")
            # Should contain at least the first word
            assert long_words[0] in prompt

    def test_generate_prompt_includes_as_many_words_as_fit(self, tmp_path):
        """Test prompt includes maximum words that fit within limit."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Add short words
            for i in range(50):
                vm.add_word(f"w{i}")
            prompt = vm.generate_initial_prompt()
            assert len(prompt) <= 224
            # Count how many words made it in
            words_in_prompt = prompt.replace("Glossary: ", "").split(", ")
            # Should have multiple words (not just one)
            assert len(words_in_prompt) > 1

    def test_generate_prompt_empty_string_when_first_word_too_long(self, tmp_path):
        """Test prompt returns empty when first word + prefix exceeds 224 chars."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Add a word so long that even with "Glossary: " it exceeds 224
            very_long_word = "a" * 220
            vm.add_word(very_long_word)
            prompt = vm.generate_initial_prompt()
            # Should return empty string as nothing fits
            assert prompt == ""

    def test_generate_prompt_preserves_word_order(self, tmp_path):
        """Test prompt preserves order of vocabulary words."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            words = ["first", "second", "third", "fourth"]
            for word in words:
                vm.add_word(word)
            prompt = vm.generate_initial_prompt()
            # Words should appear in order
            assert prompt == "Glossary: first, second, third, fourth"


class TestSaveFunctionality:
    """Test VocabularyManager save and persistence."""

    def test_save_creates_directory(self, tmp_path):
        """Test save creates data directory if it doesn't exist."""
        data_dir = tmp_path / "new_dir"
        vocab_file = data_dir / "vocabulary.json"

        with patch("src.recognition.vocabulary.user_data_dir", return_value=data_dir):
            vm = VocabularyManager()
            vm.add_word("test")
            # Directory should be created
            assert data_dir.exists()
            assert vocab_file.exists()

    def test_save_persists_data(self, tmp_path):
        """Test save persists vocabulary to file."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("PyQt6")
            vm.add_word("platformdirs")

            # Load file directly
            vocab_file = tmp_path / "vocabulary.json"
            with open(vocab_file) as f:
                data = json.load(f)

            assert "PyQt6" in data
            assert "platformdirs" in data

    def test_save_and_reload(self, tmp_path):
        """Test vocabulary persists across VocabularyManager instances."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            # First instance
            vm1 = VocabularyManager()
            vm1.add_word("word1")
            vm1.add_word("word2")

            # Second instance should load same data
            vm2 = VocabularyManager()
            vocab = vm2.get_vocabulary()
            assert "word1" in vocab
            assert "word2" in vocab
            assert len(vocab) == 2

    def test_save_after_remove(self, tmp_path):
        """Test save correctly persists after removing words."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm1 = VocabularyManager()
            vm1.add_word("keep")
            vm1.add_word("remove")
            vm1.remove_word("remove")

            vm2 = VocabularyManager()
            vocab = vm2.get_vocabulary()
            assert "keep" in vocab
            assert "remove" not in vocab

    def test_save_after_clear(self, tmp_path):
        """Test save correctly persists after clearing."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm1 = VocabularyManager()
            vm1.add_word("word1")
            vm1.clear()

            vm2 = VocabularyManager()
            assert len(vm2.get_vocabulary()) == 0


class TestGetVocabularyManagerSingleton:
    """Test get_vocabulary_manager singleton pattern."""

    def test_get_vocabulary_manager_returns_instance(self):
        """Test get_vocabulary_manager returns VocabularyManager instance."""
        vm = get_vocabulary_manager()
        assert isinstance(vm, VocabularyManager)

    def test_get_vocabulary_manager_returns_same_instance(self):
        """Test get_vocabulary_manager returns same instance on multiple calls."""
        vm1 = get_vocabulary_manager()
        vm2 = get_vocabulary_manager()
        assert vm1 is vm2

    def test_singleton_persists_state(self, tmp_path):
        """Test singleton pattern preserves state across calls."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            # Reset singleton for this test
            import src.recognition.vocabulary
            src.recognition.vocabulary._vocabulary_manager = None

            vm1 = get_vocabulary_manager()
            vm1.add_word("test_singleton")

            vm2 = get_vocabulary_manager()
            assert "test_singleton" in vm2.get_vocabulary()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_add_word_with_numbers(self, tmp_path):
        """Test adding words with numbers."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            words_with_numbers = ["Python3", "PyQt6", "Vue3", "Angular2", "mp3"]
            for word in words_with_numbers:
                result = vm.add_word(word)
                assert result is True
            vocab = vm.get_vocabulary()
            for word in words_with_numbers:
                assert word in vocab

    def test_vocabulary_with_commas(self, tmp_path):
        """Test vocabulary words containing commas."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            vm.add_word("Washington, D.C.")
            prompt = vm.generate_initial_prompt()
            assert "Washington, D.C." in prompt

    def test_multiple_operations_sequence(self, tmp_path):
        """Test sequence of multiple operations."""
        with patch("src.recognition.vocabulary.user_data_dir", return_value=tmp_path):
            vm = VocabularyManager()
            # Add
            vm.add_word("word1")
            vm.add_word("word2")
            assert len(vm.get_vocabulary()) == 2
            # Remove
            vm.remove_word("word1")
            assert len(vm.get_vocabulary()) == 1
            # Add more
            vm.add_word("word3")
            vm.add_word("word4")
            assert len(vm.get_vocabulary()) == 3
            # Clear
            vm.clear()
            assert len(vm.get_vocabulary()) == 0
            # Add after clear
            vm.add_word("fresh_start")
            assert len(vm.get_vocabulary()) == 1
            assert "fresh_start" in vm.get_vocabulary()
