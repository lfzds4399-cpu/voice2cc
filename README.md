# voice2cc

> Push-to-talk speech-to-text for Windows. Hold a hotkey, speak, release — text is pasted into the focused field.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

> 🌏 [中文 README](./README.zh-CN.md)

```
[hold key]   →   ● recording   (timer + mic level + pre-roll catches first syllable)
[release]    →   ◉ transcribing
                 →   ✓ pasted   (Ctrl+V into focus, modifier-safe)
```

## Why

Long prompts in Claude Code / Cursor / any chat UI are a thumb workout. Whisper-class STT is now fast enough that **holding a key and speaking** is genuinely faster than typing — but every voice tool I tried wanted to be a full dictation suite. I just wanted **one key, one paste, no UI in the way**.

## What's new in v0.3

The v0.1/v0.2 single-file proof-of-concept proved the idea. v0.3 makes it actually usable:

| Pain point in v0.2 | Fix in v0.3 |
|---|---|
| Pasting after Ctrl+Shift+Space sometimes opened VS Code's command palette | `paste_to_focus` now releases all modifiers and waits 200ms before sending Ctrl+V |
| First syllable of every recording was clipped | Always-on 300ms pre-roll ring buffer, prepended on hotkey-down |
| Only SiliconFlow was supported | 4 providers: SiliconFlow / OpenAI / Groq / Azure — all OpenAI-compatible HTTP |
| Editing config.env in Notepad to change a key | First-run wizard + Settings dialog (provider, mic, hotkey, language) |
| No tray icon — close the widget and you couldn't get it back | pystray icon with show/hide/settings/diagnose/quit |
| English UI only | Bilingual EN / ZH with auto-detect |
| "Why doesn't it work?" had no answer | Built-in diagnostics + rolling `voice2cc.log` |
| Required Python install for non-developers | PyInstaller spec for one-folder `.exe` build |

## Install

### For developers

Requires Python 3.10+.

```bash
git clone https://github.com/lfzds4399-cpu/voice2cc.git
cd voice2cc
pip install -r requirements.txt
python app.py
```

The first run shows a setup wizard. Pick a provider, paste your API key, click Test, click Save.

Or double-click `install.bat` once, then `start.bat` to launch.

### For end users (no Python required)

We don't yet ship a signed `.exe` (signing requires a $300/yr code-signing certificate). To build your own:

```bash
pip install pyinstaller
build_tools\build.bat
# → dist\voice2cc\voice2cc.exe
```

Zip the `dist\voice2cc\` folder and distribute it.

## Providers

Pick whichever suits your situation:

| Provider | Model recommendation | Best for |
|---|---|---|
| **SiliconFlow** | `FunAudioLLM/SenseVoiceSmall` | Free, Mandarin-native, China mainland accessible |
| **OpenAI** | `whisper-1` / `gpt-4o-mini-transcribe` | Global, paid, English-strong |
| **Groq** | `whisper-large-v3-turbo` | Fastest (~1s round trip), generous free tier |
| **Azure** | `whisper` deployment | Enterprise / data-residency requirements |

The wizard surfaces all four; settings can be changed any time from the tray icon.

## Hotkeys

Default: **Ctrl + Shift + Space**.

If your IME (Chinese / Japanese / Korean) grabs that combo, change it in **Settings → Hotkey**, or pick from the presets:

- `ctrl+alt+v`
- `ctrl+\``
- `f8` / `f9`
- `right ctrl`

## How it works

```
mic ──[InputStream]──┐
                     ├── always-on 300ms pre-roll ring buffer
hotkey ──[pynput]────┘
   │                       ┌── prepend pre-roll
   ↓ hold                  ↓
RECORDING → audio queue → wav file
   ↓ release
TRANSCRIBING → provider (SiliconFlow / OpenAI / Groq / Azure)
   ↓
release modifiers ─→ wait 200ms ─→ Ctrl+V
   ↓
DONE / ERROR (logged to voice2cc.log)
```

The pre-roll buffer fixes the "first syllable lost" problem common to push-to-talk tools.
The modifier-release-then-wait pattern fixes the "pasted as Ctrl+Shift+V" problem in apps like VS Code, Cursor, and any browser.

## Project layout

```
voice2cc/
├── app.py                       # entry-point shim
├── start.bat / install.bat
├── requirements.txt
├── pytest.ini
├── config.env (gitignored)      # your local config
├── .env.example                 # template
├── src/voice2cc/
│   ├── main.py                  # orchestrator
│   ├── config.py                # Settings + load/save
│   ├── i18n.py                  # EN/ZH string table
│   ├── audio.py                 # mic + pre-roll
│   ├── hotkey.py                # global push-to-talk
│   ├── paste.py                 # modifier-safe Ctrl+V
│   ├── diagnostics.py           # startup self-test
│   ├── autostart.py             # Windows registry HKCU\Run
│   ├── providers/               # STT providers (siliconflow, openai, groq, azure)
│   └── ui/                      # floating widget, tray, wizard, settings dialog
├── tests/                       # 38 unit tests, no GUI/network needed
└── build_tools/                 # PyInstaller spec + build.bat
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Hotkey doesn't fire | An IME grabs Ctrl+Shift+Space — change hotkey in Settings |
| Widget invisible | Right-click the tray icon → Show widget |
| Red dot but no level bar | Windows Settings → Privacy → Microphone → Allow desktop apps |
| Transcript wrong | Try a different model in Settings (Groq's whisper-large-v3 is strongest for English) |
| `pip install sounddevice` hangs | `pip install sounddevice --no-binary :all:` or use a mirror |
| No paste happens | Don't switch focus before release; check the target app doesn't block Ctrl+V |
| Mic locked error | Another app holds the mic (Zoom / Discord / DingTalk) — close it |
| Tray icon missing | `pystray` failed to install — voice2cc still runs, just without tray menu |
| SiliconFlow timeouts | You're outside mainland China — switch provider in Settings |

Diagnostics (Tray → Diagnose…) checks all of the above.

## Privacy

Audio is sent to whichever STT provider you configure. **Nothing is stored on disk** beyond a rolling debug log (`voice2cc.log`, max ~1.5MB total). No telemetry, no auto-update, no analytics. The whole codebase is < 2k LoC — read it.

## Development

```bash
git clone https://github.com/lfzds4399-cpu/voice2cc.git
cd voice2cc
pip install -r requirements.txt pytest
python -m pytest tests/ -q
```

PRs welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md). Security: [SECURITY.md](./SECURITY.md).

## License

MIT — see [LICENSE](./LICENSE).
