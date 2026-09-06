---
project: Whisper-Voice-Input
status: active
last_updated: 2026-09-07
current_focus: "Revived 2026-09-07 after a 3-month gap; streaming preview persistence fixed, docs and repo state refreshed"
next_step: "Issue #1 dock widget + hide-to-bar (largest visible UI gap), then custom-vocab alias replacement"
blockers: none
key_decisions:
  - "2026-05-03: preview-and-finalize streaming (full transcribe at VAD silence) over LocalAgreement word commits; latter lost text"
  - "2026-05-03: dictation and command hotkeys split into separate modalities; shared session caused focus-handle bugs"
  - "2026-05-26: language list locked to English + Afrikaans; only languages in use, stops Whisper weighing others"
  - "2026-05-26: preview panel anchored bottom-right of screen, independent of the widget position"
  - "2026-09-07: streamer carries a generation counter; rounds that started before finalize/stop are discarded"
recent_milestones:
  - "2026-05-03: v1.1.0 — voice commands, vocabulary, visual state redesign, streaming"
  - "2026-05-26: v1.2.0 — language lock, bottom-right upward-growing preview panel"
  - "2026-09-07: autostart registers run.vbs; preview no longer persists after commit"
---

# Whisper-Voice-Input — Project Overview

Living state + history. Captures what this project is made of, what it does, why it's shaped the way it is, and what's been done. Mirrored to vault as `_VaultOperations/projects/Whisper-Voice-Input_Session_Notes.md` (sparse-cloned).

For *future* work, see `ROADMAP.md` (sequenced) and `BACKLOG.md` (raw inbox).

## Stack

- **Language:** Python
- **Framework:** Custom hotkey-triggered tray app; PyInstaller `.spec` for distribution
- **Key libs:** OpenAI Whisper (or whisper.cpp / faster-whisper — see `requirements.txt`), prompt-based custom vocab
- **Runtime / target:** Windows desktop, hotkey-triggered, transcribes into focused window
- **External services:** None (local Whisper)

## Functionality

- Hotkey-triggered voice-to-text input — press hotkey, speak, transcript is typed into the focused window.
- Streaming transcription with preview-and-finalize architecture (snappier stop, no vocab spam in preview).
- Round-text exposure during streaming for INFO-level commit reasoning; threshold-3 commit gate with cross-chunk capitalization.
- Custom vocabulary support via sentence-style `initial_prompt` for stronger bias.
- 1Hz cadence dribble gate to smooth streaming output; bar strip subtracts noise floor so silence renders as silence.
- Restores focus to the original window after transcription completes.

## Architecture & Key Decisions

- **v1.1.0 / streaming polish** — Streaming actually keeps up with separate model + faster decoder + shorter window; preview-and-finalize architecture (S6) avoids re-typing churn.
- **2026-09-07** — Streamer generation counter: a preview round in flight during finalize/stop is dropped and the rolling window is cleared on commit, so committed text is never re-shown.
- **2026-05-26** — Preview panel anchored bottom-right of the primary screen, independent of the widget; earlier widget-relative anchoring moved with the widget and fought the bar strip.
- **2026-05-26** — Language list locked to English + Afrikaans.
- **2026-03-14** — CONTEXT.md added for workstream tracking.
- **2026-03-08** — Bug-fix sweep: hotkey registration, focus restore after transcription, transcription timeout.
- **Streaming dribble gate + 1 Hz cadence** — chosen to keep the user-visible text from flickering while leaving room for late-arriving commits.

## Work Log

- **2026-09-07** — Fix streaming preview persisting after finalize/stop (`690e5f8`); autostart registers `run.vbs` (`e0d3e42`)
- **v1.2.0** — Language list locked to English + Afrikaans (`2779613`); preview panel bottom-right, upward-growing 3 lines (`158bc91`)
- **v1.1.0** — Bump version + roadmap reflects shipped streaming (`781d368`)
- **streaming polish** — Sentence-style `initial_prompt` for stronger custom-vocab bias (`baf7dfb`)
- **streaming polish** — Snappier stop + no vocab spam in preview (`1a2d513`)
- **S6** — Preview-and-finalize architecture for streaming (`bc8845a`)
- **earlier** — Make streaming actually keep up: separate model + faster decoder + shorter window (`c1ec1de`)

## References

- **Repo:** github.com/jacques-kruger-za/Whisper-Voice-Input
- **Prod URL / deployment:** Local PyInstaller `.exe` (`Whisper Voice Input.spec`)
- **Vault status:** `_VaultOperations/projects/Whisper-Voice-Input_Session_Notes.md`
- **Key resource IDs:** _TODO_
- **Related vault notes:** _TODO_
