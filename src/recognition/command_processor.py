"""Command execution dispatcher with history tracking."""

from collections import deque
import pyautogui

from ..config.logging_config import get_logger
from ..input.injector import inject_text
from .commands import CommandResult

logger = get_logger(__name__)


class HistoryEntry:
    """Represents a single action in the command history."""

    def __init__(self, entry_type: str, data: dict):
        """
        Create a history entry.

        Args:
            entry_type: Type of entry ("dictation", "newline", "delete", "undo")
            data: Additional data for the entry (e.g., {"text": "hello world"})
        """
        self.type = entry_type
        self.data = data

    def __repr__(self) -> str:
        return f"HistoryEntry(type={self.type!r}, data={self.data!r})"


class CommandProcessor:
    """Process and execute voice commands with history tracking."""

    def __init__(self, history_size: int = 10):
        """
        Initialize command processor.

        Args:
            history_size: Maximum number of actions to keep in history (default: 10)
        """
        logger.debug("Initializing CommandProcessor with history_size=%d", history_size)
        self._history_size = history_size
        # Use deque for efficient circular buffer operations
        self._history: deque[HistoryEntry] = deque(maxlen=history_size)

        # Configure pyautogui for command execution
        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = False

    def execute_command(self, command_result: CommandResult) -> bool:
        """
        Execute a voice command.

        Args:
            command_result: CommandResult from command classification

        Returns:
            True if command executed successfully, False otherwise
        """
        logger.info(
            "Executing command: %s (action=%s, confidence=%.0f)",
            command_result.command_phrase,
            command_result.action,
            command_result.confidence
        )

        action = command_result.action

        if action == "delete_last":
            return self._delete_last()
        elif action == "undo":
            return self._undo()
        elif action == "insert_newline":
            return self._insert_newline()
        else:
            logger.warning("Unknown command action: %s", action)
            return False

    def track_dictation(self, text: str) -> None:
        """
        Track dictated text in history for undo/delete operations.

        Args:
            text: The text that was dictated and injected
        """
        if not text:
            return

        logger.debug("Tracking dictation: %d characters", len(text))
        entry = HistoryEntry("dictation", {"text": text, "length": len(text)})
        self._add_to_history(entry)

    def get_history_size(self) -> int:
        """Get current number of items in history."""
        return len(self._history)

    def clear_history(self) -> None:
        """Clear all history entries."""
        logger.debug("Clearing command history")
        self._history.clear()

    def _add_to_history(self, entry: HistoryEntry) -> None:
        """
        Add entry to history (circular buffer).

        Args:
            entry: HistoryEntry to add
        """
        self._history.append(entry)
        logger.debug(
            "Added to history: %s (history size: %d/%d)",
            entry.type,
            len(self._history),
            self._history_size
        )

    def _delete_last(self) -> bool:
        """
        Delete the last dictated segment.

        Finds the most recent dictation entry in history and removes it
        by simulating backspace keystrokes.

        Returns:
            True if deletion succeeded, False if no dictation found
        """
        logger.debug("Executing delete_last command")

        if not self._history:
            logger.info("Cannot delete: history is empty")
            return False

        # Find last dictation entry (search backwards)
        for i in range(len(self._history) - 1, -1, -1):
            entry = self._history[i]
            if entry.type == "dictation":
                text_length = entry.data.get("length", 0)
                logger.info("Deleting last dictation: %d characters", text_length)

                # Simulate backspace to delete text
                self._delete_text(text_length)

                # Remove from history
                del self._history[i]

                # Track this delete operation
                delete_entry = HistoryEntry("delete", {"deleted_text": entry.data.get("text", ""), "length": text_length})
                self._add_to_history(delete_entry)

                return True

        logger.info("No dictation found in history to delete")
        return False

    def _undo(self) -> bool:
        """
        Undo the last action in history.

        Reverses the most recent action (dictation, newline, or delete).

        Returns:
            True if undo succeeded, False if history is empty
        """
        logger.debug("Executing undo command")

        if not self._history:
            logger.info("Cannot undo: history is empty")
            return False

        # Pop last action from history
        last_entry = self._history.pop()
        logger.info("Undoing last action: %s", last_entry.type)

        if last_entry.type == "dictation":
            # Undo dictation by deleting the text
            text_length = last_entry.data.get("length", 0)
            self._delete_text(text_length)
            logger.debug("Undid dictation: deleted %d characters", text_length)
            return True

        elif last_entry.type == "newline":
            # Undo newline by deleting it
            self._delete_text(1)
            logger.debug("Undid newline")
            return True

        elif last_entry.type == "delete":
            # Undo delete by restoring the text
            deleted_text = last_entry.data.get("deleted_text", "")
            if deleted_text:
                inject_text(deleted_text)
                logger.debug("Undid delete: restored %d characters", len(deleted_text))
                return True
            else:
                logger.warning("Cannot restore deleted text: no text stored")
                return False

        else:
            logger.warning("Cannot undo action type: %s", last_entry.type)
            return False

    def _insert_newline(self) -> bool:
        """
        Insert a newline character at cursor position.

        Returns:
            True if newline inserted successfully
        """
        logger.debug("Executing insert_newline command")

        try:
            # Inject newline character
            success = inject_text("\n")

            if success:
                # Track newline in history for undo
                entry = HistoryEntry("newline", {})
                self._add_to_history(entry)
                logger.debug("Inserted newline")
                return True
            else:
                logger.error("Failed to inject newline")
                return False

        except Exception as e:
            logger.exception("Error inserting newline: %s", e)
            return False

    def _delete_text(self, count: int) -> None:
        """
        Delete text by simulating backspace keystrokes.

        Args:
            count: Number of characters to delete
        """
        if count <= 0:
            return

        logger.debug("Deleting %d characters via backspace", count)

        try:
            for _ in range(count):
                pyautogui.press("backspace")
        except Exception as e:
            logger.exception("Error simulating backspace: %s", e)
