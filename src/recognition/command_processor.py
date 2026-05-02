"""Voice command execution — thin keystroke dispatcher.

Each command in COMMAND_DEFINITIONS maps a spoken phrase to a single
pyautogui hotkey string (e.g. "ctrl+z"). Execution is stateless: we send
the keystroke to the focused window and let the host editor handle the
semantics. No history, no undo stack, no text tracking.
"""

import pyautogui

from ..config import get_logger
from .commands import CommandResult

logger = get_logger(__name__)


class CommandProcessor:
    """Stateless keystroke dispatcher for voice commands."""

    def __init__(self):
        # Tight inter-key pause; FAILSAFE off so corner-mouse doesn't kill us.
        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = False

    def execute_command(self, command_result: CommandResult) -> bool:
        """Send the command's keystroke to the focused window."""
        keystroke = command_result.keystroke
        if not keystroke:
            logger.warning("Command has no keystroke: %s", command_result.command_phrase)
            return False

        logger.info(
            "Executing command: %s -> %s (confidence=%.0f)",
            command_result.command_phrase, keystroke, command_result.confidence,
        )
        try:
            keys = [k.strip() for k in keystroke.split("+") if k.strip()]
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.exception("Failed to send keystroke '%s': %s", keystroke, e)
            return False
