# voice2cc · push-to-talk for Claude Code

[![lint](https://github.com/lfzds4399-cpu/voice2cc/actions/workflows/lint.yml/badge.svg)](https://github.com/lfzds4399-cpu/voice2cc/actions/workflows/lint.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

> 中文版 → [README.zh-CN.md](./README.zh-CN.md)

Hold a hotkey, speak, release — your speech is transcribed and pasted into the focused text field.
Built for [Claude Code](https://claude.com/claude-code), works in any input.

## At a glance

```
[hold key]   →   🔴 recording   (timer + mic level bar)
[release]    →   🟡 transcribing
                 →   🟢 ✓ pasted   (Ctrl+V into focus)
```

## Why I built this

Long Chinese prompts in Claude Code are a thumb workout. Whisper-class STT is now fast enough that *holding a key and speaking* is genuinely faster than typing — but every voice tool I tried wanted to be a dictation suite, an accessibility framework, or a $30/mo SaaS. I just wanted **one key, one paste, no UI in my way**. So this is that.

## Features

- **Push-to-talk hotkey** (default `Ctrl + Shift + Space`)
- **Always-on-top floating widget** — drag anywhere, real-time mic level bar (works in idle so you can verify the mic is alive)
- **5 visual states**: idle / recording / transcribing / pasted / error
- **Audio cues** at start, end, success
- **Startup self-test** — pings the STT API to verify key + model + network on boot
- **Typical 1–3s round-trip** on stable connection
- **Pluggable backend** — defaults to SiliconFlow's `SenseVoiceSmall` (OpenAI-compatible HTTP); swap any other compatible STT in `voice2cc.py`
- **Single-file Python** — < 500 LoC, no DB, no telemetry, no auto-update

## Install

Requires Python 3.9+. Currently Windows-only (PRs for macOS / Linux welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md)).

```bash
git clone https://github.com/<your-username>/voice2cc.git
cd voice2cc
pip install -r requirements.txt
cp .env.example config.env       # then edit and add your STT key
python voice2cc.py
```

Or on Windows just double-click `install.bat` once, then `start.bat` to launch.

Get a free SiliconFlow key at https://siliconflow.cn (or swap the backend for any OpenAI-compatible STT — see `transcribe()` in `voice2cc.py`).

## Configure

`config.env`:

```env
SILICONFLOW_API_KEY=sk-...
STT_MODEL=FunAudioLLM/SenseVoiceSmall
```

Alternative models that work out of the box:
- `iic/SenseVoiceSmall`
- `openai-whisper-large-v3`

## Customize the hotkey

Edit `HOT_KEYS` near the top of `voice2cc.py`:

```python
HOT_KEYS = {keyboard.Key.ctrl_r, keyboard.Key.shift, keyboard.Key.space}
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Hotkey doesn't fire | A Chinese / Japanese / Korean IME is grabbing it — change `HOT_KEYS` |
| Widget invisible | Probably off-screen — restart `start.bat` to reset position |
| Red light on but no level bar | Mic permission: Windows Settings → Privacy → Microphone → Allow desktop apps |
| Transcript wrong | Try a different `STT_MODEL`; `SenseVoiceSmall` is best for Mandarin |
| `pip install sounddevice` hangs | `pip install sounddevice --no-binary :all:` or switch mirror |
| No paste happens | Don't switch focus before release; check the target app doesn't block Ctrl+V |
| Mic locked error | Another app holds the mic (DingTalk/Zoom/Discord) — close it |

## Privacy

Audio is sent to whichever STT endpoint you configure (SiliconFlow by default). Nothing is stored locally. There is no telemetry, no analytics, no auto-update mechanism — read `voice2cc.py` end-to-end if you want to verify (it's one file).

## License

MIT — see [LICENSE](./LICENSE).
