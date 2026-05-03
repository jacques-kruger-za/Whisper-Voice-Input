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

## Real-time Streaming (issue #4) — Shipped

What ended up in the box was different from the original plan. The first attempt (S1+S2 LocalAgreement K=2 word-prefix commits) had structural reliability problems — text getting lost when round outputs disagreed, dribble fragments when thresholds were tuned the other way. After a real session showed 25–30 words of speech producing zero commits, the architecture got rebuilt around **preview-and-finalize** instead of incremental commits.

### Final architecture

- [x] **Rolling-window preview pipeline** — worker thread runs `transcribe_array()` on the last 8 seconds every ~1 second. Output goes to a translucent floating preview panel (no editor injection). Updates per round, may flicker as the model revises with more context. No `initial_prompt` here (avoids the "Jeanré, Jeanré, Jeanré..." vocab-spam hallucination).
- [x] **Utterance-finalize commit** — when VAD detects ≥1.0s of silence after speech, a fresh full-context `transcribe()` runs on the entire audio captured since the last finalize. That clean text goes through `cleanup_text` and lands in the focused editor as one block. Reliability matches batch mode because each commit is a full transcribe pass, not an aggregation of round outputs.
- [x] **Async stop-finalize** — pressing the hotkey to stop flips state to PROCESSING immediately; finalize runs on a background thread; result lands via Qt signal. No more 3-second frozen widget on stop.
- [x] **Streaming-specific tuning** — separate `streaming_model` setting (default `base`), reduced `beam_size`/`best_of`, separate window length and finalize thresholds. Tuning surface lives in `constants.py`.
- [x] **VAD-driven session lifecycle** — `SilenceMonitor` audio-thread → UI poll. Auto-pause Whisper rounds at 2s silence; auto-stop session at 60s; finalize commit at 1.0s post-speech silence. Single-press command capture also driven by VAD (1.5s post-speech fires the keystroke; 8s no-speech cancels).
- [x] **Live preview UI** — translucent panel anchored left of widget. Right-aligned text (newest near widget), elided on the left under an alpha-gradient fade so older words appear to roll off. Frameless, click-through. Fades on commit.

### Collapsed / removed during the rebuild

- LocalAgreement-K word-prefix commit logic (~150 lines)
- `MIN_COMMIT_WORDS` gate, `RELAX_AFTER_SECONDS` stuck-stream timeout
- The `_streaming_committed` / `_streaming_tentative` signal pair (replaced by `_streaming_preview` + `_streaming_finalized`)
- `CommitTracker` class

### Sub-modality split: dictation vs commands

Earlier S3 prototype had commands and dictation sharing a session via wake-word prefix on every preview round. This created bugs (`_saved_hwnd` consumed by command firing, subsequent dictation discarded). Final design separates them entirely:

- [x] **Dictation hotkey** (`Ctrl+Shift+Space`): pure streaming/batch, no command classification per round
- [x] **Command hotkey** (`Ctrl+Shift+C`): single-shot batch capture, fires keystroke on VAD-detected end-of-utterance. Hotkey is the wake — no spoken `"command"` prefix needed when triggered this way (`require_wake_word=False` in classify_transcription)

---

## Pending Issues

### Issue #1 — Dock widget + hide-to-bar

Dock widget to right edge, slide vertical only. Hide collapses to a thin strip; hover restores. Requires shape change from circle to rectangle. **The largest user-visible gap remaining** — repeatedly hit during the streaming work because the bar-strip layout and now the preview panel both anchor relative to the widget. Docking would make those anchors stable.

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

## Known Limitations (worth fixing soon)

- **Custom vocabulary is weak for words with English homophones.** "Jeanré" is consistently transcribed as "Jean Ray" / "John Ray" because the prompt-bias mechanism can't override Whisper's training distribution. Sentence-style prompt format ("Vocabulary: foo, bar.") ships now — marginal win, doesn't solve the homophone case.
  - **Reliable answer**: alias-replacement post-processing. Each vocab entry gets a list of common mishearings; cleanup substitutes them with the canonical form. No model bias involved, deterministic. Needs UI for adding aliases (per-word inline prompt simplest).
- **Sound Recorder app crashes when this app is running.** Likely WASAPI device contention / stream-leak. Workaround: quit from tray before using Sound Recorder. Not yet investigated.
- **Saved-but-disconnected device produces a warning every session.** Falls back to system default but logs `Configured device 'X' failed`. Should suppress after first attempt or surface a one-time "device not connected" notification.

## Future Considerations

| Category | Features |
| -------- | -------- |
| Voice control | ~~Spoken punctuation, voice commands, custom vocabulary~~ ✅ shipped. Remaining: spoken text-formatting commands ("bold this", "select last sentence"), voice-driven snippet expansion |
| Vocab accuracy | Per-word alias map (canonical → mishearings); auto-detect aliases by comparing user's speech against transcribed output |
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
| v1.1.0 | **Ready to ship** | Voice commands & vocabulary (issue #2), visual state redesign (issue #2), preview-and-finalize streaming (issue #4), separate command hotkey, retired callout (issue #3), VAD lifecycle |
| v1.2.0 | Next | Issue #1 (dock + hide-to-bar), custom-vocab alias replacement, MVP polish (onboarding, smart errors) |
| v1.3.0 | Planned | Issue #5 (clipboard history), modern settings UI (issue #6), windows installer, auto-update |
| v2.0.0 | Aspirational | Per-app shortcut profiles, snippet expansion, cross-platform |
