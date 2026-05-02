# Whisper Voice Input - Roadmap

## Shipped since v1.0.1

The work below was largely informed by GitHub issues #1–#6 and a series of dictation sessions that surfaced real-world friction. Significant chunks of what was originally pencilled in for v2.0.0 (voice commands, custom vocabulary) landed earlier than planned.

### Voice control & vocabulary (issues #2, #4 partial)

- [x] **Custom vocabulary** — words/names/jargon passed to Whisper as `initial_prompt` to bias transcription. Editable list in settings; active whenever non-empty.
- [x] **Spoken punctuation** — words like "comma", "period", "full stop", "new line", "new paragraph", "question mark", etc. are substituted into the text during cleanup. Works mid-utterance.
- [x] **Editor commands with wake-word prefix** — saying `"command save"` fires Ctrl+S, `"command undo"` fires Ctrl+Z, etc. Wake word eliminates false positives. Default catalog: undo / redo / save / select all / copy / paste / cut / find. Master toggle in settings.
- [x] **User-extensible** — add custom punctuation phrases (`open paren` → `(`) and custom commands (`build` → `ctrl+shift+b`) directly in settings; persisted in JSON.
- [x] **Settings tab restructured** — three explicit sections: **Custom Vocabulary** | **Text Editing Vocabulary** | **Editor Commands**, each with Add/Remove buttons.

### Visual state redesign (issue #2)

- [x] **Rolling 5-second volume strip** — extends 2× widget width to the left of the circle. Bars scroll right→left, fade out toward the left edge. Bar amplitude shaped via sqrt curve so normal speech reaches 50–70% of max height.
- [x] **Whole-circle yellow pulse** during processing (replaces the breathing-scale animation).
- [x] **Consistent state-coloured mic icon** — grey/blue/orange/red for idle/recording/processing/error, shown in every state.
- [x] **Retired pulse rings, vertical mic-overlay bars, breathing scale** — superseded by the bar strip + dot/pulse model.

### Architecture & bug fixes

- [x] **Callout popup retired** (issue #3) — was a placeholder for streaming feedback that didn't stream. Replaced by the bar strip; streaming will inject directly into the editor.
- [x] **Self-focus bug fixed** — hotkey path no longer captures our own widget's HWND when it's the foreground window. Falls back to the polled external HWND tracker.
- [x] **Position-clamp on restore** — wider bar-strip layout no longer leaves the widget off-screen on launch.
- [x] **Whisper model upgraded** — default switched to `small` (vs `tiny`); meaningfully better proper-noun accuracy and fewer hallucinations.

---

## In Progress — Real-time Streaming (issue #4)

Replaces the record-then-transcribe-batch lifecycle with continuous transcription. Architecture sketched in 4 phases, the first two of which are on `feat/streaming-s1`:

- [x] **S1 · Sliding-window substrate** — `StreamingTranscriber` class with rolling 12-second buffer, worker thread that calls `transcribe_array()` on a numpy buffer every ~1 second. VAD min-silence reduced to 500ms so segment boundaries fire on natural pauses.
- [x] **S2 · LocalAgreement-K commit logic** — word-level hold-back algorithm. A word commits only after appearing in 2 consecutive rounds at the same logical position. Two callbacks: `on_committed(text)` for stable output, `on_tentative(text)` for the still-flickering tail. 1.5-second buffer minimum prevents short-clip hallucinations from being committed.
- [ ] **S3 · App integration** — recorder fires audio chunks live (not just on stop); app routes committed segments through cleanup → command-classify → inject. Wake-word commands fire when a *segment* (not full utterance) starts with the wake word. Single `STREAMING` state replaces RECORDING/PROCESSING split.
- [ ] **S4 · Stability** — mid-stream focus loss (pause-and-resume injection), hotkey-during-stream = stop, transcription error mid-stream doesn't crash, final flush of pending tentative on stop.

S3 will sit behind a `streaming_mode` settings flag during testing so batch mode remains the fallback.

---

## Pending Issues

### Issue #1 — Dock widget + hide-to-bar

Dock widget to right edge, slide vertical only. Hide collapses to a thin strip; hover restores. Requires shape change from circle to rectangle. *Touches the widget bounding rect we restructured for #2 — natural follow-up after streaming integration lands.*

### Issue #5 — Clipboard history in tray

Right-click tray → list of recent dictations. Each "snippet" = the text produced between one start-recording and stop-recording. Copy / delete / clear all. *Self-contained, doesn't touch transcription.*

### Issue #6 — Modern settings UI

Windows-2026 styling, light/dark system theme adaptation. *We just refactored settings for the voice-command sections — defer until streaming UI work settles to avoid double-touching the same files.*

---

## Quality & Polish (from earlier roadmap, still relevant)

### High Priority

- [ ] **First-run onboarding** — welcome dialog with hotkey + setup instructions
- [ ] **Clipboard preservation** — save/restore user clipboard around paste
- [ ] **Success feedback** — visual confirmation after paste lands
- [ ] **Smart error messages** — "check microphone" when audio is silent, "model not responding" for transcription timeouts, etc. Fade in near widget when visible; toast (bottom-right) when widget is hidden.
- [ ] **Error log in tray menu** — quick access to recent errors/logs without opening the file system

### Medium Priority

- [ ] **Hotkey hints** — current shortcut shown in tooltip
- [ ] **Audio device auto-select** — best microphone picked automatically
- [ ] **Background noise detection** — warn when ambient noise may degrade transcription
- [ ] **Confidence threshold** — reject low-confidence rounds below configurable cutoff
- [ ] **Auto-retry on failure** — one silent retry before surfacing the error

### Recording Controls

- [ ] **Right-click widget = cancel recording** (no processing)
- [ ] **Cancel from tray** while recording
- [ ] **Hold-to-record mode** as optional alternative to toggle

---

## Distribution

- [x] **Single-file portable EXE** via PyInstaller (`dist/Whisper Voice Input.exe`, ~157 MB)
- [ ] **Windows installer** — Inno Setup or NSIS wrapper with Start Menu entry, uninstaller, version metadata
- [ ] **Auto-update** — check GitHub releases, download + replace
- [ ] **Code signing** — eliminate SmartScreen warnings on first launch

---

## Future Considerations

| Category | Features |
| -------- | -------- |
| Voice control | ~~Spoken punctuation, voice commands, custom vocabulary~~ ✅ shipped. Remaining: spoken text-formatting commands ("bold this", "select last sentence"), voice-driven snippet expansion |
| Productivity | Custom text snippets triggered by phrase, quick phrases / templates, per-app shortcut profiles |
| Voice | ~~Custom vocabulary~~ ✅. Multi-language hot-switch, per-app language overrides, language auto-detect quality improvement |
| History | Favorites, export, search across past dictations |
| App | Auto-update, multiple user profiles, cross-platform (macOS/Linux) |

---

## Version Plan

| Version | Status | Focus |
| ------- | ------ | ----- |
| v1.0.0 | Shipped | Core functionality |
| v1.0.1 | Shipped | Stability fixes, recovery mechanisms, language detection |
| v1.1.0 | **In progress** | Voice commands & vocabulary, visual state redesign, real-time streaming (S1–S4) |
| v1.2.0 | Planned | Issue #1 (dock + hide-to-bar), Issue #5 (clipboard history), MVP polish (onboarding, smart errors) |
| v1.3.0 | Planned | Modern settings UI (issue #6), windows installer, auto-update |
| v2.0.0 | Aspirational | Per-app shortcut profiles, snippet expansion, cross-platform |
