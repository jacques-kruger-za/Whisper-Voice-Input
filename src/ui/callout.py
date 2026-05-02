"""Transcription callout — DEPRECATED, no-op stub.

The callout popup was a placeholder for "streaming text feedback" that
predated the current dictation pipeline. It is being retired in favour
of true real-time streaming directly into the target editor (separate
work track requiring a streaming-capable model).

This stub preserves the public API so app.py callsites can continue to
call set_final_text(), append_segment(), show_at_widget() etc. without
refactor. None of these calls produce any visible UI. The class itself
is kept (rather than deleted) only to avoid a noisy ripple of edits;
once the streaming feature lands, all callsites and this file go.
"""

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class TranscriptionCallout:
    """No-op replacement for the retired callout popup."""

    def __init__(self, parent=None):
        # No Qt widget is created — nothing is ever shown.
        pass

    # All public methods previously used by app.py are no-ops.
    def set_final_text(self, text: str) -> None:
        pass

    def append_segment(self, text: str) -> None:
        pass

    def show_at_widget(self, pos, size) -> None:
        pass

    def show_near_tray(self) -> None:
        pass

    def show_paste_warning(self, text: str) -> None:
        # Failures still surface via the tray notification in app.py;
        # nothing extra to show.
        pass

    def clear(self) -> None:
        pass

    def hide(self) -> None:
        pass
