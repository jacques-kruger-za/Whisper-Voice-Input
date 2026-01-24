"""Unit tests for command processor."""

import pytest
from unittest.mock import MagicMock, patch, call

from src.recognition.command_processor import CommandProcessor, HistoryEntry
from src.recognition.commands import CommandResult


class TestHistoryEntry:
    """Test HistoryEntry data class."""

    def test_history_entry_initialization(self):
        """Test HistoryEntry initializes correctly."""
        entry = HistoryEntry("dictation", {"text": "hello", "length": 5})
        assert entry.type == "dictation"
        assert entry.data == {"text": "hello", "length": 5}

    def test_history_entry_with_empty_data(self):
        """Test HistoryEntry with empty data dictionary."""
        entry = HistoryEntry("newline", {})
        assert entry.type == "newline"
        assert entry.data == {}

    def test_history_entry_repr(self):
        """Test HistoryEntry string representation."""
        entry = HistoryEntry("dictation", {"text": "test"})
        repr_str = repr(entry)
        assert "HistoryEntry" in repr_str
        assert "dictation" in repr_str
        assert "test" in repr_str


class TestCommandProcessorInitialization:
    """Test CommandProcessor initialization."""

    def test_default_initialization(self):
        """Test CommandProcessor initializes with default history size."""
        cp = CommandProcessor()
        assert cp.get_history_size() == 0
        assert cp._history_size == 10

    def test_custom_history_size(self):
        """Test CommandProcessor initializes with custom history size."""
        cp = CommandProcessor(history_size=5)
        assert cp._history_size == 5

    def test_initialization_with_large_history(self):
        """Test CommandProcessor with large history size."""
        cp = CommandProcessor(history_size=100)
        assert cp._history_size == 100

    def test_initialization_with_minimal_history(self):
        """Test CommandProcessor with minimal history size."""
        cp = CommandProcessor(history_size=1)
        assert cp._history_size == 1


class TestTrackDictation:
    """Test CommandProcessor.track_dictation functionality."""

    def test_track_single_dictation(self):
        """Test tracking single dictation."""
        cp = CommandProcessor()
        cp.track_dictation("hello world")
        assert cp.get_history_size() == 1

    def test_track_multiple_dictations(self):
        """Test tracking multiple dictations."""
        cp = CommandProcessor()
        cp.track_dictation("first")
        cp.track_dictation("second")
        cp.track_dictation("third")
        assert cp.get_history_size() == 3

    def test_track_empty_string_ignored(self):
        """Test empty string is not tracked."""
        cp = CommandProcessor()
        cp.track_dictation("")
        assert cp.get_history_size() == 0

    def test_track_whitespace_only_is_tracked(self):
        """Test whitespace-only string is tracked (has length)."""
        cp = CommandProcessor()
        cp.track_dictation("   ")
        assert cp.get_history_size() == 1

    def test_track_long_text(self):
        """Test tracking long text."""
        cp = CommandProcessor()
        long_text = "a" * 1000
        cp.track_dictation(long_text)
        assert cp.get_history_size() == 1

    def test_track_unicode_text(self):
        """Test tracking unicode text."""
        cp = CommandProcessor()
        cp.track_dictation("café résumé 北京")
        assert cp.get_history_size() == 1

    def test_track_dictation_stores_text_length(self):
        """Test dictation entry stores text length."""
        cp = CommandProcessor()
        text = "hello world"
        cp.track_dictation(text)
        # Access internal history to verify data
        entry = cp._history[0]
        assert entry.type == "dictation"
        assert entry.data["length"] == len(text)
        assert entry.data["text"] == text


class TestHistoryManagement:
    """Test history management and circular buffer behavior."""

    def test_history_circular_buffer_limit(self):
        """Test history respects circular buffer limit."""
        cp = CommandProcessor(history_size=3)
        cp.track_dictation("first")
        cp.track_dictation("second")
        cp.track_dictation("third")
        cp.track_dictation("fourth")  # Should push out "first"

        assert cp.get_history_size() == 3

    def test_history_circular_buffer_removes_oldest(self):
        """Test oldest entries are removed when limit is reached."""
        cp = CommandProcessor(history_size=3)
        cp.track_dictation("first")
        cp.track_dictation("second")
        cp.track_dictation("third")
        cp.track_dictation("fourth")

        # "first" should be gone, check by accessing internal history
        texts = [entry.data.get("text") for entry in cp._history]
        assert "first" not in texts
        assert "second" in texts
        assert "third" in texts
        assert "fourth" in texts

    def test_history_at_default_limit(self):
        """Test history with default 10 item limit."""
        cp = CommandProcessor()  # Default history_size=10
        for i in range(15):
            cp.track_dictation(f"text{i}")

        assert cp.get_history_size() == 10

    def test_clear_history(self):
        """Test clearing history."""
        cp = CommandProcessor()
        cp.track_dictation("test1")
        cp.track_dictation("test2")
        cp.clear_history()
        assert cp.get_history_size() == 0

    def test_clear_empty_history(self):
        """Test clearing already empty history."""
        cp = CommandProcessor()
        cp.clear_history()
        assert cp.get_history_size() == 0

    def test_operations_after_clear(self):
        """Test operations work correctly after clearing history."""
        cp = CommandProcessor()
        cp.track_dictation("before_clear")
        cp.clear_history()
        cp.track_dictation("after_clear")
        assert cp.get_history_size() == 1


class TestExecuteCommandDeleteLast:
    """Test execute_command with delete_last action."""

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_with_dictation(self, mock_press):
        """Test delete_last removes last dictation."""
        cp = CommandProcessor()
        cp.track_dictation("hello world")  # 11 characters

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        success = cp.execute_command(result)

        assert success is True
        # Should call backspace 11 times
        assert mock_press.call_count == 11
        mock_press.assert_called_with("backspace")

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_with_empty_history(self, mock_press):
        """Test delete_last with empty history returns False."""
        cp = CommandProcessor()

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        success = cp.execute_command(result)

        assert success is False
        mock_press.assert_not_called()

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_tracks_delete_operation(self, mock_press):
        """Test delete_last tracks the delete operation in history."""
        cp = CommandProcessor()
        cp.track_dictation("test text")

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        cp.execute_command(result)

        # History should now contain a delete entry
        assert cp.get_history_size() == 1
        entry = cp._history[0]
        assert entry.type == "delete"

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_removes_dictation_from_history(self, mock_press):
        """Test delete_last removes the dictation entry from history."""
        cp = CommandProcessor()
        cp.track_dictation("first")
        cp.track_dictation("second")
        initial_size = cp.get_history_size()

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        cp.execute_command(result)

        # One dictation removed, one delete added
        assert cp.get_history_size() == initial_size

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_finds_most_recent_dictation(self, mock_press):
        """Test delete_last finds and removes most recent dictation."""
        cp = CommandProcessor()
        cp.track_dictation("first")
        cp.track_dictation("second")
        cp.track_dictation("third")

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        cp.execute_command(result)

        # Should delete "third" (most recent)
        # Check that backspace was called with length of "third"
        assert mock_press.call_count == len("third")

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_with_special_characters(self, mock_press):
        """Test delete_last handles special characters correctly."""
        cp = CommandProcessor()
        text = "hello! world?"
        cp.track_dictation(text)

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        success = cp.execute_command(result)

        assert success is True
        assert mock_press.call_count == len(text)

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_last_with_zero_length_text(self, mock_press):
        """Test delete_last with zero-length dictation."""
        cp = CommandProcessor()
        # Manually create entry with 0 length (edge case)
        entry = HistoryEntry("dictation", {"text": "", "length": 0})
        cp._add_to_history(entry)

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        success = cp.execute_command(result)

        assert success is True
        mock_press.assert_not_called()  # No backspace for 0 length


class TestExecuteCommandUndo:
    """Test execute_command with undo action."""

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_dictation(self, mock_press):
        """Test undo reverses dictation by deleting text."""
        cp = CommandProcessor()
        cp.track_dictation("hello")  # 5 characters

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is True
        assert mock_press.call_count == 5
        mock_press.assert_called_with("backspace")

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_with_empty_history(self, mock_press):
        """Test undo with empty history returns False."""
        cp = CommandProcessor()

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is False
        mock_press.assert_not_called()

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_newline(self, mock_press):
        """Test undo reverses newline by deleting it."""
        cp = CommandProcessor()
        # Manually add newline entry
        entry = HistoryEntry("newline", {})
        cp._add_to_history(entry)

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is True
        assert mock_press.call_count == 1
        mock_press.assert_called_with("backspace")

    @patch("src.recognition.command_processor.inject_text")
    def test_undo_delete_restores_text(self, mock_inject):
        """Test undo reverses delete by restoring deleted text."""
        cp = CommandProcessor()
        # Manually add delete entry
        deleted_text = "restored text"
        entry = HistoryEntry("delete", {"deleted_text": deleted_text, "length": len(deleted_text)})
        cp._add_to_history(entry)

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is True
        mock_inject.assert_called_once_with(deleted_text)

    @patch("src.recognition.command_processor.inject_text")
    def test_undo_delete_without_stored_text(self, mock_inject):
        """Test undo delete without stored text returns False."""
        cp = CommandProcessor()
        # Delete entry without deleted_text
        entry = HistoryEntry("delete", {"length": 5})
        cp._add_to_history(entry)

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is False
        mock_inject.assert_not_called()

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_removes_entry_from_history(self, mock_press):
        """Test undo removes the entry from history."""
        cp = CommandProcessor()
        cp.track_dictation("test")
        assert cp.get_history_size() == 1

        result = CommandResult("undo", "undo", 100.0, "undo")
        cp.execute_command(result)

        assert cp.get_history_size() == 0

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_multiple_times(self, mock_press):
        """Test undo can be called multiple times."""
        cp = CommandProcessor()
        cp.track_dictation("first")
        cp.track_dictation("second")
        cp.track_dictation("third")

        result = CommandResult("undo", "undo", 100.0, "undo")

        # Undo three times
        cp.execute_command(result)
        assert cp.get_history_size() == 2

        cp.execute_command(result)
        assert cp.get_history_size() == 1

        cp.execute_command(result)
        assert cp.get_history_size() == 0

        # Fourth undo should fail
        success = cp.execute_command(result)
        assert success is False

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_up_to_history_limit(self, mock_press):
        """Test undo works up to history limit (10 items)."""
        cp = CommandProcessor(history_size=10)

        # Add 10 dictations
        for i in range(10):
            cp.track_dictation(f"text{i}")

        result = CommandResult("undo", "undo", 100.0, "undo")

        # Undo all 10
        for i in range(10):
            success = cp.execute_command(result)
            assert success is True

        # History should be empty now
        assert cp.get_history_size() == 0

        # One more undo should fail
        success = cp.execute_command(result)
        assert success is False

    def test_undo_unknown_entry_type(self):
        """Test undo with unknown entry type returns False."""
        cp = CommandProcessor()
        # Add unknown entry type
        entry = HistoryEntry("unknown_type", {})
        cp._add_to_history(entry)

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is False


class TestExecuteCommandInsertNewline:
    """Test execute_command with insert_newline action."""

    @patch("src.recognition.command_processor.inject_text")
    def test_insert_newline_success(self, mock_inject):
        """Test insert_newline inserts newline character."""
        mock_inject.return_value = True
        cp = CommandProcessor()

        result = CommandResult("new line", "insert_newline", 100.0, "new line")
        success = cp.execute_command(result)

        assert success is True
        mock_inject.assert_called_once_with("\n")

    @patch("src.recognition.command_processor.inject_text")
    def test_insert_newline_tracks_to_history(self, mock_inject):
        """Test insert_newline tracks to history."""
        mock_inject.return_value = True
        cp = CommandProcessor()

        result = CommandResult("new line", "insert_newline", 100.0, "new line")
        cp.execute_command(result)

        assert cp.get_history_size() == 1
        entry = cp._history[0]
        assert entry.type == "newline"

    @patch("src.recognition.command_processor.inject_text")
    def test_insert_newline_failure(self, mock_inject):
        """Test insert_newline handles injection failure."""
        mock_inject.return_value = False
        cp = CommandProcessor()

        result = CommandResult("new line", "insert_newline", 100.0, "new line")
        success = cp.execute_command(result)

        assert success is False

    @patch("src.recognition.command_processor.inject_text")
    def test_insert_newline_exception(self, mock_inject):
        """Test insert_newline handles exceptions gracefully."""
        mock_inject.side_effect = Exception("Injection failed")
        cp = CommandProcessor()

        result = CommandResult("new line", "insert_newline", 100.0, "new line")
        success = cp.execute_command(result)

        assert success is False

    @patch("src.recognition.command_processor.inject_text")
    def test_insert_multiple_newlines(self, mock_inject):
        """Test inserting multiple newlines."""
        mock_inject.return_value = True
        cp = CommandProcessor()

        result = CommandResult("new line", "insert_newline", 100.0, "new line")

        cp.execute_command(result)
        cp.execute_command(result)
        cp.execute_command(result)

        assert cp.get_history_size() == 3
        assert mock_inject.call_count == 3


class TestExecuteCommandUnknownAction:
    """Test execute_command with unknown action."""

    def test_unknown_action_returns_false(self):
        """Test unknown command action returns False."""
        cp = CommandProcessor()

        result = CommandResult("unknown", "unknown_action", 90.0, "unknown")
        success = cp.execute_command(result)

        assert success is False

    def test_unknown_action_does_not_modify_history(self):
        """Test unknown action does not modify history."""
        cp = CommandProcessor()

        result = CommandResult("unknown", "unknown_action", 90.0, "unknown")
        cp.execute_command(result)

        assert cp.get_history_size() == 0


class TestCommandProcessorIntegration:
    """Integration tests for complete workflow scenarios."""

    @patch("src.recognition.command_processor.inject_text")
    @patch("src.recognition.command_processor.pyautogui.press")
    def test_dictation_delete_workflow(self, mock_press, mock_inject):
        """Test complete dictation then delete workflow."""
        cp = CommandProcessor()

        # Dictate text
        cp.track_dictation("hello world")
        assert cp.get_history_size() == 1

        # Delete it
        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        success = cp.execute_command(result)

        assert success is True
        assert mock_press.call_count == len("hello world")
        assert cp.get_history_size() == 1  # Delete operation tracked

    @patch("src.recognition.command_processor.inject_text")
    @patch("src.recognition.command_processor.pyautogui.press")
    def test_dictation_undo_workflow(self, mock_press, mock_inject):
        """Test complete dictation then undo workflow."""
        cp = CommandProcessor()

        # Dictate text
        cp.track_dictation("test text")

        # Undo it
        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is True
        assert mock_press.call_count == len("test text")
        assert cp.get_history_size() == 0

    @patch("src.recognition.command_processor.inject_text")
    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_then_undo_workflow(self, mock_press, mock_inject):
        """Test delete then undo restores text."""
        mock_inject.return_value = True
        cp = CommandProcessor()

        # Dictate text
        original_text = "restore me"
        cp.track_dictation(original_text)

        # Delete it
        delete_result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        cp.execute_command(delete_result)

        # Undo the delete (should restore text)
        undo_result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(undo_result)

        assert success is True
        mock_inject.assert_called_with(original_text)

    @patch("src.recognition.command_processor.inject_text")
    @patch("src.recognition.command_processor.pyautogui.press")
    def test_newline_then_undo_workflow(self, mock_press, mock_inject):
        """Test newline then undo workflow."""
        mock_inject.return_value = True
        cp = CommandProcessor()

        # Insert newline
        newline_result = CommandResult("new line", "insert_newline", 100.0, "new line")
        cp.execute_command(newline_result)
        assert cp.get_history_size() == 1

        # Undo it
        undo_result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(undo_result)

        assert success is True
        assert mock_press.call_count == 1
        assert cp.get_history_size() == 0

    @patch("src.recognition.command_processor.inject_text")
    @patch("src.recognition.command_processor.pyautogui.press")
    def test_complex_workflow_sequence(self, mock_press, mock_inject):
        """Test complex sequence of operations."""
        mock_inject.return_value = True
        cp = CommandProcessor()

        # Dictate
        cp.track_dictation("first line")
        # Insert newline
        newline_result = CommandResult("new line", "insert_newline", 100.0, "new line")
        cp.execute_command(newline_result)
        # Dictate again
        cp.track_dictation("second line")
        # Undo last dictation
        undo_result = CommandResult("undo", "undo", 100.0, "undo")
        cp.execute_command(undo_result)

        # Should have 2 items: first dictation and newline
        assert cp.get_history_size() == 2

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_circular_buffer_with_commands(self, mock_press):
        """Test circular buffer behavior with mixed operations."""
        cp = CommandProcessor(history_size=5)

        # Fill history beyond capacity
        for i in range(7):
            cp.track_dictation(f"text{i}")

        # Should only have last 5
        assert cp.get_history_size() == 5

        # Verify oldest entries were removed
        texts = [entry.data.get("text") for entry in cp._history]
        assert "text0" not in texts
        assert "text1" not in texts
        assert "text6" in texts


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_backspace_exception_handled(self, mock_press):
        """Test pyautogui exceptions are handled gracefully."""
        mock_press.side_effect = Exception("Keyboard error")
        cp = CommandProcessor()
        cp.track_dictation("test")

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        # Should not raise exception
        success = cp.execute_command(result)

        assert success is True  # Command logic succeeded, pyautogui failed

    def test_command_result_with_invalid_data(self):
        """Test execute_command with malformed CommandResult."""
        cp = CommandProcessor()

        # Empty action
        result = CommandResult("test", "", 90.0, "test")
        success = cp.execute_command(result)

        assert success is False

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_delete_with_missing_length_field(self, mock_press):
        """Test delete handles missing length field in history entry."""
        cp = CommandProcessor()
        # Create entry without length field
        entry = HistoryEntry("dictation", {"text": "test"})
        cp._add_to_history(entry)

        result = CommandResult("delete that", "delete_last", 95.0, "delete that")
        success = cp.execute_command(result)

        # Should use length 0 from get("length", 0)
        assert success is True
        mock_press.assert_not_called()

    def test_history_size_with_mixed_operations(self):
        """Test history size is accurate with mixed operations."""
        cp = CommandProcessor()

        cp.track_dictation("text1")
        assert cp.get_history_size() == 1

        cp.track_dictation("text2")
        assert cp.get_history_size() == 2

        cp.clear_history()
        assert cp.get_history_size() == 0

    @patch("src.recognition.command_processor.pyautogui.press")
    def test_undo_dictation_with_very_long_text(self, mock_press):
        """Test undo handles very long text."""
        cp = CommandProcessor()
        long_text = "a" * 10000
        cp.track_dictation(long_text)

        result = CommandResult("undo", "undo", 100.0, "undo")
        success = cp.execute_command(result)

        assert success is True
        assert mock_press.call_count == 10000
