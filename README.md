# voice2ai

Windows push-to-talk dictation. Hold a hotkey, talk, release, the transcript
gets pasted into whatever window had focus. I use it to dictate into VS Code,
Cursor, Claude Code, and WeChat.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

[Chinese README](./README.zh-CN.md) | [Releases](https://github.com/lfzds4399-cpu/voice2ai/releases/latest)

![voice2ai demo](./docs/voice2ai-demo.gif)

Windows-only for now. The paste backend calls Win32 keyboard APIs directly.
Most of the provider / config / audio / VAD code is platform-neutral, but
nobody has wired up a macOS or Linux paste backend yet.

## Install

Python 3.10+.

```powershell
git clone https://github.com/lfzds4399-cpu/voice2ai.git
cd voice2ai
python -m pip install -r requirements.txt
python app.py
```

First run opens a setup wizard. Pick a provider, paste your API key, hit test,
save. You can also double-click `install.bat` then `start.bat`.

There's a PyInstaller spec in `build_tools/` if you want a frozen `.exe`, but
the binary is unsigned so SmartScreen will complain on first launch.

## Hotkeys and modes

Default hotkey is `ctrl+shift+space`. Other built-in presets are `f8`, `f9`,
`right ctrl`, and `ctrl+alt+v`. Press `f9` to flip into continuous mode, which
uses EnergyVAD to wait for a pause and then transcribes whatever you just said.

When you start talking, voice2ai grabs the foreground window handle. When the
transcript comes back it restores that window before pasting, so switching tabs
mid-sentence doesn't send your text to the wrong app. Known terminals and
editors get `ctrl+shift+v`, everything else gets `ctrl+v`.

## Providers

| Provider | Model I use | Notes |
|---|---|---|
| SiliconFlow | `FunAudioLLM/SenseVoiceSmall` | Decent Mandarin, reachable from mainland China. |
| OpenAI | `whisper-1` or `gpt-4o-mini-transcribe` | Paid API, global. |
| Groq | `whisper-large-v3-turbo` | Fast Whisper-compatible endpoint. |
| Azure | `whisper` deployment | Needs an Azure OpenAI resource. |

`config.env` accepts both the main key names and the provider aliases listed
in `.env.example` (`GROQ_MODEL`, `OPENAI_MODEL`, `SILICONFLOW_MODEL`,
`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`).

## The paste detail that took longest to get right

voice2ai doesn't simulate typing. It copies the transcript to the clipboard,
releases any stuck modifier keys, waits a few milliseconds, restores the target
window if it can, then sends the paste shortcut.

The reason is dumb but real: if you hold `ctrl+shift+space` to talk and `shift`
is still physically down when the paste fires, Windows reads `ctrl+shift+v`
instead of `ctrl+v` and your terminal eats the paste. The modifier-release path
is what `tests/test_paste.py` covers.

## Project layout

```text
voice2ai/
  app.py                       entry-point shim
  start.bat / install.bat      Windows helpers
  pyproject.toml               package metadata
  src/voice2ai/
    main.py                    app orchestration
    config.py                  settings load/save
    audio.py                   microphone capture and pre-roll
    hotkey.py                  global hotkey listeners
    paste.py                   clipboard and Win32 paste backend
    vad.py                     continuous-mode VAD
    diagnostics.py             dependency / mic / network / provider checks
    providers/                 STT provider implementations
    ui/                        wizard, settings, widget, tray
  tests/                       offline unit tests
  build_tools/                 PyInstaller build files
```

## Development

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest ruff
python -m pytest tests/ -q
python -m ruff check src tests app.py
```

Tests run offline. They don't call providers, drive the real keyboard, or do
GUI automation.

## Privacy

Audio only goes to whichever STT provider you configured. There's no telemetry,
no analytics, no auto-update, no listening socket. API keys live in
`config.env`, which is gitignored. Security reports go through
[SECURITY.md](./SECURITY.md).

## License

MIT. See [LICENSE](./LICENSE).
