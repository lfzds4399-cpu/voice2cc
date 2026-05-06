"""tray.py — system tray icon.

Optional: pystray + Pillow may not install on every machine. If unavailable, this
module returns a NullTray so the app still runs (just without a tray menu).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("voice2ai.ui.tray")


def _make_icon_image(size: int = 64):
    """Generate a small mic icon procedurally so we don't ship a PNG asset."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # mic capsule
    cx = size // 2
    top = size // 5
    bot = size // 2 + size // 10
    cap_w = size // 3
    d.rounded_rectangle(
        (cx - cap_w // 2, top, cx + cap_w // 2, bot),
        radius=cap_w // 2,
        fill=(137, 180, 250, 255),
    )
    # arc base
    d.arc(
        (cx - cap_w, bot - cap_w // 2, cx + cap_w, bot + cap_w),
        start=0, end=180, fill=(137, 180, 250, 255), width=3,
    )
    # stand
    d.line((cx, bot + cap_w // 2, cx, size - size // 8), fill=(137, 180, 250, 255), width=3)
    return img


class NullTray:
    """No-op fallback when pystray is unavailable."""
    def start(self): pass
    def stop(self): pass
    def update_visibility_label(self, _hidden: bool): pass


class Tray:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_hide: Callable[[], None],
        on_settings: Callable[[], None],
        on_diagnose: Callable[[], None],
        on_open_log: Callable[[], None],
        on_quit: Callable[[], None],
        is_widget_visible: Callable[[], bool],
    ):
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_settings = on_settings
        self._on_diagnose = on_diagnose
        self._on_open_log = on_open_log
        self._on_quit = on_quit
        self._is_widget_visible = is_widget_visible

        try:
            import pystray  # type: ignore
        except ImportError as e:
            raise RuntimeError(f"pystray unavailable: {e}")

        from ..i18n import t
        self._pystray = pystray
        self._t = t

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _build_menu(self):
        from ..i18n import t
        ps = self._pystray
        visible = self._is_widget_visible()
        toggle_label = t("tray.hide") if visible else t("tray.show")
        return ps.Menu(
            ps.MenuItem(toggle_label, self._toggle_widget, default=True),
            ps.MenuItem(t("tray.settings"), lambda *_: self._on_settings()),
            ps.MenuItem(t("tray.diagnose"), lambda *_: self._on_diagnose()),
            ps.MenuItem(t("tray.open_log"), lambda *_: self._on_open_log()),
            ps.Menu.SEPARATOR,
            ps.MenuItem(t("tray.quit"), lambda *_: self._on_quit()),
        )

    def _toggle_widget(self, *_args):
        if self._is_widget_visible():
            self._on_hide()
        else:
            self._on_show()
        if self._icon is not None:
            self._icon.menu = self._build_menu()

    def start(self) -> None:
        ps = self._pystray
        self._icon = ps.Icon("voice2ai", _make_icon_image(), "voice2ai", self._build_menu())
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("tray icon started")

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def update_visibility_label(self, _hidden: bool) -> None:
        if self._icon is not None:
            self._icon.menu = self._build_menu()


def make_tray(*args, **kwargs):
    """Factory: returns a real Tray or NullTray depending on pystray availability."""
    try:
        return Tray(*args, **kwargs)
    except Exception as e:
        logger.warning("tray disabled: %s", e)
        return NullTray()
