# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.2] — 2026-05-06

Polish & discoverability release. No code behaviour changes — just CI/CD,
docs, and GitHub setup so others can find / contribute / build.

### Added
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — runs pytest on Windows
  for Python 3.10 / 3.11 / 3.12 plus ruff lint on every push & PR.
- **GitHub Actions Release** (`.github/workflows/release.yml`) — on every
  `v*.*.*` tag push, builds the Windows .exe via PyInstaller and attaches the
  `voice2cc-vX.Y.Z-windows.zip` artefact to the matching GitHub Release.
- **`docs/`** — `getting-started.md`, `faq.md`, `troubleshooting.md`.
- **3 pinned "help wanted" issues** — macOS port, Linux port, silero-vad
  upgrade. Each has scope, suggested approach, and merge criteria.
- **README hero rewrite** — front-line ASCII demo, problem statement, "what
  works today" matrix, "verified live" section.
- **20 GitHub topics** + improved repo description for SEO discoverability.

### Removed
- `.github/workflows/lint.yml` referenced the old single-file `voice2cc.py`
  and pushed to a non-existent `main` branch — replaced by the new `ci.yml`.

## [0.4.1] — 2026-05-06

Same-day follow-up to 0.4.0, focused on real-world VAD usability and "paste
into the wrong window" failures discovered while dogfooding hands-free mode
for an hour.

### Added
- **VAD hysteresis** — separate `threshold` (enter speech) and `silence_floor =
  threshold × silence_ratio` (exit speech). Default ratio 0.4 means a
  mid-sentence breath at RMS=0.010 keeps the utterance alive even though the
  speech-enter threshold is 0.015. Stops "every breath ends my sentence."
- **ZCR (zero-crossing-rate) gate** in EnergyVAD — filters broadband noise
  (breath into mic, fan, AC, paper rustle) which has high RMS but ZCR > 0.20.
  Voiced speech sits at ZCR 0.05–0.15 and passes. Configurable via
  `VOICE2CC_VAD_MAX_ZCR` (default 0.18; set 1.0 to disable).
- **WS_EX_NOACTIVATE on the floating widget** — Windows now refuses to give
  the widget focus, so when the user clicks another Claude Code / VS Code /
  Edge window, that click really takes effect and voice2cc captures the
  correct foreground HWND on speech_start.
- **WS_EX_TOOLWINDOW on the floating widget** — keeps it out of the Alt+Tab
  list (it's an overlay, not an app).
- **Foreground-window fallback** in paste — if `SetForegroundWindow` returns
  False for the captured HWND (window closed / foreground-lock denied), fall
  back to whatever has focus right now instead of pasting into a dead HWND.
- 3 new VAD tests for ZCR-gate behaviour. Total: 45 → **48 tests** passing.

### Fixed
- "voice2cc records forever and never paste-submits": breath at RMS just below
  enter-threshold accumulated `silence_ms` and incorrectly triggered
  speech_end. Hysteresis fixes this end of the failure mode.
- "every exhale fires recording": ZCR gate rejects the high-frequency content
  of breath / fan noise even when its energy clears the RMS bar.
- "paste lands in the wrong window when I have multiple Claude Code tabs
  open": floating widget was occasionally winning focus during state-change
  UI updates; NOACTIVATE prevents this entirely.
- "paste into a window that closed during transcribe" → paste no-op'd.
  Fallback to live foreground HWND fixes this.

### Verified live (real WeChat / multi-window test, 2026-05-06)
- Continuous mode + breath/换气 mid-sentence → utterance stays alive,
  paste fires only on real 1.2s pause.
- Click another VS Code window → speech → text lands there.
- Click WeChat input box → speech → text lands in WeChat.

## [0.4.0] — 2026-05-06

**The "zero-touch" release.** Hands-free dictation via VAD, smart-paste detection
across 10+ apps, auto-Enter to submit. Verified live: from "press F9" → speak →
text appears in your AI chat already submitted, no keyboard.

### Added
- **Continuous mode (Voice Activity Detection)** — press the toggle hotkey
  (default **F9**) once and voice2cc listens hands-free: speech start/end is
  detected from RMS energy with hysteresis (`min_speech_ms`, `min_silence_ms`),
  each utterance is auto-paste + auto-Enter. Press F9 again to stop.
  - 7 unit tests covering the state machine.
  - Tunable via `VOICE2CC_VAD_THRESHOLD`, `VOICE2CC_VAD_MIN_SPEECH_MS`, `VOICE2CC_VAD_MIN_SILENCE_MS`.
- **Smart paste** — auto-detects the foreground app and chooses Ctrl+V vs
  Ctrl+Shift+V. Currently:
  - Ctrl+Shift+V: VS Code, Cursor, Windsurf, Trae, Windows Terminal,
    Windows PowerShell ISE, mintty (Git Bash), PuTTY, gVim.
  - Ctrl+V (forced, never Ctrl+Shift+V): Chrome / Edge / Firefox / Notepad /
    classic conhost (cmd / classic PowerShell window) — these would otherwise
    open incognito-paste / dev-paste on Ctrl+Shift+V.
- **Auto-Enter after paste** — sends Enter ~100ms after the paste keystroke so
  AI chat submissions are zero-touch end-to-end. Toggleable
  (`VOICE2CC_AUTO_ENTER_AFTER_PASTE`).
- **Win32 keybd_event paste backend** replaces pynput on Windows — significantly
  more reliable in apps that filter synthetic keystrokes (Electron sandbox,
  some game-launcher overlays).
- **Foreground-window restore** — captures the HWND at hotkey-down (or VAD
  speech_start), then `SetForegroundWindow` + 50ms settle before paste. Uses
  the AutoHotKey `AttachThreadInput` workaround for Windows' foreground-lock
  rules. Only restores `ShowWindow(SW_RESTORE)` if the target was actually
  minimised (`IsIconic`) — fixes a bug where maximised windows were
  un-maximised on every paste.

### Changed
- `paste.py` rewritten end-to-end. Public API additions:
  `paste_to_focus(text, target_hwnd=0, auto_enter=False, smart_paste=True)`,
  `get_foreground_window()`, `needs_ctrl_shift_v(hwnd=0)`.
- `audio.py` exposes `set_frame_listener(fn)` so VAD (or future modules) can
  observe every audio chunk without owning the mic stream.
- `hotkey.py` adds `ToggleHotkeyListener` for press-once toggle behaviour
  (existing `HotkeyListener` is unchanged for push-to-talk).
- 38 → **45 unit tests**, all passing offline.

### Fixed
- VS Code / Windows Terminal pastes that previously needed manual Ctrl+Shift+V.
- "Pasted into the wrong window" — fixed with hwnd capture + restore.
- "Paste un-maximises my window" (regression in 0.4.0-pre) — guarded with
  `IsIconic` so SW_RESTORE only fires for genuinely minimised targets.

### Known limitations
- VAD is RMS-energy based (no webrtcvad/silero-vad yet). Works well in quiet
  desktop environments; for noisy environments increase `VAD_THRESHOLD` to
  ~0.025–0.03. webrtcvad/silero-vad upgrade path is wired in `vad.py` for v0.5.
- Floating-widget status text in continuous mode still says "release F8 to
  stop" (legacy push-to-talk wording) — cosmetic, fix queued for v0.4.1.

## [0.3.0] — 2026-05-04

Full rewrite from a 460-line single file into a tested package, with multiple
providers, a tray icon, configuration GUI, bilingual UI, and a `.exe` build path.

### Added
- **Multi-provider STT** — SiliconFlow / OpenAI / Groq / Azure, all OpenAI-compatible HTTP.
- **First-run setup wizard** — pick provider, paste key, test, save (no Notepad-editing).
- **Settings dialog** (tray → Settings) — provider, mic device picker with test-record, hotkey
  recorder + presets, language, autostart, audio cues, paste-vs-copy mode.
- **System tray icon** (pystray) — show/hide widget, open settings, run diagnostics, open log,
  quit. Falls back to no-tray if pystray fails to install.
- **Bilingual UI** — English / 中文 with system-locale auto-detection.
- **Built-in diagnostics** — dependencies / mic / network / provider reachability / API health,
  rendered in a single window (tray → Diagnose…).
- **Pre-roll audio buffer** (300ms ring buffer always running) — captures the first syllable
  that v0.2 routinely lost.
- **Modifier-safe paste** — explicitly releases Ctrl/Shift/Alt/Cmd before sending Ctrl+V,
  fixing the v0.2 bug where some apps interpreted the paste as Ctrl+Shift+V.
- **Windows autostart** option (HKCU\\Run, no admin required).
- **PyInstaller build pipeline** — `build_tools/voice2cc.spec` + `build_tools/build.bat`,
  produces `dist/voice2cc/voice2cc.exe` (folder mode for faster startup + fewer AV alarms).
- **Rotating log file** — `voice2cc.log` (max ~1.5 MB total). Includes API latency and errors.
- **38 unit tests** — config roundtrip & legacy migration, hotkey parser, providers (HTTP
  mocked), i18n, diagnostics, paste, pre-roll buffer behavior. No GUI/network needed.
- **`python -m voice2cc`** entry point in addition to `python app.py`.

### Changed
- Refactored from `voice2cc.py` (460 LoC, single file) into `src/voice2cc/` (≈1.8k LoC,
  21 modules with clear seams).
- Renamed shim from `voice2cc.py` → `app.py` to avoid colliding with the `voice2cc` package
  name during pytest collection. `start.bat` updated.
- Default `pythonw app.py` (instead of `python`) so non-developers don't see a console window.
- `config.env` now supports `VOICE2CC_PROVIDER`, `VOICE2CC_HOTKEY`, `VOICE2CC_LANGUAGE`,
  `VOICE2CC_AUTOSTART`, `VOICE2CC_INPUT_DEVICE`, `VOICE2CC_SHOW_WIDGET`,
  `VOICE2CC_PLAY_CUES`, `VOICE2CC_PASTE_AFTER`, plus all four `*_API_KEY` keys.
  Old `SILICONFLOW_API_KEY` + `STT_MODEL` keys still work — `provider` is inferred.

### Fixed
- Pasting into VS Code / Cursor / browsers no longer occasionally opens the command palette
  or incognito window because the paste was interpreted as Ctrl+Shift+V.
- The first syllable of recordings is no longer clipped on the hotkey edge.
- Tracebacks and provider errors now hit `voice2cc.log` so users can attach it to issues.

## [0.1.0] — 2026-05-01

Initial public release.

### Added
- Push-to-talk hotkey (default `Ctrl+Shift+Space`) — hold, speak, release, paste
- Floating always-on-top widget with state colours: idle / recording / transcribing / pasted / error
- Real-time mic level meter (also shown at idle so you can verify the mic works)
- Audio cues at start, end, and successful paste
- Startup self-test that pings the STT endpoint to verify key + model + network
- SiliconFlow `SenseVoiceSmall` STT backend by default; pluggable via `config.env`
- Auto Ctrl+V into focused field
- 0.3s minimum recording length to ignore accidental key bumps
