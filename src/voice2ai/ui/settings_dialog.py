"""settings_dialog.py — full settings panel reachable from tray menu.

Tabs:
  - Provider — same as wizard (provider/key/model/test)
  - Audio    — input device picker + test record
  - Hotkey   — record a new hotkey by pressing it
  - General  — language, autostart, widget visible, audio cues, paste mode
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..audio import list_input_devices
from ..config import Settings, save as save_settings
from ..hotkey import hotkey_label
from ..i18n import t
from ..providers import DEFAULT_MODELS, PROVIDER_KEY_HELP_URL, get_provider

logger = logging.getLogger("voice2ai.ui.settings")


class SettingsDialog:
    PROVIDERS = ["siliconflow", "openai", "groq", "azure"]

    def __init__(self, initial: Settings, parent: Optional[tk.Tk] = None):
        self.result: Optional[Settings] = None
        self._initial = initial

        if parent is None:
            self.win = tk.Tk()
            self._owns_root = True
        else:
            self.win = tk.Toplevel(parent)
            self._owns_root = False

        self.win.title(t("settings.title"))
        self.win.geometry("560x460")
        self.win.resizable(False, False)
        self._build()

    def _build(self):
        nb = ttk.Notebook(self.win)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_provider_tab(nb)
        self._build_audio_tab(nb)
        self._build_hotkey_tab(nb)
        self._build_general_tab(nb)

        btn_row = tk.Frame(self.win); btn_row.pack(fill="x", padx=10, pady=8)
        tk.Button(btn_row, text=t("settings.cancel"), width=10,
                  command=self._cancel).pack(side="right", padx=4)
        tk.Button(btn_row, text=t("settings.save"), width=12,
                  command=self._save).pack(side="right", padx=4)
        self.status_lbl = tk.Label(btn_row, text="", fg="#444", anchor="w")
        self.status_lbl.pack(side="left", fill="x", expand=True)

    # ── provider tab ────────────────────────────────────────────
    def _build_provider_tab(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=t("settings.tab_provider"))

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=8)
        tk.Label(row, text=t("wizard.provider"), width=14, anchor="w").pack(side="left")
        self.provider_var = tk.StringVar(value=self._initial.provider)
        ttk.Combobox(row, textvariable=self.provider_var, values=self.PROVIDERS,
                     state="readonly", width=20).pack(side="left")
        self.provider_var.trace_add("write", lambda *_: self._refresh_models())

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=4)
        tk.Label(row, text=t("wizard.api_key"), width=14, anchor="w").pack(side="left")
        self.key_var = tk.StringVar(value=self._initial.api_key)
        tk.Entry(row, textvariable=self.key_var, show="•", width=40).pack(side="left", fill="x", expand=True)

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=4)
        tk.Label(row, text=t("wizard.model"), width=14, anchor="w").pack(side="left")
        self.model_var = tk.StringVar(value=self._initial.model)
        self.model_combo = ttk.Combobox(row, textvariable=self.model_var, width=38)
        self.model_combo.pack(side="left", fill="x", expand=True)

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=4)
        tk.Label(row, text="Azure region", width=14, anchor="w").pack(side="left")
        self.region_var = tk.StringVar(value=self._initial.azure_region)
        self.region_entry = tk.Entry(row, textvariable=self.region_var, width=40)
        self.region_entry.pack(side="left", fill="x", expand=True)

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=12)
        tk.Button(row, text=t("wizard.test_button"), command=self._test_provider).pack(side="left")

        self._refresh_models()

    def _refresh_models(self):
        provider = self.provider_var.get()
        models = DEFAULT_MODELS.get(provider, [])
        self.model_combo["values"] = models
        if self.model_var.get() not in models and models:
            self.model_var.set(models[0])
        try:
            self.region_entry.config(state="normal" if provider == "azure" else "disabled")
        except tk.TclError:
            pass

    def _test_provider(self):
        s = self._collect()
        self.status_lbl.config(text=t("wizard.testing"), fg="#444")

        def run():
            try:
                cls = get_provider(s.provider)
                p = cls(api_key=s.api_key, model=s.model, api_base=s.effective_api_base,
                        azure_region=s.azure_region)
                r = p.health_check()
                if r.ok:
                    msg = t("diag.api_ok", model=s.model) + f" · {r.latency_ms}ms"
                    color = "#0a0"
                else:
                    msg = r.error or "?"
                    color = "#b00"
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                color = "#b00"
            self.win.after(0, lambda: self.status_lbl.config(text=msg, fg=color))

        threading.Thread(target=run, daemon=True).start()

    # ── audio tab ───────────────────────────────────────────────
    def _build_audio_tab(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=t("settings.tab_audio"))

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=8)
        tk.Label(row, text=t("settings.input_device"), width=14, anchor="w").pack(side="left")

        devices = list_input_devices()
        self._device_index_map = {f"[{d.index}] {d.name}": d.index for d in devices}
        self._device_index_map["(default)"] = -1

        current_label = "(default)"
        for label, idx in self._device_index_map.items():
            if idx == self._initial.input_device:
                current_label = label
                break

        self.device_var = tk.StringVar(value=current_label)
        ttk.Combobox(row, textvariable=self.device_var,
                     values=list(self._device_index_map.keys()),
                     state="readonly", width=42).pack(side="left", fill="x", expand=True)

        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=8)
        tk.Button(row, text=t("settings.test_record"), command=self._test_record).pack(side="left")
        self.audio_status = tk.Label(row, text="", fg="#444")
        self.audio_status.pack(side="left", padx=8)

    def _test_record(self):
        self.audio_status.config(text="rec 3s…", fg="#444")

        def run():
            import tempfile, time
            import numpy as np
            import sounddevice as sd
            try:
                idx = self._device_index_map.get(self.device_var.get(), -1)
                device = None if idx < 0 else idx
                rec = sd.rec(int(3 * 16000), samplerate=16000, channels=1,
                             dtype="float32", device=device)
                sd.wait()
                rms = float(np.sqrt(np.mean(rec ** 2)))
                msg = f"OK · rms={rms:.4f}" if rms > 1e-4 else f"silent · rms={rms:.4f}"
                color = "#0a0" if rms > 1e-4 else "#b08000"
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                color = "#b00"
            self.win.after(0, lambda: self.audio_status.config(text=msg, fg=color))

        threading.Thread(target=run, daemon=True).start()

    # ── hotkey tab ──────────────────────────────────────────────
    def _build_hotkey_tab(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=t("settings.tab_hotkey"))

        self.hotkey_value = tk.StringVar(value=self._initial.hotkey)
        cur = tk.Label(f, text=t("settings.hotkey_current", hotkey=hotkey_label(self._initial.hotkey)),
                       font=("Consolas", 11))
        cur.pack(padx=12, pady=20)
        self._hotkey_label = cur

        self.record_btn = tk.Button(f, text=t("settings.hotkey_record"), command=self._start_hotkey_record)
        self.record_btn.pack()

        self.recording_lbl = tk.Label(f, text="", fg="#666")
        self.recording_lbl.pack(pady=8)

        # quick presets
        presets = ["ctrl+shift+space", "ctrl+alt+v", "ctrl+`", "f8", "f9", "right ctrl"]
        preset_row = tk.Frame(f); preset_row.pack(pady=14)
        tk.Label(preset_row, text="Presets:", fg="#666").pack(side="left", padx=4)
        for p in presets:
            tk.Button(preset_row, text=p, command=lambda x=p: self._set_hotkey(x)).pack(side="left", padx=2)

    def _set_hotkey(self, spec: str):
        self.hotkey_value.set(spec)
        self._hotkey_label.config(
            text=t("settings.hotkey_current", hotkey=hotkey_label(spec))
        )

    def _start_hotkey_record(self):
        from pynput import keyboard
        self.recording_lbl.config(text="…")
        captured: set = set()

        def on_press(key):
            try:
                if isinstance(key, keyboard.Key):
                    name = str(key).replace("Key.", "").replace("_l", "").replace("_r", "")
                    captured.add(name)
                elif hasattr(key, "char") and key.char:
                    captured.add(key.char.lower())
            except Exception:
                pass

        def on_release(key):
            # capture once any release happens
            try:
                listener.stop()
            except Exception:
                pass

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        def wait():
            listener.join(timeout=8.0)
            if captured:
                spec = "+".join(sorted(captured, key=lambda s: (len(s) > 1, s)))
                self.win.after(0, lambda: self._set_hotkey(spec))
                self.win.after(0, lambda: self.recording_lbl.config(text="captured"))
            else:
                self.win.after(0, lambda: self.recording_lbl.config(text="(no keys)"))

        threading.Thread(target=wait, daemon=True).start()

    # ── general tab ─────────────────────────────────────────────
    def _build_general_tab(self, nb):
        f = ttk.Frame(nb); nb.add(f, text=t("settings.tab_general"))

        # language
        row = tk.Frame(f); row.pack(fill="x", padx=12, pady=8)
        tk.Label(row, text=t("settings.language"), width=14, anchor="w").pack(side="left")
        self.lang_var = tk.StringVar(value=self._initial.language)
        ttk.Combobox(row, textvariable=self.lang_var,
                     values=["auto", "en", "zh"], state="readonly", width=18).pack(side="left")

        # checkboxes
        self.autostart_var = tk.BooleanVar(value=self._initial.autostart)
        tk.Checkbutton(f, text=t("settings.autostart"), variable=self.autostart_var,
                       anchor="w").pack(fill="x", padx=12, pady=2)

        self.widget_var = tk.BooleanVar(value=self._initial.show_floating_widget)
        tk.Checkbutton(f, text=t("settings.show_widget"), variable=self.widget_var,
                       anchor="w").pack(fill="x", padx=12, pady=2)

        self.cues_var = tk.BooleanVar(value=self._initial.play_audio_cues)
        tk.Checkbutton(f, text=t("settings.play_cues"), variable=self.cues_var,
                       anchor="w").pack(fill="x", padx=12, pady=2)

        self.paste_var = tk.BooleanVar(value=self._initial.paste_after_transcribe)
        tk.Checkbutton(f, text=t("settings.paste_mode"), variable=self.paste_var,
                       anchor="w").pack(fill="x", padx=12, pady=2)

    def _collect(self) -> Settings:
        s = Settings(**{**self._initial.__dict__})
        s.provider = self.provider_var.get()
        s.api_key = self.key_var.get().strip()
        s.model = self.model_var.get().strip()
        s.azure_region = self.region_var.get().strip()
        s.input_device = self._device_index_map.get(self.device_var.get(), -1)
        s.hotkey = self.hotkey_value.get()
        s.language = self.lang_var.get()
        s.autostart = bool(self.autostart_var.get())
        s.show_floating_widget = bool(self.widget_var.get())
        s.play_audio_cues = bool(self.cues_var.get())
        s.paste_after_transcribe = bool(self.paste_var.get())
        return s

    def _save(self):
        s = self._collect()
        save_settings(s)
        self.result = s
        self.win.destroy()

    def _cancel(self):
        self.win.destroy()

    def run(self) -> Optional[Settings]:
        if self._owns_root:
            self.win.mainloop()
        else:
            self.win.wait_window()
        return self.result
