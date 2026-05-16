# Contributing to voice2ai

Thanks for taking a look. The project is a small Windows desktop tool, so the best
contributions are focused fixes with a clear local reproduction.

## Quick start

```bash
git clone https://github.com/<your-fork>/voice2ai.git
cd voice2ai
pip install -r requirements.txt
cp .env.example config.env       # then edit and add your STT key
python app.py
```

## Useful contribution areas

- **New STT backends**: add a class next to `src/voice2ai/providers/{siliconflow,openai,groq,azure}.py`. The protocol lives in `providers/base.py` and selection is driven by `VOICE2AI_PROVIDER`.
- **macOS / Linux support**: currently Windows-only because paste and global hotkeys need platform-specific handling. See issues [#1](https://github.com/lfzds4399-cpu/voice2ai/issues/1) and [#2](https://github.com/lfzds4399-cpu/voice2ai/issues/2).
- **Hotkey conflicts**: include OS version, keyboard layout, IME, target app, and the exact hotkey.
- **Error messages**: include the traceback or the relevant `voice2ai.log` lines with keys redacted.

## Before opening a PR

1. **Tests pass**: `python -m pytest tests/ -q` should pass.
2. **Compile clean**: `python -m compileall -q src app.py` should produce no warnings.
3. **Lint**: `python -m ruff check src tests app.py` should pass.
4. **Smoke it locally**: launch and verify the floating widget appears and the idle state shows a mic level.

## Style

- Source lives under `src/voice2ai/`; entrypoint is `app.py` at repo root.
- Keep runtime dependencies small.
- No telemetry, analytics, or auto-updates.
- Do not describe APIs, files, or commands in docs unless they exist in the repo.

## Reporting bugs

Open an issue with: OS, Python version, target app, hotkey, expected behavior,
actual behavior, and relevant logs. Redact API keys before posting.

## Security

Do not open a public issue for vulnerabilities. See [SECURITY.md](SECURITY.md).
