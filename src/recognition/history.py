"""Dictation history — every finalized chunk of every session, so a paste
that lands nowhere is recoverable instead of lost.

A session is one start→stop of dictation (streaming or batch). Chunks are
appended as they are finalized; the session is persisted as one JSONL line
when it ends. The current session's text is available while it is open, so
"paste last dictation" mid-session gives everything so far.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config.logging_config import get_logger

logger = get_logger(__name__)

HISTORY_FILE_NAME = "history.jsonl"
HISTORY_MAX_SESSIONS = 50          # kept on disk and in memory


class DictationHistory:
    def __init__(self, data_dir: Path, max_sessions: int = HISTORY_MAX_SESSIONS) -> None:
        self._path = Path(data_dir) / HISTORY_FILE_NAME
        self._max = max_sessions
        self._sessions: list[tuple[float, str]] = []   # (epoch seconds, text), oldest first
        self._current: list[str] | None = None
        self._load()

    # ── Session lifecycle ─────────────────────────────────────────────────

    def begin(self) -> None:
        """Start a new session; an unfinished one is closed first."""
        if self._current:
            self.end()
        self._current = []

    def append(self, text: str) -> None:
        """Record a finalized chunk of the current session."""
        text = (text or "").strip()
        if not text:
            return
        if self._current is None:
            self._current = []
        self._current.append(text)

    def end(self) -> str | None:
        """Close the session, persist it if it produced text. Returns the text."""
        chunks, self._current = self._current, None
        if not chunks:
            return None
        text = " ".join(chunks)
        self._sessions.append((time.time(), text))
        del self._sessions[:-self._max]
        self._save()
        return text

    # ── Queries ───────────────────────────────────────────────────────────

    @property
    def last_text(self) -> str | None:
        """Current session so far, else the most recent finished session."""
        if self._current:
            return " ".join(self._current)
        return self._sessions[-1][1] if self._sessions else None

    def recent(self, n: int = 10) -> list[tuple[float, str]]:
        """Most recent finished sessions, newest first."""
        return list(reversed(self._sessions[-n:]))

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if not self._path.exists():
                return
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    self._sessions.append((float(row["ts"]), str(row["text"])))
            del self._sessions[:-self._max]
        except Exception as e:
            logger.warning("Could not load dictation history: %s", e)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                for ts, text in self._sessions:
                    f.write(json.dumps({"ts": ts, "text": text}, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Could not save dictation history: %s", e)
