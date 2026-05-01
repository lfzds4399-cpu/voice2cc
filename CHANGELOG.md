# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
