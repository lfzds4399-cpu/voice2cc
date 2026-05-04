"""paste.py — copy text to clipboard and paste into focused window.

Critical fix vs v0.2:

When the user holds Ctrl+Shift+Space and releases, the OS may still be in the middle
of dispatching the modifier-up events when we send Ctrl+V. The result: many apps see
the synthetic keystroke as Ctrl+Shift+V, which means very different things —

  - VS Code / Cursor: opens the command palette
  - Browsers: opens incognito window
  - Terminals (Win Terminal, Cmder): paste-without-formatting (often fine, sometimes a no-op)
  - Office apps: paste-special

Fix: explicitly synth a release for every modifier we know about, then sleep, then
press Ctrl+V. The release is idempotent — releasing a key that wasn't pressed is a
no-op on Windows.
"""
from __future__ import annotations

import logging
import time

import pyperclip
from pynput import keyboard

logger = logging.getLogger("voice2cc.paste")


_MODIFIER_KEYS = (
    keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
    keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
)
# alt_gr / cmd / cmd_l / cmd_r exist on some platforms; check via getattr
_OPTIONAL_MOD_NAMES = ("alt_gr", "cmd", "cmd_l", "cmd_r")


def _release_all_modifiers(kbd: keyboard.Controller) -> None:
    for k in _MODIFIER_KEYS:
        try:
            kbd.release(k)
        except Exception:
            pass
    for name in _OPTIONAL_MOD_NAMES:
        k = getattr(keyboard.Key, name, None)
        if k is None:
            continue
        try:
            kbd.release(k)
        except Exception:
            pass


def copy_to_clipboard(text: str) -> None:
    pyperclip.copy(text)


def paste_to_focus(text: str, settle_ms: int = 200) -> None:
    """Copy `text` to clipboard, release stuck modifiers, send Ctrl+V."""
    copy_to_clipboard(text)
    kbd = keyboard.Controller()
    _release_all_modifiers(kbd)
    time.sleep(settle_ms / 1000.0)
    kbd.press(keyboard.Key.ctrl)
    try:
        kbd.press("v")
        kbd.release("v")
    finally:
        kbd.release(keyboard.Key.ctrl)
    logger.debug("paste sent (len=%d)", len(text))
