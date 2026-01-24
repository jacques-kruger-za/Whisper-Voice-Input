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

### Medium Priority

- [ ] **Error messages** - Actionable suggestions for common issues
- [ ] **Hotkey hints** - Display current shortcut in tooltip
- [ ] **Audio device auto-select** - Pick best microphone automatically

---

## Future

| Category | Features |
|----------|----------|
| Voice | Custom vocabulary, voice commands, multi-language switch |
| History | Transcription log, favorites, export |
| App | Auto-update, multiple profiles, cross-platform |

---

## Version Plan

| Version | Focus |
|---------|-------|
| v1.0.0 | **Current** - Core functionality |
| v1.1.0 | MVP polish + logging improvements |
| v2.0.0 | History, voice commands |
