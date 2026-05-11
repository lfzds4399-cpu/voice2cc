# Pull request

**What this changes**

One-paragraph summary.

**Why**

Linked issue or motivation.

**Tested on**

- OS:
- Python:
- STT backend:

**Checks**

- [ ] `python -m compileall src/ app.py` is clean
- [ ] `ruff check src/ tests/ app.py` passes
- [ ] `pytest tests/` reports 48 passing
- [ ] Floating widget still launches and shows mic level
- [ ] No new always-on paid services or telemetry

**Risk**

Anything reviewers should pay extra attention to (hotkey changes, audio handling, paste mechanism).
