# Whisper Voice Input - Roadmap

## Current State (v1.0.0)

Core functionality is complete:

| Feature | Status |
|---------|--------|
| Global Hotkey (Ctrl+Alt+F4) | Done |
| Floating Widget with audio-reactive animations | Done |
| System Tray integration | Done |
| Local engine (Faster-Whisper) | Done |
| Cloud engine (OpenAI API) | Done |
| Text cleanup & injection | Done |
| Settings persistence | Done |

**State Machine**: Idle → Recording → Processing → (Success/Error)

---

## Recent Improvements (In Progress)

Code quality improvements from review:

- [x] **Logging infrastructure** - App-wide logging with file/console output
- [x] **Widget size constants** - Fixed label-to-size mismatch
- [x] **Error handling** - Silent audio processing errors now logged
- [x] **Code cleanup** - Removed unused legacy FrequencyBar class
- [x] **Docstrings & type hints** - Improved code documentation

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
| Voice | Custom vocabulary, multi-language switch |
| History | Favorites, export, search |
| App | Auto-update, multiple profiles, cross-platform |

---

## Version Plan

| Version | Focus |
|---------|-------|
| v1.0.0 | **Current** - Core functionality |
| v1.1.0 | MVP polish, error handling, focus management |
| v1.2.0 | Widget animation redesign, transcription history |
| v2.0.0 | Voice commands, advanced productivity |
