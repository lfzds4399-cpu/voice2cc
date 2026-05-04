"""tests/test_paste.py — verify paste_to_focus releases all modifiers before Ctrl+V.

The bug we're guarding: if the user holds Ctrl+Shift and we send Ctrl+V without
first releasing Shift, the OS sees Ctrl+Shift+V (different shortcut!).

We can't actually drive the OS keyboard in tests, so we patch pynput.Controller
and assert the call sequence.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock, call

import pyperclip

from voice2cc.paste import paste_to_focus, copy_to_clipboard


def test_copy_to_clipboard_uses_pyperclip():
    with patch("voice2cc.paste.pyperclip.copy") as mock_copy:
        copy_to_clipboard("hello")
    mock_copy.assert_called_once_with("hello")


def test_paste_releases_modifiers_before_ctrl_v():
    """Critical fix: any pre-existing modifier must be released before pressing Ctrl+V."""
    fake_kbd = MagicMock()

    with patch("voice2cc.paste.pyperclip.copy") as mock_copy, \
         patch("voice2cc.paste.keyboard.Controller", return_value=fake_kbd), \
         patch("voice2cc.paste.time.sleep"):
        paste_to_focus("hi", settle_ms=10)

    mock_copy.assert_called_once_with("hi")

    # Collect the order of release vs press calls
    method_names = [c[0] for c in fake_kbd.method_calls]
    # The first calls must all be `release(...)` for modifiers
    first_release_count = 0
    for name in method_names:
        if name == "release":
            first_release_count += 1
        else:
            break
    assert first_release_count >= 6, \
        f"expected ≥6 modifier releases before any press, got call sequence: {method_names}"

    # Subsequent calls must include a press(ctrl) → press('v') → release('v') → release(ctrl)
    assert "press" in method_names, "should press something after releasing modifiers"
