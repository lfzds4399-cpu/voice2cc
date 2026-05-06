"""hotkey.py — global push-to-talk hotkey.

Parses human-readable hotkey strings ("ctrl+shift+space", "ctrl+alt+v", "f8") into
pynput key sets. Handles left/right modifier aliasing so the user pressing
left-shift fires the same hotkey as right-shift.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from pynput import keyboard

logger = logging.getLogger("voice2cc.hotkey")


# Map human names → primary pynput Key. Left-side variants are canonical.
_NAME_TO_KEY = {
    "ctrl": keyboard.Key.ctrl_l,
    "control": keyboard.Key.ctrl_l,
    "shift": keyboard.Key.shift,
    "alt": keyboard.Key.alt_l,
    "option": keyboard.Key.alt_l,
    "win": keyboard.Key.cmd_l,
    "cmd": keyboard.Key.cmd_l,
    "super": keyboard.Key.cmd_l,
    "space": keyboard.Key.space,
    "enter": keyboard.Key.enter,
    "return": keyboard.Key.enter,
    "tab": keyboard.Key.tab,
    "esc": keyboard.Key.esc,
    "escape": keyboard.Key.esc,
    "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete,
    "home": keyboard.Key.home,
    "end": keyboard.Key.end,
    "pageup": keyboard.Key.page_up,
    "pagedown": keyboard.Key.page_down,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "capslock": keyboard.Key.caps_lock,
    **{f"f{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)},
}

# Alias map: any of these → the canonical Key (so left/right shift count as same press).
_ALIASES = {
    keyboard.Key.ctrl: keyboard.Key.ctrl_l,
    keyboard.Key.ctrl_r: keyboard.Key.ctrl_l,
    keyboard.Key.shift_l: keyboard.Key.shift,
    keyboard.Key.shift_r: keyboard.Key.shift,
    keyboard.Key.alt: keyboard.Key.alt_l,
    keyboard.Key.alt_r: keyboard.Key.alt_l,
    keyboard.Key.alt_gr: keyboard.Key.alt_l,
    keyboard.Key.cmd: keyboard.Key.cmd_l,
    keyboard.Key.cmd_r: keyboard.Key.cmd_l,
}


def parse_hotkey(spec: str) -> set:
    """Parse 'ctrl+shift+space' → {Key.ctrl_l, Key.shift, Key.space}.

    Single-letter keys like 'a' become the literal char (pynput compares by char).
    Unknown tokens are ignored with a warning.
    """
    keys: set = set()
    for tok in spec.lower().replace(" ", "").split("+"):
        if not tok:
            continue
        if tok in _NAME_TO_KEY:
            keys.add(_NAME_TO_KEY[tok])
        elif len(tok) == 1:
            keys.add(keyboard.KeyCode.from_char(tok))
        else:
            logger.warning("unknown hotkey token %r in %r", tok, spec)
    return keys


def normalize_key(k):
    """Map left/right modifier variants to canonical."""
    return _ALIASES.get(k, k)


def hotkey_label(spec: str) -> str:
    """Human-display version: 'ctrl+shift+space' → 'Ctrl + Shift + Space'."""
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    pretty = []
    for p in parts:
        pretty.append(p.upper() if len(p) == 1 else p.title())
    return " + ".join(pretty)


class HotkeyListener:
    """Push-to-talk listener: fires on_press when all keys held, on_release when any released."""

    def __init__(self, hotkey_spec: str, on_press: Callable[[], None], on_release: Callable[[], None]):
        self.set_hotkey(hotkey_spec)
        self._on_press = on_press
        self._on_release = on_release
        self._held: set = set()
        self._fired: bool = False
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def set_hotkey(self, spec: str) -> None:
        self._spec = spec
        self._target = parse_hotkey(spec)
        if not self._target:
            logger.error("hotkey %r parsed to empty set; using ctrl+shift+space", spec)
            self._target = parse_hotkey("ctrl+shift+space")

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._handle_press, on_release=self._handle_release)
        self._listener.daemon = True
        self._listener.start()
        logger.info("hotkey listening: %s", self._spec)

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _handle_press(self, key):
        try:
            with self._lock:
                self._held.add(normalize_key(key))
                if self._target.issubset(self._held) and not self._fired:
                    self._fired = True
                    fire = True
                else:
                    fire = False
            if fire:
                try:
                    self._on_press()
                except Exception:
                    logger.exception("hotkey on_press handler raised")
        except Exception:
            logger.exception("hotkey press dispatch")

    def _handle_release(self, key):
        try:
            with self._lock:
                self._held.discard(normalize_key(key))
                if self._fired and not self._target.issubset(self._held):
                    self._fired = False
                    fire = True
                else:
                    fire = False
            if fire:
                try:
                    self._on_release()
                except Exception:
                    logger.exception("hotkey on_release handler raised")
        except Exception:
            logger.exception("hotkey release dispatch")


class ToggleHotkeyListener:
    """Fires on_toggle exactly once each time the user presses-and-releases the hotkey.

    Used for the continuous-mode (VAD) on/off switch. Different from HotkeyListener
    (push-to-talk hold) which fires both press and release.
    """

    def __init__(self, hotkey_spec: str, on_toggle: Callable[[], None]):
        self.set_hotkey(hotkey_spec)
        self._on_toggle = on_toggle
        self._held: set = set()
        self._fired: bool = False
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def set_hotkey(self, spec: str) -> None:
        self._spec = spec
        self._target = parse_hotkey(spec)
        if not self._target:
            logger.error("toggle hotkey %r parsed to empty set; using f9", spec)
            self._target = parse_hotkey("f9")

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._handle_press, on_release=self._handle_release)
        self._listener.daemon = True
        self._listener.start()
        logger.info("toggle hotkey listening: %s", self._spec)

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _handle_press(self, key):
        try:
            with self._lock:
                self._held.add(normalize_key(key))
                if self._target.issubset(self._held) and not self._fired:
                    self._fired = True
                    fire = True
                else:
                    fire = False
            if fire:
                try:
                    self._on_toggle()
                except Exception:
                    logger.exception("toggle on_toggle handler raised")
        except Exception:
            logger.exception("toggle press dispatch")

    def _handle_release(self, key):
        try:
            with self._lock:
                self._held.discard(normalize_key(key))
                if self._fired and not self._target.issubset(self._held):
                    self._fired = False
        except Exception:
            logger.exception("toggle release dispatch")
