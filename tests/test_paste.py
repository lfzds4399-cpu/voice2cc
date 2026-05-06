"""tests/test_paste.py — verify paste_to_focus releases all modifiers before Ctrl+V.

The bug we're guarding: if the user holds Ctrl+Shift and we send Ctrl+V without
first releasing Shift, the OS sees Ctrl+Shift+V (different shortcut!).

We can't actually drive the OS keyboard in tests, so we patch the Win32 keybd_event
backend (Windows path) and assert the call sequence.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pyperclip  # noqa: F401  (imported for module presence check)

from voice2cc.paste import (
    _KEYEVENTF_KEYUP,
    _MODIFIERS_TO_RELEASE,
    _VK_CONTROL,
    _VK_V,
    copy_to_clipboard,
    paste_to_focus,
)


def test_copy_to_clipboard_uses_pyperclip():
    with patch("voice2cc.paste.pyperclip.copy") as mock_copy:
        copy_to_clipboard("hello")
    mock_copy.assert_called_once_with("hello")


def test_paste_releases_modifiers_before_ctrl_v():
    """Critical fix: any pre-existing modifier must be released before pressing Ctrl+V."""
    fake_user32 = MagicMock()

    with patch("voice2cc.paste.pyperclip.copy") as mock_copy, \
         patch("voice2cc.paste._user32", return_value=fake_user32), \
         patch("voice2cc.paste.time.sleep"), \
         patch("voice2cc.paste.sys.platform", "win32"):
        paste_to_focus("hi", settle_ms=10)

    mock_copy.assert_called_once_with("hi")

    calls = list(fake_user32.keybd_event.call_args_list)
    assert len(calls) >= len(_MODIFIERS_TO_RELEASE) + 4, (
        f"expected ≥{len(_MODIFIERS_TO_RELEASE) + 4} keybd_event calls "
        f"({len(_MODIFIERS_TO_RELEASE)} modifier releases + 4 Ctrl/V key events), "
        f"got {len(calls)}"
    )

    n_mods = len(_MODIFIERS_TO_RELEASE)
    for i, vk in enumerate(_MODIFIERS_TO_RELEASE):
        args = calls[i].args
        assert args[0] == vk, f"call #{i}: expected vk={vk:#x}, got vk={args[0]:#x}"
        assert args[2] == _KEYEVENTF_KEYUP, f"call #{i}: modifier release must use KEYEVENTF_KEYUP"

    paste_calls = calls[n_mods:n_mods + 4]
    assert paste_calls[0].args[0] == _VK_CONTROL and paste_calls[0].args[2] == 0, "ctrl down"
    assert paste_calls[1].args[0] == _VK_V and paste_calls[1].args[2] == 0, "v down"
    assert paste_calls[2].args[0] == _VK_V and paste_calls[2].args[2] == _KEYEVENTF_KEYUP, "v up"
    assert paste_calls[3].args[0] == _VK_CONTROL and paste_calls[3].args[2] == _KEYEVENTF_KEYUP, "ctrl up"
