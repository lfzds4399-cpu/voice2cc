"""main.py — orchestrator that wires modules together.

Lifecycle:
  1. Set up logging
  2. Load Settings → set i18n language
  3. If no api_key → show wizard
  4. Open mic + hotkey listener
  5. Build floating widget (optional) and tray icon
  6. Pump tk mainloop until quit
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from . import __version__
from .audio import MicCapture
from .autostart import disable as autostart_disable, enable as autostart_enable, is_enabled as autostart_is_enabled
from .config import CONFIG_PATH, Settings, install_root, load as load_settings, save as save_settings
from .diagnostics import diagnose, format_report
from .hotkey import HotkeyListener, ToggleHotkeyListener, hotkey_label
from .i18n import set_language, t
from .paste import copy_to_clipboard, get_foreground_window, paste_to_focus
from .providers import get_provider
from .ui.floating import DONE, ERROR, FloatingPanel, IDLE, RECORDING, TRANSCRIBING
from .ui.settings_dialog import SettingsDialog
from .ui.tray import make_tray
from .ui.wizard import Wizard
from .vad import EnergyVAD, VADConfig


# ── logging setup ────────────────────────────────────────────────
def _setup_logging(settings: Settings) -> Path:
    log_path = install_root() / "voice2ai.log"
    logger = logging.getLogger("voice2ai")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    if not logger.handlers:
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=512_000, backupCount=2, encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(fh)
    return log_path


def _audio_cue(freq: int, dur_ms: int, enabled: bool) -> None:
    if not enabled:
        return
    try:
        import winsound
        winsound.Beep(freq, dur_ms)
    except Exception:
        pass


# ── orchestrator ─────────────────────────────────────────────────
class Voice2CC:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger("voice2ai.main")

        self._state: str = IDLE
        self._t0: float = 0.0
        self._record_started: list = []
        self.ui_q: "queue.Queue[dict]" = queue.Queue()

        self.mic = MicCapture(
            sample_rate=settings.sample_rate,
            input_device=settings.input_device,
            preroll_sec=settings.preroll_sec,
        )

        self.hotkeys = HotkeyListener(
            settings.hotkey,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

        # Toggle hotkey for hands-free continuous (VAD) mode
        self.continuous_toggle = ToggleHotkeyListener(
            settings.continuous_toggle_hotkey,
            on_toggle=self._toggle_continuous_mode,
        )
        self._continuous_active: bool = False
        self._vad: Optional[EnergyVAD] = None

        self.provider = self._build_provider(settings)

        self.tk_root: Optional[tk.Tk] = None
        self.widget: Optional[FloatingPanel] = None
        self.tray = None
        self._widget_visible: bool = settings.show_floating_widget
        self._quit_requested: bool = False

    @staticmethod
    def _build_provider(s: Settings):
        cls = get_provider(s.provider)
        return cls(
            api_key=s.api_key,
            model=s.model,
            api_base=s.effective_api_base,
            azure_region=s.azure_region,
        )

    # ── widget controller protocol ─────────────────────────────
    def current_state(self) -> str:
        return self._state

    def volume_level(self) -> float:
        return self.mic.volume_level

    def hotkey_label(self) -> str:
        return hotkey_label(self.settings.hotkey)

    def on_close(self) -> None:
        self.hide_widget()

    # ── tray actions ───────────────────────────────────────────
    def show_widget(self) -> None:
        if self.tk_root is None:
            return
        if self.widget is None:
            self.widget = FloatingPanel(self.tk_root, self, self.ui_q)
        else:
            try:
                self.tk_root.deiconify()
            except tk.TclError:
                pass
        self._widget_visible = True
        if self.tray is not None:
            self.tray.update_visibility_label(False)

    def hide_widget(self) -> None:
        if self.tk_root is None:
            return
        try:
            self.tk_root.withdraw()
        except tk.TclError:
            pass
        self._widget_visible = False
        if self.tray is not None:
            self.tray.update_visibility_label(True)

    def is_widget_visible(self) -> bool:
        return self._widget_visible

    def open_settings(self) -> None:
        # Settings dialog must run on the tk thread; schedule it
        if self.tk_root is None:
            return
        self.tk_root.after(0, self._open_settings_on_main)

    def _open_settings_on_main(self) -> None:
        dlg = SettingsDialog(self.settings, parent=self.tk_root)
        new_settings = dlg.run()
        if new_settings is None:
            return
        self._apply_settings(new_settings)

    def _apply_settings(self, new: Settings) -> None:
        old_hotkey = self.settings.hotkey
        old_provider = (self.settings.provider, self.settings.api_key, self.settings.model,
                        self.settings.api_base, self.settings.azure_region)
        old_input_device = self.settings.input_device
        self.settings = new

        set_language(new.language)
        if new.hotkey != old_hotkey:
            self.hotkeys.set_hotkey(new.hotkey)

        new_provider_tuple = (new.provider, new.api_key, new.model,
                              new.effective_api_base, new.azure_region)
        if new_provider_tuple != old_provider:
            self.provider = self._build_provider(new)

        if new.input_device != old_input_device:
            self.mic.stop()
            self.mic = MicCapture(
                sample_rate=new.sample_rate,
                input_device=new.input_device,
                preroll_sec=new.preroll_sec,
            )
            try:
                self.mic.start()
            except Exception as e:
                self.logger.exception("mic restart failed")
                self.ui_q.put({"state": ERROR, "msg": f"mic: {e}"})

        # autostart
        if sys.platform.startswith("win"):
            currently_enabled = autostart_is_enabled()
            if new.autostart and not currently_enabled:
                autostart_enable(_autostart_target_path())
            elif not new.autostart and currently_enabled:
                autostart_disable()

        self.logger.info("settings applied")

    def open_log(self) -> None:
        log_path = install_root() / "voice2ai.log"
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(log_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_path)])
            else:
                subprocess.Popen(["xdg-open", str(log_path)])
        except Exception:
            self.logger.exception("open_log")

    def open_diagnose(self) -> None:
        if self.tk_root is None:
            return
        self.tk_root.after(0, self._open_diagnose_on_main)

    def _open_diagnose_on_main(self) -> None:
        win = tk.Toplevel(self.tk_root)
        win.title("Diagnostics")
        win.geometry("560x400")
        text = tk.Text(win, wrap="word", font=("Consolas", 9))
        text.pack(fill="both", expand=True, padx=8, pady=8)
        text.insert("end", "running…\n")

        def run():
            results = diagnose(self.settings, self.provider)
            report = format_report(results)
            self.tk_root.after(0, lambda: (text.delete("1.0", "end"),
                                           text.insert("end", report)))

        threading.Thread(target=run, daemon=True).start()

    def quit_app(self) -> None:
        self._quit_requested = True
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        try:
            self.mic.stop()
        except Exception:
            pass
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        if self.tk_root is not None:
            try:
                self.tk_root.after(0, self.tk_root.destroy)
            except Exception:
                pass

    # ── hotkey callbacks ───────────────────────────────────────
    def _on_hotkey_press(self) -> None:
        if self._state != IDLE:
            return
        # Capture the foreground window BEFORE any UI update — this is the
        # target window for the paste. Without this snapshot, the floating
        # widget's update can steal focus and the paste lands in the wrong app.
        self._target_hwnd = get_foreground_window()
        self._record_started = self.mic.begin_record()
        self._state = RECORDING
        self._t0 = time.time()
        self.ui_q.put({"state": RECORDING, "t0": self._t0})
        _audio_cue(800, 60, self.settings.play_audio_cues)

    def _on_hotkey_release(self) -> None:
        if self._state != RECORDING:
            return
        self._state = TRANSCRIBING
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    # ── continuous (VAD) mode ──────────────────────────────────
    def _toggle_continuous_mode(self) -> None:
        """Toggle hands-free VAD mode. F9 → on; F9 again → off."""
        if self._continuous_active:
            self._exit_continuous_mode()
        else:
            self._enter_continuous_mode()

    def _enter_continuous_mode(self) -> None:
        if self._continuous_active:
            return
        self._vad = EnergyVAD(
            config=VADConfig(
                threshold=self.settings.vad_threshold,
                silence_ratio=self.settings.vad_silence_ratio,
                max_zcr=self.settings.vad_max_zcr,
                min_speech_ms=self.settings.vad_min_speech_ms,
                min_silence_ms=self.settings.vad_min_silence_ms,
                sample_rate=self.settings.sample_rate,
            ),
            on_speech_start=self._vad_speech_start,
            on_speech_end=self._vad_speech_end,
        )
        self.mic.set_frame_listener(self._vad.process)
        self._continuous_active = True
        self.logger.info("continuous mode ON (vad threshold=%.4f)", self.settings.vad_threshold)
        self.ui_q.put({"state": IDLE, "msg": "🎙️ continuous mode ON"})
        _audio_cue(1200, 80, self.settings.play_audio_cues)

    def _exit_continuous_mode(self) -> None:
        if not self._continuous_active:
            return
        self.mic.set_frame_listener(None)
        if self._vad is not None:
            self._vad.reset()
            self._vad = None
        self._continuous_active = False
        # If a recording was in progress, finalize it like a normal hotkey release.
        if self._state == RECORDING:
            self._on_hotkey_release()
        self.logger.info("continuous mode OFF")
        self.ui_q.put({"state": IDLE, "msg": "continuous mode OFF"})
        _audio_cue(600, 80, self.settings.play_audio_cues)

    def _vad_speech_start(self) -> None:
        # Runs in audio thread — keep cheap, do not block.
        if self._state != IDLE or not self._continuous_active:
            return
        self._target_hwnd = get_foreground_window()
        self._record_started = self.mic.begin_record()
        self._state = RECORDING
        self._t0 = time.time()
        self.ui_q.put({"state": RECORDING, "t0": self._t0})

    def _vad_speech_end(self) -> None:
        if self._state != RECORDING or not self._continuous_active:
            return
        self._state = TRANSCRIBING
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    def _do_transcribe(self) -> None:
        try:
            audio, duration = self.mic.end_record(self._record_started)
            if audio is None:
                self.ui_q.put({"state": IDLE, "msg": t("status.no_audio")})
                self._state = IDLE
                return
            if duration < 0.30:
                self.ui_q.put({"state": IDLE, "msg": t("status.too_short")})
                self._state = IDLE
                return

            _audio_cue(600, 40, self.settings.play_audio_cues)
            self.ui_q.put({"state": TRANSCRIBING, "duration": duration,
                           "provider": self.settings.provider})

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            try:
                sf.write(wav_path, audio, self.settings.sample_rate)
                result = self.provider.transcribe(wav_path)
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

            if not result.ok:
                self.logger.error("STT error: %s", result.error)
                self.ui_q.put({"state": ERROR, "msg": result.error})
                self._state = IDLE
                return

            text = result.text.strip()
            if not text:
                self.ui_q.put({"state": IDLE, "msg": t("status.empty_result")})
                self._state = IDLE
                return

            if self.settings.paste_after_transcribe:
                paste_to_focus(
                    text,
                    target_hwnd=getattr(self, "_target_hwnd", 0),
                    auto_enter=self.settings.auto_enter_after_paste,
                    smart_paste=self.settings.smart_paste,
                )
                pasted = True
            else:
                copy_to_clipboard(text)
                pasted = False

            _audio_cue(1000, 60, self.settings.play_audio_cues)
            self.ui_q.put({
                "state": DONE, "text": text,
                "latency_ms": result.latency_ms, "pasted": pasted,
            })
            self._state = IDLE
        except Exception as e:
            self.logger.exception("transcribe pipeline")
            self.ui_q.put({"state": ERROR, "msg": f"{type(e).__name__}: {e}"})
            self._state = IDLE


def _autostart_target_path() -> str:
    """If frozen → exe path. Else → pythonw start.bat path so launching is silent."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(install_root() / "start.bat")


def run() -> int:
    raw_settings = load_settings()
    log_path = _setup_logging(raw_settings)
    log = logging.getLogger("voice2ai.main")
    log.info("voice2ai v%s start | log=%s", __version__, log_path)

    set_language(raw_settings.language)

    # First-run wizard if no api key
    settings = raw_settings
    if not settings.api_key:
        log.info("no api key — running wizard")
        result = Wizard(settings).run()
        if result is None:
            log.info("wizard cancelled — exit")
            return 1
        settings = result
        set_language(settings.language)

    app = Voice2CC(settings)

    # Open mic
    try:
        app.mic.start()
        log.info("mic device: %s", app.mic.device_name())
    except Exception as e:
        log.exception("mic start failed")
        # Show a tk error dialog so users without a console see it
        root = tk.Tk(); root.withdraw()
        from tkinter import messagebox
        messagebox.showerror("voice2ai", f"Microphone failed: {e}\n\nSee voice2ai.log.")
        root.destroy()
        return 2

    # Hotkey listeners (push-to-talk + continuous-mode toggle)
    try:
        app.hotkeys.start()
        app.continuous_toggle.start()
    except Exception:
        log.exception("hotkey listener failed")
        return 3

    # Auto-enter continuous mode at launch if configured
    if settings.continuous_mode:
        app._toggle_continuous_mode()

    # tk root
    root = tk.Tk()
    if not settings.show_floating_widget:
        root.withdraw()
    app.tk_root = root

    if settings.show_floating_widget:
        app.widget = FloatingPanel(root, app, app.ui_q)
        app.ui_q.put({"state": IDLE, "msg": t("status.ready", hotkey=hotkey_label(settings.hotkey))})

    # Tray
    app.tray = make_tray(
        on_show=app.show_widget,
        on_hide=app.hide_widget,
        on_settings=app.open_settings,
        on_diagnose=app.open_diagnose,
        on_open_log=app.open_log,
        on_quit=app.quit_app,
        is_widget_visible=app.is_widget_visible,
    )
    try:
        app.tray.start()
    except Exception:
        log.exception("tray start failed")

    # Apply autostart on first run if requested
    if settings.autostart and sys.platform.startswith("win") and not autostart_is_enabled():
        autostart_enable(_autostart_target_path())

    try:
        root.mainloop()
    finally:
        log.info("voice2ai exit")
        try:
            app.mic.stop()
        except Exception:
            pass
        try:
            app.hotkeys.stop()
        except Exception:
            pass
        try:
            if app.tray is not None:
                app.tray.stop()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(run())
