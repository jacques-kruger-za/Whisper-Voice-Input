# Whisper Voice Input - Roadmap

## Current State (v1.0.1) — Stability & Recovery

Bug-fix release focused on eliminating the app-hang / unresponsive state.

### Bug Fixes
- [x] **Hotkey debounce (500ms)** — Prevents key bounce and OS re-fire from spawning multiple callbacks, which caused recording to start and immediately stop
- [x] **Audio stream lifecycle fix** — Leaked `sd.InputStream` objects are now closed before creating new ones; `stop()` always closes the stream even if `_recording` was already False
- [x] **Language detection fix** — `"en"` now forces English explicitly instead of passing `None` to Whisper (which auto-detected Welsh on short audio). Only `"auto"` triggers auto-detection
- [x] **Cancellable error recovery timer** — Replaced `QTimer.singleShot` with `startTimer`/`killTimer` so the error→idle transition doesn't collide with new user input
- [x] **State guards in toggle_recording** — Pressing hotkey during ERROR state cancels the timer and returns to IDLE cleanly; pressing during PROCESSING is explicitly rejected
- [x] **Transcription timeout (120s)** — Prevents indefinite hang if Whisper stalls; shows error and clears `_processing` flag
- [x] **`_processing` flag bulletproofing** — `finally` block in `_process_audio()` ensures flag is always cleared

### New Features
- [x] **Reset State** (tray menu) — Force-clears processing flag, closes leaked audio streams, returns to idle
- [x] **Restart App** (tray menu) — Full process restart via `os.execv`, saves widget position first
- [x] **Afrikaans language support** — Added `"af"` to supported languages
- [x] **Auto-detect language option** — Added `"auto"` for explicit auto-detection (not default)

### Previous (v1.0.0)

Core functionality:

| Feature | Status |
|---------|--------|
| Global Hotkey (Ctrl+Shift+Space) | Done |
| Floating Widget with audio-reactive animations | Done |
| System Tray integration | Done |
| Local engine (Faster-Whisper) | Done |
| Cloud engine (OpenAI API) | Done |
| Text cleanup & injection | Done |
| Settings persistence | Done |
| Logging infrastructure | Done |

**State Machine**: Idle → Recording → Processing → (Success/Error)

---

## MVP Polish (Pending)

### High Priority

- [ ] **First-run onboarding** - Welcome dialog with hotkey instructions
- [ ] **Clipboard preservation** - Save/restore user clipboard during paste
- [ ] **Success feedback** - Visual confirmation after paste
- [ ] **Smart error messages** - Detect and display actionable errors:
  - "Check microphone" when audio is silent/garbled
  - "Model not responding" for transcription timeouts
  - Fade in/out near widget when visible
  - Toast notification (bottom-right) when widget is hidden
- [ ] **Error log in tray menu** - Right-click system tray to view recent errors/logs

### Medium Priority

- [ ] **Hotkey hints** - Display current shortcut in tooltip
- [ ] **Audio device auto-select** - Pick best microphone automatically

---

## Quality & Reliability

- [ ] **Background noise detection** - Warn user when ambient noise may affect transcription
- [ ] **Confidence threshold** - Reject low-quality transcriptions below configurable threshold
- [ ] **Audio quality detection** - Warn about mic permission issues or poor audio levels
- [ ] **Auto-retry on failure** - Retry transcription once automatically before showing error

---

## Recording Controls

- [ ] **Right-click widget to cancel** - While recording, right-click cancels without processing
- [ ] **Cancel option in tray menu** - While recording, right-click tray shows "Cancel Recording" option
- [ ] **Hold-to-record mode** (optional setting):
  - Hold hotkey → recording, release → process
  - Click and hold widget → recording, release → process
  - Quick tap/click (< 500ms) → cancel

---

## Focus & Window Management

- [ ] **Return focus after transcription** - When clicking widget or using hotkey, return focus to the previously active window after transcription completes
- [ ] **Same behavior for tray icon** - Clicking system tray icon should also preserve/restore window focus
- [ ] **"No place to paste" detection** - If no text field is available to receive paste:
  - Show friendly message to user
  - Store transcription in recent history for later use

---

## Transcription History

- [ ] **Recent transcriptions panel** - Store and display last 5 transcriptions
- [ ] **Access from tray menu** - View recent transcriptions via right-click on system tray
- [ ] **Click to copy** - Click any history item to copy to clipboard

---

## Widget Animation Redesign

- [ ] **Inward animations** - All visual effects should animate INSIDE the circle, not outside
- [ ] **Prominent audio level display** - More visible representation of microphone input intensity
- [ ] **Quality visualization** - Animation should reflect both intensity AND quality of audio signal
- [ ] **State-specific animations** - Each state (idle, recording, processing, error) should have distinct inward animations
- [ ] **Hover opacity** - Significantly reduce widget transparency when mouse hovers over it

---

## Future Considerations

| Category | Features |
|----------|----------|
| Voice Commands | Spoken punctuation ("period", "comma"), "delete that", "undo", "new line" |
| Productivity | Custom text snippets triggered by phrase, quick phrases/templates |
| Voice | Custom vocabulary, multi-language switch, configurable language list in settings UI |
| History | Favorites, export, search |
| App | Auto-update, multiple profiles, cross-platform |

---

## Version Plan

| Version | Focus |
|---------|-------|
| v1.0.0 | Core functionality |
| v1.0.1 | **Current** - Stability fixes, recovery mechanisms, language detection |
| v1.1.0 | MVP polish, error handling, focus management, installer |
| v1.2.0 | Widget animation redesign, transcription history |
| v2.0.0 | Voice commands, advanced productivity |
