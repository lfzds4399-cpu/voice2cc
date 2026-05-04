"""config.py — user settings loaded from config.env (legacy) and runtime overrides.

Settings precedence (highest first):
  1. CLI flags (future)
  2. Runtime overrides written via UI (settings dialog persists to config.env)
  3. config.env in the install dir
  4. Hard-coded defaults below

Backward-compatible with v0.1's config.env (SILICONFLOW_API_KEY / STT_MODEL).
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, dotenv_values

logger = logging.getLogger("voice2cc.config")


def install_root() -> Path:
    """Return the directory that holds config.env / voice2cc.log.

    When frozen by PyInstaller, sys.frozen is set and we use the exe directory.
    Otherwise it's the package install root (3 levels up from this file).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # src/voice2cc/config.py → src/voice2cc → src → install root
    return Path(__file__).resolve().parents[2]


CONFIG_PATH = install_root() / "config.env"


@dataclass
class Settings:
    # ── STT provider ────────────────────────────────────────────
    provider: str = "siliconflow"            # siliconflow | openai | groq | azure
    api_key: str = ""                        # primary key for the chosen provider
    model: str = "FunAudioLLM/SenseVoiceSmall"
    api_base: str = ""                       # optional override; empty = provider default
    azure_region: str = ""                   # azure-only

    # ── Hotkey ──────────────────────────────────────────────────
    hotkey: str = "ctrl+shift+space"         # human-readable, parsed by hotkey.py

    # ── Audio ───────────────────────────────────────────────────
    sample_rate: int = 16000
    input_device: int = -1                   # -1 = system default
    preroll_sec: float = 0.30                # ring buffer before hotkey down

    # ── UX ──────────────────────────────────────────────────────
    language: str = "auto"                   # auto | en | zh
    autostart: bool = False                  # Windows autostart on login
    show_floating_widget: bool = True
    play_audio_cues: bool = True
    paste_after_transcribe: bool = True      # if False, only copies to clipboard

    # ── Diagnostics ─────────────────────────────────────────────
    log_level: str = "INFO"                  # DEBUG | INFO | WARNING | ERROR

    @property
    def effective_api_base(self) -> str:
        return self.api_base or _DEFAULT_API_BASE.get(self.provider, "")


_DEFAULT_API_BASE = {
    "siliconflow": "https://api.siliconflow.cn/v1",
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    # azure is constructed at request time from region
}


# ── Legacy config.env keys (v0.1 / v0.2) ─────────────────────────
_LEGACY_KEY_MAP = {
    "SILICONFLOW_API_KEY": ("provider", "siliconflow", "api_key"),
    "OPENAI_API_KEY": ("provider", "openai", "api_key"),
    "GROQ_API_KEY": ("provider", "groq", "api_key"),
    "AZURE_API_KEY": ("provider", "azure", "api_key"),
    "STT_MODEL": (None, None, "model"),
    "API_BASE": (None, None, "api_base"),
    "AZURE_REGION": (None, None, "azure_region"),
    "VOICE2CC_HOTKEY": (None, None, "hotkey"),
    "VOICE2CC_LANGUAGE": (None, None, "language"),
    "VOICE2CC_AUTOSTART": (None, None, "autostart"),
    "VOICE2CC_INPUT_DEVICE": (None, None, "input_device"),
    "VOICE2CC_PROVIDER": (None, None, "provider"),
    "VOICE2CC_LOG_LEVEL": (None, None, "log_level"),
    "VOICE2CC_SHOW_WIDGET": (None, None, "show_floating_widget"),
    "VOICE2CC_PLAY_CUES": (None, None, "play_audio_cues"),
    "VOICE2CC_PASTE_AFTER": (None, None, "paste_after_transcribe"),
}


def _coerce(field_name: str, raw: str):
    """Coerce env-string to typed value based on Settings dataclass."""
    if raw is None:
        return None
    if field_name in ("autostart", "show_floating_widget", "play_audio_cues",
                      "paste_after_transcribe"):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if field_name in ("sample_rate", "input_device"):
        try:
            return int(raw)
        except ValueError:
            return None
    if field_name in ("preroll_sec",):
        try:
            return float(raw)
        except ValueError:
            return None
    return raw.strip()


def load() -> Settings:
    """Load settings from config.env. Missing file → defaults. Always returns a valid Settings."""
    s = Settings()
    if not CONFIG_PATH.exists():
        logger.info("config.env not found at %s — using defaults", CONFIG_PATH)
        return s

    load_dotenv(CONFIG_PATH, override=True)
    raw = dotenv_values(CONFIG_PATH)

    # 1) Map legacy keys onto Settings
    inferred_provider = None
    for legacy_key, (provider_field, provider_value, dest_field) in _LEGACY_KEY_MAP.items():
        if legacy_key in raw and raw[legacy_key]:
            v = _coerce(dest_field, raw[legacy_key])
            if v is None:
                continue
            setattr(s, dest_field, v)
            if provider_field == "provider" and not inferred_provider:
                # If user only set SILICONFLOW_API_KEY, infer provider=siliconflow
                inferred_provider = provider_value
    if inferred_provider and not raw.get("VOICE2CC_PROVIDER"):
        s.provider = inferred_provider

    return s


def save(s: Settings) -> None:
    """Persist Settings back to config.env. Keeps comments minimal — overwrites cleanly.

    Writing back atomically is important on Windows where text editors may have the file open;
    we write to a temp sibling and replace.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".env.tmp")

    # We persist the canonical VOICE2CC_* keys, plus provider-specific *_API_KEY for clarity.
    lines: list[str] = [
        "# voice2cc config — written by Settings dialog. Edits here are read on next launch.",
        "# https://github.com/lfzds4399-cpu/voice2cc",
        "",
        f"VOICE2CC_PROVIDER={s.provider}",
        f"STT_MODEL={s.model}",
        f"API_BASE={s.api_base}",
        "",
        "# Provider key — set the one matching VOICE2CC_PROVIDER above",
        f"SILICONFLOW_API_KEY={s.api_key if s.provider == 'siliconflow' else ''}",
        f"OPENAI_API_KEY={s.api_key if s.provider == 'openai' else ''}",
        f"GROQ_API_KEY={s.api_key if s.provider == 'groq' else ''}",
        f"AZURE_API_KEY={s.api_key if s.provider == 'azure' else ''}",
        f"AZURE_REGION={s.azure_region}",
        "",
        "# Hotkey — human-readable, e.g. ctrl+shift+space, ctrl+alt+v, f8",
        f"VOICE2CC_HOTKEY={s.hotkey}",
        "",
        "# UX",
        f"VOICE2CC_LANGUAGE={s.language}",
        f"VOICE2CC_AUTOSTART={'true' if s.autostart else 'false'}",
        f"VOICE2CC_INPUT_DEVICE={s.input_device}",
        f"VOICE2CC_SHOW_WIDGET={'true' if s.show_floating_widget else 'false'}",
        f"VOICE2CC_PLAY_CUES={'true' if s.play_audio_cues else 'false'}",
        f"VOICE2CC_PASTE_AFTER={'true' if s.paste_after_transcribe else 'false'}",
        f"VOICE2CC_LOG_LEVEL={s.log_level}",
    ]

    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)
    logger.info("config saved to %s", CONFIG_PATH)


def asdict_safe(s: Settings) -> dict:
    """Return Settings as dict but redact api_key for logging."""
    d = asdict(s)
    if d.get("api_key"):
        d["api_key"] = d["api_key"][:6] + "****" + d["api_key"][-4:] if len(d["api_key"]) > 12 else "****"
    return d
