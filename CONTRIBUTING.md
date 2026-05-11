# Contributing to voice2ai

Thanks for taking a look. This started as a tool I built for my own Claude Code workflow, so contributions that make it work for *your* setup are exactly what I'm hoping for.

## Quick start

```bash
git clone https://github.com/<your-fork>/voice2ai.git
cd voice2ai
pip install -r requirements.txt
cp .env.example config.env       # then edit and add your STT key
python app.py
```

## What I'd love help with

- **New STT backends** — add a class next to `src/voice2ai/providers/{siliconflow,openai,groq,azure}.py`. The protocol lives in `providers/base.py` and selection is driven by `VOICE2AI_PROVIDER`.
- **macOS / Linux support** — currently Windows-only because of `pynput` and `pyperclip` quirks. See pinned issues [#1](https://github.com/lfzds4399-cpu/voice2ai/issues/1) (macOS) and [#2](https://github.com/lfzds4399-cpu/voice2ai/issues/2) (Linux).
- **Hotkey conflicts** — if you found a combo that doesn't fight the IME on your locale, share the config.
- **Error messages** — anything you hit that confused you, the fix is usually a clearer message.

## Before opening a PR

1. **Tests pass**: `pytest tests/` should report 48 passing.
2. **Compile clean**: `python -m compileall src/ app.py` should produce no warnings.
3. **Lint**: `ruff check src/ tests/ app.py` should pass.
4. **Smoke it locally**: launch and verify the floating widget appears and at least the *idle* state shows your mic level.

## Style

- Source lives under `src/voice2ai/` (package layout); entrypoint is `app.py` at repo root.
- Standard library first, minimal deps.
- No telemetry, no analytics, no auto-updates.

## Reporting bugs

Open an issue with: OS, Python version, your `config.env` minus the API key, and the console output. If the widget itself crashes, run from a terminal and paste the traceback.

## License

By contributing you agree your work is released under the MIT License.
