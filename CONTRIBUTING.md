# Contributing to voice2ai

Thanks for taking a look. This started as a tool I built for my own Claude Code workflow, so contributions that make it work for *your* setup are exactly what I'm hoping for.

## Quick start

```bash
git clone https://github.com/<your-fork>/voice2ai.git
cd voice2ai
pip install -r requirements.txt
cp .env.example config.env       # then edit and add your STT key
python voice2ai.py
```

## What I'd love help with

- **New STT backends** — local Whisper, OpenAI, Deepgram, Azure. The pluggable seam is in `transcribe()` in `voice2ai.py`.
- **macOS / Linux support** — currently Windows-only because of `pynput` and `pyperclip` quirks. Patches very welcome.
- **Hotkey conflicts** — if you found a combo that doesn't fight the IME on your locale, share the config.
- **Error messages** — anything you hit that confused you, the fix is usually a clearer message.

## Before opening a PR

1. **Compile clean**: `python -m compileall voice2ai.py` should produce no warnings.
2. **Lint**: `ruff check voice2ai.py --select=E,F,W` should pass.
3. **Smoke it locally**: launch and verify the floating widget appears and at least the *idle* state shows your mic level.

## Style

- Single file (`voice2ai.py`) is intentional — keep it that way unless there's a strong case to split.
- Standard library first, minimal deps.
- No telemetry, no analytics, no auto-updates.

## Reporting bugs

Open an issue with: OS, Python version, your `config.env` minus the API key, and the console output. If the widget itself crashes, run from a terminal and paste the traceback.

## License

By contributing you agree your work is released under the MIT License.
