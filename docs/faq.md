# FAQ — voice2cc

### Q: Is my voice recorded / sent anywhere I can't see?
Audio is sent to the STT provider you configured (Groq / OpenAI / SiliconFlow / Azure) — that's where the transcription happens. **Nothing else** leaves your machine. No telemetry, no analytics, no auto-update. There's a rolling debug log at `voice2cc.log` (max ~1.5 MB) — readable, deletable.

### Q: How is this different from Wispr Flow / Talon / Windows dictation?
- **Wispr Flow**: Mac-first, $15/mo
- **Talon**: brilliant, but year-long learning curve and command-language oriented
- **Windows dictation**: modal (locks focus) and English-only on most builds
- **voice2cc**: hold-and-paste primitive, $0, MIT, ~2 k LoC, 4 STT providers, English + Chinese first-class

### Q: Can I use it without an internet connection?
Currently no — all 4 providers are HTTP. Local Whisper support is on the roadmap.

### Q: My hotkey collides with my IME / VS Code shortcut.
Tray → Settings → Hotkey. Pre-set options: F8, F9, Right Ctrl, Ctrl+Alt+V, Ctrl+\`. Or any custom combo (`shift+space`, `f6` etc).

### Q: VAD continuous mode misses me / triggers on breath. How do I tune?
Edit `config.env` (or wait for the Settings UI in v0.5):

```
VOICE2CC_VAD_THRESHOLD=0.015          # raise if breath/fan triggers; lower if you talk softly
VOICE2CC_VAD_SILENCE_RATIO=0.4        # how loose the "exit speech" gate is (mid-sentence pauses)
VOICE2CC_VAD_MAX_ZCR=0.18             # tighten to 0.13 to reject more breath; 1.0 disables
VOICE2CC_VAD_MIN_SPEECH_MS=250        # raise to 500 to ignore short clicks
VOICE2CC_VAD_MIN_SILENCE_MS=1500      # how long a pause must be to end an utterance
```

### Q: Does it work on Mac / Linux?
Not yet. Mac/Linux is the #1 wishlist item — see [#1](../../issues) (PRs welcome). The bottleneck is the paste backend (`paste.py` is currently Win32 keybd_event); the rest of the codebase is platform-neutral.

### Q: Why does the .exe trigger SmartScreen?
Because we don't pay for code-signing ($300+/yr). Until that changes: **More info → Run anyway**. The build pipeline is open-source and reproducible from `build_tools/voice2cc.spec`.

### Q: Auto-Enter sent my message before I was ready!
Disable it in `config.env`:
```
VOICE2CC_AUTO_ENTER_AFTER_PASTE=false
```
Now voice2cc only pastes; you press Enter when you want to send.

### Q: Why is the transcription wrong?
- **English-strong → Groq `whisper-large-v3-turbo`** (fastest, most accurate for English)
- **Mandarin-strong → SiliconFlow `FunAudioLLM/SenseVoiceSmall`**
- Tray → Settings → Model

### Q: Can voice2cc submit Enter in apps that intercept Enter (e.g. multi-line chat)?
Currently sends a single Enter. If your chat app needs Shift+Enter for newline / Enter for send — that's the standard, and voice2cc fits it. If it's reversed, file an issue.

### Q: How do I add a new STT provider?
`src/voice2cc/providers/` has 4 implementations. Subclass `Provider` (in `base.py`), implement `transcribe(wav_path) → TranscribeResult`, register in `__init__.py`. ~30 lines. PR welcome.
