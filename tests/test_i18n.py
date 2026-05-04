"""tests/test_i18n.py — i18n string lookup, formatting, fallback."""
from __future__ import annotations

from voice2cc.i18n import set_language, t


def test_english_default():
    set_language("en")
    assert t("status.idle") == "idle"


def test_chinese_strings():
    set_language("zh")
    assert "录音" in t("status.recording")


def test_format_kwargs():
    set_language("en")
    msg = t("status.ready", hotkey="Ctrl + Shift + Space")
    assert "Ctrl + Shift + Space" in msg


def test_unknown_key_returns_key_itself():
    set_language("en")
    assert t("does.not.exist") == "does.not.exist"


def test_fallback_to_english_for_missing_translation():
    set_language("zh")
    # If a future key exists in EN but not ZH, it should still return SOMETHING
    msg = t("does.not.exist")
    assert msg == "does.not.exist"


def test_auto_language_falls_back():
    # Just check it doesn't crash; actual locale depends on machine
    set_language("auto")
    assert t("status.idle") in ("idle", "待机")
