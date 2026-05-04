"""tests/test_hotkey.py — hotkey parser + listener thread-safety."""
from __future__ import annotations

import pytest
from pynput import keyboard

from voice2cc.hotkey import HotkeyListener, hotkey_label, normalize_key, parse_hotkey


def test_parse_simple_combo():
    keys = parse_hotkey("ctrl+shift+space")
    assert keyboard.Key.ctrl_l in keys
    assert keyboard.Key.shift in keys
    assert keyboard.Key.space in keys


def test_parse_function_key():
    keys = parse_hotkey("f8")
    assert keyboard.Key.f8 in keys


def test_parse_letter():
    keys = parse_hotkey("ctrl+v")
    assert keyboard.Key.ctrl_l in keys
    chars = {k.char for k in keys if isinstance(k, keyboard.KeyCode)}
    assert "v" in chars


def test_normalize_left_right_modifier():
    assert normalize_key(keyboard.Key.shift_r) == keyboard.Key.shift
    assert normalize_key(keyboard.Key.ctrl_r) == keyboard.Key.ctrl_l


def test_label_format():
    assert hotkey_label("ctrl+shift+space") == "Ctrl + Shift + Space"
    assert hotkey_label("f8") == "F8"
    assert hotkey_label("ctrl+v") == "Ctrl + V"


def test_listener_construct_and_set_hotkey():
    fired = []
    listener = HotkeyListener("ctrl+shift+space",
                              on_press=lambda: fired.append("p"),
                              on_release=lambda: fired.append("r"))
    listener.set_hotkey("ctrl+alt+v")
    assert listener._spec == "ctrl+alt+v"
    assert keyboard.Key.alt_l in listener._target


def test_listener_ignores_unknown_token():
    keys = parse_hotkey("ctrl+nonsense+space")
    # 'nonsense' is silently ignored, ctrl+space should still parse
    assert keyboard.Key.ctrl_l in keys
    assert keyboard.Key.space in keys
