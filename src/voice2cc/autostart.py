"""autostart.py — Windows HKCU autostart registry entry.

Adds/removes a value under:
  HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run

We only ever touch HKCU (current user), so no admin elevation is needed and the
change cannot affect other users on the machine.

On non-Windows platforms the module is a no-op (warns once).
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger("voice2cc.autostart")

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "voice2cc"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def is_enabled() -> bool:
    if not _is_windows():
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ) as k:
            value, _ = winreg.QueryValueEx(k, _VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception:
        logger.exception("autostart is_enabled")
        return False


def enable(exe_path: str) -> bool:
    """Register `exe_path` to start with Windows. Returns True on success."""
    if not _is_windows():
        logger.warning("autostart.enable: non-Windows, skipped")
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, _VALUE_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        logger.info("autostart enabled: %s", exe_path)
        return True
    except Exception:
        logger.exception("autostart enable failed")
        return False


def disable() -> bool:
    if not _is_windows():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, _VALUE_NAME)
        logger.info("autostart disabled")
        return True
    except FileNotFoundError:
        return True   # already absent
    except Exception:
        logger.exception("autostart disable failed")
        return False
