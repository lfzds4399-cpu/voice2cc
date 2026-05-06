"""paste.py — copy text to clipboard and paste into focused window.

Why we can't just use pynput:

pynput's keyboard.Controller works on most apps but in some Windows targets
(some browser sandboxes, some Electron apps, some game-launcher overlays) the
synthetic keypress is filtered out as untrusted input. The fix is to drop down
to Win32 keybd_event via ctypes — a lower API surface that more apps trust.

We also still need to:
  1. Release stuck modifiers (Ctrl/Shift/Alt) — your finger is physically still
     holding them when this runs, so otherwise the paste becomes Ctrl+Shift+V
     which opens the command palette in VS Code / Cursor.
  2. Sleep ~200ms — give the OS time to dispatch the modifier-up events.
"""
from __future__ import annotations

import ctypes
import logging
import sys
import time

import pyperclip

logger = logging.getLogger("voice2cc.paste")

# ── Win32 keybd_event constants ────────────────────────────────────────────
_KEYEVENTF_KEYUP = 0x0002
_VK_CONTROL = 0x11
_VK_LCONTROL = 0xA2
_VK_RCONTROL = 0xA3
_VK_SHIFT = 0x10
_VK_LSHIFT = 0xA0
_VK_RSHIFT = 0xA1
_VK_MENU = 0x12  # Alt
_VK_LMENU = 0xA4
_VK_RMENU = 0xA5
_VK_LWIN = 0x5B
_VK_RWIN = 0x5C
_VK_V = 0x56
_VK_RETURN = 0x0D  # Enter

_MODIFIERS_TO_RELEASE = (
    _VK_CONTROL, _VK_LCONTROL, _VK_RCONTROL,
    _VK_SHIFT, _VK_LSHIFT, _VK_RSHIFT,
    _VK_MENU, _VK_LMENU, _VK_RMENU,
    _VK_LWIN, _VK_RWIN,
)


def _user32():
    return ctypes.windll.user32 if sys.platform == "win32" else None


def _send_key(vk: int, *, up: bool) -> None:
    u = _user32()
    if u is None:
        return
    flags = _KEYEVENTF_KEYUP if up else 0
    u.keybd_event(vk, 0, flags, 0)


def _release_all_modifiers_win32() -> None:
    for vk in _MODIFIERS_TO_RELEASE:
        try:
            _send_key(vk, up=True)
        except Exception:
            pass


def _send_ctrl_v_win32() -> None:
    """Press Ctrl+V via Win32 keybd_event. Most reliable on Windows."""
    _send_key(_VK_CONTROL, up=False)
    try:
        _send_key(_VK_V, up=False)
        _send_key(_VK_V, up=True)
    finally:
        _send_key(_VK_CONTROL, up=True)


def _send_ctrl_shift_v_win32() -> None:
    """Press Ctrl+Shift+V — required for VS Code Terminal / Windows Terminal / Cursor."""
    _send_key(_VK_CONTROL, up=False)
    _send_key(_VK_SHIFT, up=False)
    try:
        _send_key(_VK_V, up=False)
        _send_key(_VK_V, up=True)
    finally:
        _send_key(_VK_SHIFT, up=True)
        _send_key(_VK_CONTROL, up=True)


def _send_enter_win32() -> None:
    """Press Enter via Win32 keybd_event."""
    _send_key(_VK_RETURN, up=False)
    _send_key(_VK_RETURN, up=True)


# Apps that need Ctrl+Shift+V for paste (Ctrl+V is intercepted or means something else)
_NEEDS_CTRL_SHIFT_V_TITLE = (
    "Visual Studio Code",
    "Cursor",
    "Windsurf",
    "Trae",                # Bytedance Trae editor (Electron)
    "Windows PowerShell ISE",
)
_NEEDS_CTRL_SHIFT_V_CLASS = (
    "CASCADIA_HOSTING_WINDOW_CLASS",  # Windows Terminal (modern)
    "WindowsTerminal.HwndHost",
    "mintty",                          # Git Bash / MSYS2 / Cygwin terminal
    "PuTTY",                           # PuTTY SSH terminal
    "Vim",                             # gVim (uses Ctrl+Shift+V conventionally)
)
# These windows DO accept Ctrl+V — explicit allowlist so future detections don't accidentally
# break them.  Browsers in particular: Ctrl+Shift+V opens incognito-paste / dev-only paste.
_NEVER_CTRL_SHIFT_V_CLASS = (
    "Chrome_RenderWidgetHostHWND",    # Chrome / Edge / Brave content area
    "MozillaWindowClass",             # Firefox
    "Notepad",
    "Notepad++",
    "ConsoleWindowClass",             # Legacy conhost.exe (cmd / classic PowerShell window)
)


def needs_ctrl_shift_v(hwnd: int = 0) -> bool:
    """Inspect the foreground (or supplied) window and return True if it's an
    app that intercepts Ctrl+V for something else and needs Ctrl+Shift+V to paste.

    Order of checks:
      1. NEVER list (browsers, Notepad, conhost) — always Ctrl+V even if title matches editor
      2. Class match (terminal classes)
      3. Title match (electron editors with no distinct class)

    Returns False on any error so we always degrade safely to Ctrl+V.
    """
    u = _user32()
    if u is None:
        return False
    try:
        if not hwnd:
            hwnd = u.GetForegroundWindow()
        cls_buf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hwnd, cls_buf, 256)
        class_name = cls_buf.value
        n = u.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, title_buf, n + 1)
        title = title_buf.value

        if class_name in _NEVER_CTRL_SHIFT_V_CLASS:
            return False
        if class_name in _NEEDS_CTRL_SHIFT_V_CLASS:
            return True
        for marker in _NEEDS_CTRL_SHIFT_V_TITLE:
            if marker in title:
                return True
        return False
    except Exception:
        return False


def copy_to_clipboard(text: str) -> None:
    pyperclip.copy(text)


def get_foreground_window() -> int:
    """Snapshot the current foreground HWND so we can restore it before paste."""
    u = _user32()
    if u is None:
        return 0
    try:
        return int(u.GetForegroundWindow())
    except Exception:
        return 0


def _restore_foreground(hwnd: int) -> bool:
    """Bring `hwnd` back to the foreground. Returns True on apparent success.

    Win32 SetForegroundWindow is restricted by foreground-lock rules
    (Windows refuses unless the calling thread "owns" foreground or was given
    permission). Workaround: AttachThreadInput to the target's thread, set,
    detach. This is the standard trick for tools like AutoHotKey.
    """
    u = _user32()
    if u is None or not hwnd:
        return False
    try:
        # Get the thread that owns the target window
        target_thread = u.GetWindowThreadProcessId(hwnd, None)
        kernel32 = ctypes.windll.kernel32
        current_thread = kernel32.GetCurrentThreadId()

        attached = False
        if target_thread and target_thread != current_thread:
            attached = bool(u.AttachThreadInput(current_thread, target_thread, True))

        # Only restore if actually minimised — otherwise SW_RESTORE incorrectly
        # un-maximises maximised windows (bug reported 2026-05-06).
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, 9)  # SW_RESTORE = 9, only when minimised
        ok = bool(u.SetForegroundWindow(hwnd))

        if attached:
            u.AttachThreadInput(current_thread, target_thread, False)
        return ok
    except Exception:
        return False


def paste_to_focus(
    text: str,
    settle_ms: int = 200,
    target_hwnd: int = 0,
    auto_enter: bool = False,
    smart_paste: bool = True,
) -> None:
    """Copy `text` to clipboard, refocus `target_hwnd`, send paste keystroke
    (Ctrl+V or Ctrl+Shift+V depending on target app), optionally press Enter.

    Args:
        text: transcribed text
        settle_ms: delay between modifier-release and paste keystroke
        target_hwnd: HWND captured at hotkey-press time (0 = current focus)
        auto_enter: if True, send Enter ~100ms after paste (zero-touch send)
        smart_paste: if True, detect VS Code/Terminal and use Ctrl+Shift+V

    Logs paste mode + auto-enter to voice2cc.log so user can audit.
    """
    copy_to_clipboard(text)

    if sys.platform != "win32":
        # Non-Windows fallback — use pynput (Mac/Linux not yet a target but be safe).
        from pynput import keyboard as _kb
        kbd = _kb.Controller()
        time.sleep(settle_ms / 1000.0)
        kbd.press(_kb.Key.ctrl)
        try:
            kbd.press("v"); kbd.release("v")
        finally:
            kbd.release(_kb.Key.ctrl)
        logger.info("paste sent via pynput (len=%d)", len(text))
        return

    # Windows path: restore focus → release stuck mods → choose paste flavour → enter
    u = _user32()
    if target_hwnd:
        restored = _restore_foreground(target_hwnd)
        logger.info("focus restore hwnd=%s ok=%s", hex(target_hwnd), restored)
        if not restored and u is not None:
            # SetForegroundWindow refused (e.g. the original window closed,
            # or Windows' foreground-lock blocked us). Degrade to whatever has
            # focus right now — better than pasting into a dead HWND.
            try:
                live_hwnd = int(u.GetForegroundWindow())
            except Exception:
                live_hwnd = 0
            if live_hwnd and live_hwnd != target_hwnd:
                logger.info("falling back to live foreground hwnd=%s", hex(live_hwnd))
                target_hwnd = live_hwnd
        time.sleep(0.05)

    _release_all_modifiers_win32()
    time.sleep(settle_ms / 1000.0)

    used_shift_v = smart_paste and needs_ctrl_shift_v(target_hwnd)
    if used_shift_v:
        _send_ctrl_shift_v_win32()
    else:
        _send_ctrl_v_win32()
    logger.info(
        "paste sent via %s (len=%d, hwnd=%s, auto_enter=%s)",
        "Ctrl+Shift+V" if used_shift_v else "Ctrl+V",
        len(text),
        hex(target_hwnd) if target_hwnd else "<none>",
        auto_enter,
    )

    if auto_enter:
        time.sleep(0.10)  # let the paste actually land before pressing Enter
        _send_enter_win32()
        logger.info("auto-enter sent")
