# Troubleshooting — voice2ai

When something doesn't work, the file to read first is `voice2ai.log` in the install dir. Tray → **Open log**.

## "Hotkey doesn't fire / nothing happens when I press F8"

| Possible cause | Fix |
|---|---|
| An IME (Chinese / Japanese) grabs Ctrl+Shift+Space | Tray → Settings → Hotkey → pick `f8` or `right ctrl` |
| Antivirus blocks pynput keyboard hook | Whitelist `voice2ai.exe` (or `python.exe` if running from source) |
| Tray icon missing | Open `voice2ai.log` — if `pystray unavailable`, `pip install pystray` |
| Two voice2ai instances running | Task Manager → kill one. Hotkey is global; first listener wins |

## "Recording fires but nothing pastes"

Look at the log for `paste sent via Ctrl+V` or `Ctrl+Shift+V`:
- **No paste line** → transcribe failed. Look for `STT error:`
- **Paste line present, target window doesn't show text** → focus drifted. See next section

## "Paste lands in the wrong window"

This was a real bug fixed in v0.4.1 (`WS_EX_NOACTIVATE` on the floating widget). If you see it on v0.4.1+, file an issue with:
- `voice2ai.log` lines for the failing paste (look for `focus restore hwnd=...`)
- Which window you wanted to paste into vs. where it actually went

Workaround: click the target window, **wait ~0.5 s** for focus to settle, then start speaking.

## "VAD never fires (continuous mode)"

```
[INFO] voice2ai.main: continuous mode ON (vad threshold=0.0150)
[INFO] voice2ai.vad: VAD: speech_start (rms=0.04 zcr=0.10)   ← what you should see
```

If you see `continuous mode ON` but no `speech_start` for minutes:
- Your mic level is too low → speak louder, or lower `VOICE2AI_VAD_THRESHOLD` to e.g. 0.008
- Wrong mic selected → Tray → Settings → Mic device

If you see `speech_start` but never `speech_end` (recording forever):
- Background noise stays above threshold → raise `VOICE2AI_VAD_THRESHOLD` to 0.025–0.030
- Or use a quieter mic / closer to mouth

## "VAD triggers on every breath"

- Raise `VOICE2AI_VAD_MAX_ZCR` to 0.13 (stricter ZCR gate)
- Or raise `VOICE2AI_VAD_MIN_SPEECH_MS` to 500 (short breaths under 500 ms ignored)
- Or simply use **F8 push-to-talk** — VAD has fundamental limits without webrtcvad / silero-vad (planned for v0.5)

## "Auto-Enter sent before I finished"

Disable it:
```
# config.env
VOICE2AI_AUTO_ENTER_AFTER_PASTE=false
```

## "Transcription is wrong / truncated"

- Model: try Groq `whisper-large-v3-turbo` (most accurate English)
- Mandarin: SiliconFlow `FunAudioLLM/SenseVoiceSmall`
- Mic too quiet: voice gets clipped at low end. Use a USB mic close to mouth
- API timeout: log will show `STT timeout` — switch provider or check internet

## "Microphone is locked by another app"

Zoom / Discord / DingTalk / OBS hold the mic exclusively on some Windows configs. Close them, or in Sound Settings allow shared mic access.

## "The widget vanishes when I click elsewhere"

Working as designed — the widget is `WS_EX_NOACTIVATE` (it can never have focus, can never steal yours). Tray → **Show widget** to bring it back.

## Diagnostics tool

Tray → **Diagnose…** runs all of the above checks programmatically. Send me the output if you file an issue.

## Filing a good bug report

Include:
1. voice2ai version (`v0.4.1` or commit hash)
2. Windows version (`winver`)
3. Last ~50 lines of `voice2ai.log` (mask any API key)
4. What you expected vs. what happened
5. Screenshot of widget state if it looks wrong

Issues: https://github.com/lfzds4399-cpu/voice2ai/issues
