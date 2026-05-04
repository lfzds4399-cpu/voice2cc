# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
