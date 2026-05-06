# Getting started — voice2ai

5 minutes from clone → "I just spoke into my AI chat and it auto-submitted."

## 1. Install

### Path A: Download the .exe (no Python needed)

1. Go to the [latest release](https://github.com/lfzds4399-cpu/voice2ai/releases/latest)
2. Download **`voice2ai-vX.Y.Z-windows.zip`**
3. Unzip anywhere
4. Double-click `voice2ai.exe`

> Windows SmartScreen will warn the first time (the .exe is unsigned — code-signing certs are $300/yr). Click **More info → Run anyway**. Inspect `voice2ai.log` later if you don't trust me.

### Path B: From source (developers)

```powershell
git clone https://github.com/lfzds4399-cpu/voice2ai
cd voice2ai
python -m pip install -r requirements.txt
python app.py
```

## 2. Pick an STT provider

You need an API key from one of:

| Provider | Best for | Free tier |
|---|---|---|
| [**Groq**](https://console.groq.com) | English, fastest (~1 s round trip) | ✅ generous |
| [**SiliconFlow**](https://cloud.siliconflow.cn) | Mandarin, China-mainland-friendly | ✅ free model `SenseVoiceSmall` |
| [**OpenAI**](https://platform.openai.com) | Global, paid | $5 minimum |
| [**Azure**](https://portal.azure.com) | Enterprise / data-residency | requires region setup |

The first-run wizard asks. Paste your key, click **Test**, click **Save**.

## 3. Two modes — pick when to use which

### Push-to-talk (default)

```
hold F8  →  speak  →  release
                     ↓
                 transcript pastes into focused window
                     ↓
                 auto-Enter (submit)
```

Best for: **AI chat** where you want to think before submitting, then send a finished sentence.

### Continuous mode (VAD)

```
press F9 once  →  walk away if you want, voice2ai keeps listening
              ↓
              [you speak] → [pause 1.5 s]  →  utterance pastes + auto-Enters
              ↓
              keep speaking forever, every utterance fires
              ↓
press F9 again  →  stops listening
```

Best for: **long conversations** where you want hands-free dictation. Use a USB mic in a quiet room for best VAD reliability.

## 4. The widget + tray

A small floating widget appears bottom-right. It shows:
- ● red — recording
- ◉ blue — transcribing
- ✓ green — pasted (with elapsed ms)
- ⌨ white — idle

A tray icon (Windows system tray) gives you:
- Show / hide widget
- Settings (provider / hotkey / mic / language / autostart)
- Diagnose (mic / network / API health)
- Open log
- Quit

If the tray icon is missing, `pip install pystray` was skipped — voice2ai still runs, just without the menu.

## 5. Where things land

| Window you've focused | Paste keystroke voice2ai sends |
|---|---|
| VS Code, Cursor, Windsurf, Trae | Ctrl+Shift+V |
| Windows Terminal, PowerShell ISE, mintty, PuTTY, gVim | Ctrl+Shift+V |
| Chrome, Edge, Firefox | Ctrl+V (forced — Ctrl+Shift+V opens incognito-paste) |
| Notepad, classic conhost | Ctrl+V (forced) |
| WeChat, Discord, Slack, Notion, Word, anything else | Ctrl+V (default) |

If your app paste-shortcut is different, file an issue.

## Next

- [FAQ](./faq.md) — top 10 questions
- [Troubleshooting](./troubleshooting.md) — when something doesn't work
- [Contributing](../CONTRIBUTING.md) — Mac / Linux ports welcome
