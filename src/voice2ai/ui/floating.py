"""floating.py — top-most always-on widget showing state + mic level.

Decoupled from the orchestrator: the widget pulls state through a small interface
(see Controller protocol below), so the same widget works whether driven by tests
or by the real audio loop.
"""
from __future__ import annotations

import logging
import queue
import time
import tkinter as tk
from typing import Protocol

from ..i18n import t

logger = logging.getLogger("voice2ai.ui.floating")


class Controller(Protocol):
    def current_state(self) -> str: ...
    def volume_level(self) -> float: ...
    def hotkey_label(self) -> str: ...
    def on_close(self) -> None: ...


# state codes
IDLE = "idle"
RECORDING = "rec"
TRANSCRIBING = "stt"
DONE = "done"
ERROR = "err"


class FloatingPanel:
    def __init__(self, root: tk.Tk, controller: Controller, ui_q: "queue.Queue"):
        self.root = root
        self.controller = controller
        self.ui_q = ui_q

        root.title("voice2ai")
        try:
            root.overrideredirect(True)
        except tk.TclError:
            pass
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.94)
        root.configure(bg="#1e1e2e")

        # WS_EX_NOACTIVATE — make sure the widget can never be the foreground.
        # Without this, recording-state UI updates can briefly steal focus away
        # from the user's chat window between speech_start and paste, and
        # GetForegroundWindow returns the widget instead of the app the user
        # clicked on. With NOACTIVATE, Windows refuses to give the widget focus
        # at all and the user's last-clicked window stays foreground.
        try:
            import ctypes
            import sys
            if sys.platform == "win32":
                root.update_idletasks()  # ensure HWND exists
                # winfo_id returns child HWND; the toplevel comes from GetParent
                hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_TOOLWINDOW = 0x00000080
                u = ctypes.windll.user32
                ex_style = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
                u.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                 ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        except Exception:
            logger.exception("failed to set WS_EX_NOACTIVATE")

        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = 460, 92
        root.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 80}")

        bg = "#1e1e2e"
        fg = "#cdd6f4"
        accent = "#89b4fa"

        frm = tk.Frame(root, bg=bg, padx=12, pady=8)
        frm.pack(fill="both", expand=True)

        top = tk.Frame(frm, bg=bg)
        top.pack(fill="x")

        self.dot = tk.Canvas(top, width=14, height=14, bg=bg, highlightthickness=0)
        self.dot_circle = self.dot.create_oval(2, 2, 12, 12, fill="#6c7086", outline="")
        self.dot.pack(side="left", padx=(0, 8))

        self.status_lbl = tk.Label(
            top, text=t("status.idle"), bg=bg, fg=fg,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.status_lbl.pack(side="left")

        self.timer_lbl = tk.Label(top, text="", bg=bg, fg="#a6adc8", font=("Consolas", 9))
        self.timer_lbl.pack(side="left", padx=(10, 0))

        self.hotkey_lbl = tk.Label(
            top, text=controller.hotkey_label(), bg=bg, fg="#7f849c", font=("Consolas", 9),
        )
        self.hotkey_lbl.pack(side="right")

        close_btn = tk.Label(
            top, text="×", bg=bg, fg="#f38ba8", font=("Arial", 14, "bold"), cursor="hand2",
        )
        close_btn.pack(side="right", padx=(8, 0))
        close_btn.bind("<Button-1>", lambda e: self._close())

        self.vol_canvas = tk.Canvas(frm, height=10, bg="#11111b", highlightthickness=0)
        self.vol_canvas.pack(fill="x", pady=(8, 6))
        self.vol_bar = self.vol_canvas.create_rectangle(0, 0, 0, 10, fill=accent, outline="")

        self.text_lbl = tk.Label(
            frm, text="…", bg=bg, fg=fg,
            font=("Microsoft YaHei UI", 9), anchor="w", wraplength=420, justify="left",
        )
        self.text_lbl.pack(fill="x")

        for w in (frm, top, self.status_lbl, self.timer_lbl, self.text_lbl):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        self._drag_x = 0
        self._drag_y = 0
        self._t0 = None
        self._accent = accent

        root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(40, self._tick)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _close(self):
        try:
            self.controller.on_close()
        except Exception:
            logger.exception("controller.on_close failed")

    def _tick(self):
        try:
            w = self.vol_canvas.winfo_width()
            bar_w = int(w * self.controller.volume_level())
            color = "#f38ba8" if self.controller.current_state() == RECORDING else "#45475a"
            self.vol_canvas.itemconfig(self.vol_bar, fill=color)
            self.vol_canvas.coords(self.vol_bar, 0, 0, bar_w, 10)

            if self.controller.current_state() == RECORDING and self._t0:
                self.timer_lbl.config(text=f"{time.time() - self._t0:.1f}s")

            try:
                while True:
                    msg = self.ui_q.get_nowait()
                    self._apply(msg)
            except queue.Empty:
                pass
        finally:
            self.root.after(40, self._tick)

    def _apply(self, msg: dict):
        st = msg.get("state")
        if st == RECORDING:
            self.dot.itemconfig(self.dot_circle, fill="#f38ba8")
            self.status_lbl.config(text=t("status.recording"), fg="#f38ba8")
            self.text_lbl.config(text=t("status.recording_hint", hotkey=self.controller.hotkey_label()))
            self._t0 = msg.get("t0", time.time())
        elif st == TRANSCRIBING:
            self.dot.itemconfig(self.dot_circle, fill="#f9e2af")
            self.status_lbl.config(text=t("status.transcribing"), fg="#f9e2af")
            self.timer_lbl.config(text=f"{msg.get('duration', 0):.1f}s ➜")
            self.text_lbl.config(text=t("status.calling_api", provider=msg.get("provider", "")))
        elif st == DONE:
            self.dot.itemconfig(self.dot_circle, fill="#a6e3a1")
            label_key = "status.pasted" if msg.get("pasted") else "status.copied"
            self.status_lbl.config(text=t(label_key), fg="#a6e3a1")
            self.timer_lbl.config(text=f"{msg.get('latency_ms', 0)}ms")
            self.text_lbl.config(text=msg.get("text", ""))
        elif st == ERROR:
            self.dot.itemconfig(self.dot_circle, fill="#f38ba8")
            self.status_lbl.config(text=t("status.error"), fg="#f38ba8")
            self.timer_lbl.config(text="")
            self.text_lbl.config(text=msg.get("msg", ""))
        elif st == IDLE:
            self.dot.itemconfig(self.dot_circle, fill="#6c7086")
            self.status_lbl.config(text=t("status.idle"), fg="#cdd6f4")
            self.timer_lbl.config(text="")
            if "msg" in msg:
                self.text_lbl.config(text=msg["msg"])
