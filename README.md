# voice2ai

Windows push-to-talk dictation. Hold a hotkey, speak, release — the transcript
is pasted into the focused window.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

[Chinese README](./README.zh-CN.md) | [Releases](https://github.com/lfzds4399-cpu/voice2ai/releases/latest)

![voice2ai demo](./docs/voice2ai-demo.gif)

Windows-only. The paste backend calls Win32 keyboard APIs directly; the
provider, config, audio, and VAD layers are platform-neutral. macOS and Linux
paste backends are not implemented.

## Install

Python 3.10+.

```powershell
git clone https://github.com/lfzds4399-cpu/voice2ai.git
cd voice2ai
python -m pip install -r requirements.txt
python app.py
```

First run opens a setup wizard: pick a provider, paste an API key, test, save.
Alternatively, run `install.bat` then `start.bat`. A PyInstaller spec in
`build_tools/` produces a frozen `.exe`; the binary is unsigned, so SmartScreen
will warn on first launch.

## Hotkeys and modes

Default hotkey: `ctrl+shift+space`. Built-in presets: `f8`, `f9`, `right ctrl`,
`ctrl+alt+v`. Press `f9` to toggle continuous mode, which uses EnergyVAD to
detect pauses and transcribe the preceding utterance.

On hotkey press, voice2ai snapshots the foreground HWND and restores it before
the paste fires, preventing text from landing in the wrong application after a
mid-utterance focus change. Known terminals and editors receive
`ctrl+shift+v`; other windows receive `ctrl+v`.

## Providers

| Provider | Model | Notes |
|---|---|---|
| SiliconFlow | `FunAudioLLM/SenseVoiceSmall` | Mandarin-capable, reachable from mainland China. |
| OpenAI | `whisper-1`, `gpt-4o-mini-transcribe` | Paid API, global. |
| Groq | `whisper-large-v3-turbo` | Whisper-compatible endpoint, low latency. |
| Azure | `whisper` deployment | Requires an Azure OpenAI resource. |

`config.env` accepts the canonical keys and the provider aliases listed in
`.env.example` (`GROQ_MODEL`, `OPENAI_MODEL`, `SILICONFLOW_MODEL`,
`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`).

## Modifier handling

voice2ai does not simulate keystrokes. It copies the transcript to the
clipboard, releases held modifier keys, waits a few milliseconds, restores the
target window if possible, then sends the paste shortcut.

If `shift` remains physically held when paste fires, Windows interprets
`ctrl+v` as `ctrl+shift+v`, which some terminals intercept and discard. The
modifier-release path is covered by `tests/test_paste.py`.

## Project layout

```text
app.py                  entry-point shim
src/voice2ai/
  main.py               app orchestration
  config.py             settings load/save
  audio.py              microphone capture and pre-roll
  hotkey.py             global hotkey listeners
  paste.py              Win32 clipboard paste backend
  vad.py                continuous-mode VAD
  diagnostics.py        dependency / mic / network / provider checks
  providers/, ui/       STT providers and Tk UI components
tests/                  offline unit tests
build_tools/            PyInstaller spec
```

## Development

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest ruff
python -m pytest tests/ -q
python -m ruff check src tests app.py
```

Tests run offline. Provider APIs, real keyboard input, and GUI automation are
not exercised.

## Privacy

Audio is sent only to the configured STT provider. No telemetry, analytics,
auto-update, or listening sockets. API keys are stored in `config.env`, which
is gitignored. Security reports: [SECURITY.md](./SECURITY.md).

## License

MIT. See [LICENSE](./LICENSE).
