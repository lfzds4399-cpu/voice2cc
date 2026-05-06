"""wizard.py — first-run setup dialog.

Shown when config.env is absent or the API key field is empty. Lets a non-developer
pick provider, paste key, test, and save — without ever opening config.env in an editor.
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Optional

from ..config import Settings, save as save_settings
from ..i18n import t
from ..providers import DEFAULT_MODELS, PROVIDER_KEY_HELP_URL, get_provider

logger = logging.getLogger("voice2ai.ui.wizard")


def _provider_hint(name: str) -> str:
    return t(f"wizard.provider_hint_{name}")


class Wizard:
    """Modal-ish setup window. Returns the new Settings via .result on close, or None on cancel."""

    PROVIDERS = ["siliconflow", "openai", "groq", "azure"]

    def __init__(self, initial: Settings):
        self.result: Optional[Settings] = None
        self._initial = initial

        self.win = tk.Tk()
        self.win.title(t("wizard.title"))
        self.win.geometry("520x420")
        self.win.resizable(False, False)
        self._build()

    def _build(self):
        pad = {"padx": 16, "pady": 6}
        title = tk.Label(self.win, text=t("wizard.welcome"),
                         font=("Microsoft YaHei UI", 11, "bold"), wraplength=480, justify="left")
        title.pack(anchor="w", padx=16, pady=(16, 6))

        # provider
        row = tk.Frame(self.win); row.pack(fill="x", **pad)
        tk.Label(row, text=t("wizard.provider"), width=12, anchor="w").pack(side="left")
        self.provider_var = tk.StringVar(value=self._initial.provider)
        self.provider_combo = ttk.Combobox(
            row, textvariable=self.provider_var, values=self.PROVIDERS, state="readonly", width=18,
        )
        self.provider_combo.pack(side="left")
        self.provider_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_provider_change())

        self.hint_lbl = tk.Label(self.win, text=_provider_hint(self._initial.provider), fg="#666")
        self.hint_lbl.pack(anchor="w", padx=16)

        # api key
        row = tk.Frame(self.win); row.pack(fill="x", **pad)
        tk.Label(row, text=t("wizard.api_key"), width=12, anchor="w").pack(side="left")
        self.key_var = tk.StringVar(value=self._initial.api_key)
        self.key_entry = tk.Entry(row, textvariable=self.key_var, show="•", width=40)
        self.key_entry.pack(side="left", fill="x", expand=True)

        link_row = tk.Frame(self.win); link_row.pack(fill="x", padx=16)
        self.link_lbl = tk.Label(link_row, text="", fg="#1f6feb", cursor="hand2", anchor="w")
        self.link_lbl.pack(side="left")
        self.link_lbl.bind("<Button-1>", lambda _e: self._open_link())

        # model
        row = tk.Frame(self.win); row.pack(fill="x", **pad)
        tk.Label(row, text=t("wizard.model"), width=12, anchor="w").pack(side="left")
        self.model_var = tk.StringVar(value=self._initial.model)
        self.model_combo = ttk.Combobox(row, textvariable=self.model_var, width=38)
        self.model_combo.pack(side="left", fill="x", expand=True)

        # azure region (only enabled when provider=azure)
        row = tk.Frame(self.win); row.pack(fill="x", **pad)
        tk.Label(row, text="Azure region", width=12, anchor="w").pack(side="left")
        self.region_var = tk.StringVar(value=self._initial.azure_region)
        self.region_entry = tk.Entry(row, textvariable=self.region_var, width=38)
        self.region_entry.pack(side="left", fill="x", expand=True)

        # status / test
        self.status_lbl = tk.Label(self.win, text="", fg="#444", wraplength=480, justify="left")
        self.status_lbl.pack(fill="x", padx=16, pady=(12, 4))

        # buttons
        btn_row = tk.Frame(self.win); btn_row.pack(side="bottom", fill="x", padx=16, pady=12)
        tk.Button(btn_row, text=t("wizard.cancel_button"), width=10,
                  command=self._cancel).pack(side="right", padx=4)
        tk.Button(btn_row, text=t("wizard.save_button"), width=14,
                  command=self._save).pack(side="right", padx=4)
        tk.Button(btn_row, text=t("wizard.test_button"), width=14,
                  command=self._test).pack(side="right", padx=4)

        self._on_provider_change()

    def _on_provider_change(self):
        provider = self.provider_var.get()
        self.hint_lbl.config(text=_provider_hint(provider))
        models = DEFAULT_MODELS.get(provider, [])
        self.model_combo["values"] = models
        if self.model_var.get() not in models and models:
            self.model_var.set(models[0])
        url = PROVIDER_KEY_HELP_URL.get(provider, "")
        self.link_lbl.config(text=f"→ {url}")
        self.region_entry.config(state="normal" if provider == "azure" else "disabled")

    def _open_link(self):
        url = PROVIDER_KEY_HELP_URL.get(self.provider_var.get(), "")
        if url:
            webbrowser.open(url)

    def _build_settings(self) -> Settings:
        s = Settings(**{**self._initial.__dict__})  # copy
        s.provider = self.provider_var.get()
        s.api_key = self.key_var.get().strip()
        s.model = self.model_var.get().strip()
        s.azure_region = self.region_var.get().strip()
        return s

    def _test(self):
        s = self._build_settings()
        if not s.api_key:
            self.status_lbl.config(text="⚠ no api key", fg="#b00")
            return
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
                    msg = t("diag.api_http", status="?", body=r.error or "unknown")
                    color = "#b00"
            except Exception as e:
                msg = t("diag.api_exception", err=f"{type(e).__name__}: {e}")
                color = "#b00"
            self.win.after(0, lambda: self.status_lbl.config(text=msg, fg=color))

        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        s = self._build_settings()
        if not s.api_key:
            self.status_lbl.config(text="⚠ api key required", fg="#b00")
            return
        save_settings(s)
        self.result = s
        self.win.destroy()

    def _cancel(self):
        self.result = None
        self.win.destroy()

    def run(self) -> Optional[Settings]:
        self.win.mainloop()
        return self.result
