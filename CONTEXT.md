# Whisper-Voice-Input — Context

## What This Project Is
Whisper-Voice-Input is a Windows desktop dictation app that lets a user speak into any application through a global hotkey or floating widget. It is aimed at users who want a lightweight universal voice-to-text tool with a local-first default, optional cloud transcription, and minimal workflow friction.

## Current State
The app is in a stable post-v1.0.1 state. Core flows are implemented: global hotkey capture, floating widget, system tray controls, local Faster-Whisper transcription, optional OpenAI API transcription, text cleanup, and text injection into the active application. Recent stability work fixed hotkey debounce, audio stream cleanup, language handling, stuck processing states, and transcription timeouts. The main remaining work is polish around onboarding, feedback, error clarity, and clipboard/focus handling.

## Active Workstream
Current work is focused on MVP polish rather than new platform expansion. The highest-value improvements are first-run onboarding, preserving the user's clipboard during paste, clearer success and error feedback, and better focus restoration after transcription. Documentation is also being tightened so setup steps and hotkey behavior stay consistent with the shipped app.

## Key Decisions
- Windows is the primary target platform for the current product shape.
- Local Faster-Whisper is the default engine, with OpenAI Whisper API as an optional cloud fallback.
- Python 3.12 is the supported runtime because key dependencies do not yet have reliable wheels for newer Python versions.
- The app uses a global hotkey plus a small floating widget instead of a full main window as the primary interaction model.
- Stability and recovery are prioritized over adding broad new feature scope.

## Next Steps
1. Add first-run onboarding with clear hotkey guidance.
2. Preserve and restore clipboard contents during paste injection.
3. Improve success and error feedback around recording and transcription.
4. Restore focus more reliably to the previously active window after transcription.
5. Add lightweight visibility into recent errors and recent transcriptions from the tray.

## Reference Material
- `README.md` for setup, runtime requirements, and user-facing behavior.
- `ROADMAP.md` for current priorities and deferred ideas.
- `prompts/001-voice-input-desktop-app.md` for original product framing.
- `prompts/002-redesign-floating-widget.md` and `prompts/003-widget-visual-refinements.md` for widget UX direction.
- `tests/verify_widget_sizes.py` for widget sizing validation.
