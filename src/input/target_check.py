"""Is there somewhere to paste? UI Automation look at the focused control.

Three answers, and the caller must treat them differently:
- True:  an editable text control has keyboard focus — paste.
- False: focus is clearly on something that cannot take text (button,
         menu item, image, static text…) — keep the text on the clipboard
         and tell the user instead of pasting into nothing.
- None:  unknown (no UIA exposure, our own window, any error) — paste
         anyway; Flutter apps, games and remote desktops land here.

Call it while the TARGET is still the foreground window, i.e. at session
start, not after our own widget has been clicked.
"""

from __future__ import annotations

import os

from ..config.logging_config import get_logger

logger = get_logger(__name__)


def focused_control_is_editable() -> bool | None:
    try:
        import uiautomation as auto  # lazy: COM init + typelib on first use

        control = auto.GetFocusedControl()
        if control is None:
            return None
        if control.ProcessId == os.getpid():
            return None  # our own window has focus — says nothing about the target

        ct = control.ControlType
        name = control.ControlTypeName
        if ct in (auto.ControlType.EditControl, auto.ControlType.DocumentControl):
            value_pattern = control.GetValuePattern()
            if value_pattern is not None and value_pattern.IsReadOnly:
                logger.info("Target check: %s is read-only", name)
                return False
            logger.info("Target check: %s is editable", name)
            return True

        not_text = (
            auto.ControlType.ButtonControl, auto.ControlType.CheckBoxControl,
            auto.ControlType.RadioButtonControl, auto.ControlType.MenuItemControl,
            auto.ControlType.MenuControl, auto.ControlType.HyperlinkControl,
            auto.ControlType.ImageControl, auto.ControlType.ListItemControl,
            auto.ControlType.TreeItemControl, auto.ControlType.TabItemControl,
            auto.ControlType.TextControl, auto.ControlType.SliderControl,
            auto.ControlType.ProgressBarControl, auto.ControlType.ScrollBarControl,
            auto.ControlType.HeaderItemControl, auto.ControlType.SplitButtonControl,
        )
        if ct in not_text:
            logger.info("Target check: %s cannot take text", name)
            return False
        logger.info("Target check: %s — unknown, will paste", name)
        return None
    except Exception as e:  # ponytail: any UIA hiccup means "don't know"
        logger.debug("Target check unavailable: %s", e)
        return None
