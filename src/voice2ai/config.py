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

logger = logging.getLogger("voice2ai.config")


def install_root() -> Path:
    """Return the directory that holds config.env / voice2ai.log.

    When frozen by PyInstaller, sys.frozen is set and we use the exe directory.
    Otherwise it's the package install root (3 levels up from this file).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # src/voice2ai/config.py → src/voice2ai → src → install root
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
    hotkey: str = "ctrl+shift+space"         # push-to-talk hotkey (hold to record)
    continuous_toggle_hotkey: str = "f9"     # toggle hands-free continuous (VAD) mode

    # ── Continuous (VAD) mode ──────────────────────────────────
    continuous_mode: bool = False            # start in continuous mode at launch
    vad_threshold: float = 0.015             # RMS energy threshold to ENTER speech
    vad_silence_ratio: float = 0.4           # silence floor = threshold * ratio (hysteresis)
    vad_max_zcr: float = 0.18                # max zero-crossing rate (filters breath/wind)
    vad_min_speech_ms: int = 250             # min continuous speech to start recording
    vad_min_silence_ms: int = 1500           # silence duration that ends an utterance

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
    auto_enter_after_paste: bool = True      # auto press Enter after paste (zero-touch send)
    smart_paste: bool = True                 # detect VS Code/Terminal → use Ctrl+Shift+V

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
    "AZURE_SPEECH_KEY": ("provider", "azure", "api_key"),
    "STT_MODEL": (None, None, "model"),
    "SILICONFLOW_MODEL": ("provider", "siliconflow", "model"),
    "OPENAI_MODEL": ("provider", "openai", "model"),
    "GROQ_MODEL": ("provider", "groq", "model"),
    "AZURE_MODEL": ("provider", "azure", "model"),
    "API_BASE": (None, None, "api_base"),
    "AZURE_REGION": (None, None, "azure_region"),
    "AZURE_SPEECH_REGION": (None, None, "azure_region"),
    "VOICE2AI_HOTKEY": (None, None, "hotkey"),
    "VOICE2AI_LANGUAGE": (None, None, "language"),
    "VOICE2AI_AUTOSTART": (None, None, "autostart"),
    "VOICE2AI_INPUT_DEVICE": (None, None, "input_device"),
    "VOICE2AI_PROVIDER": (None, None, "provider"),
    "VOICE2AI_LOG_LEVEL": (None, None, "log_level"),
    "VOICE2AI_SHOW_WIDGET": (None, None, "show_floating_widget"),
    "VOICE2AI_PLAY_CUES": (None, None, "play_audio_cues"),
    "VOICE2AI_PASTE_AFTER": (None, None, "paste_after_transcribe"),
    "VOICE2AI_AUTO_ENTER_AFTER_PASTE": (None, None, "auto_enter_after_paste"),
    "VOICE2AI_SMART_PASTE": (None, None, "smart_paste"),
    "VOICE2AI_CONTINUOUS_MODE": (None, None, "continuous_mode"),
    "VOICE2AI_CONTINUOUS_TOGGLE_HOTKEY": (None, None, "continuous_toggle_hotkey"),
    "VOICE2AI_VAD_THRESHOLD": (None, None, "vad_threshold"),
    "VOICE2AI_VAD_SILENCE_RATIO": (None, None, "vad_silence_ratio"),
    "VOICE2AI_VAD_MAX_ZCR": (None, None, "vad_max_zcr"),
    "VOICE2AI_VAD_MIN_SPEECH_MS": (None, None, "vad_min_speech_ms"),
    "VOICE2AI_VAD_MIN_SILENCE_MS": (None, None, "vad_min_silence_ms"),
}

# Backwards-compat: VOICE2CC_* keys from voice2cc 0.4.x are still accepted as
# deprecated aliases of VOICE2AI_*. Existing config.env files keep working.
_LEGACY_KEY_MAP.update({
    k.replace("VOICE2AI_", "VOICE2CC_"): v
    for k, v in list(_LEGACY_KEY_MAP.items())
    if k.startswith("VOICE2AI_")
})


def _coerce(field_name: str, raw: str):
    """Coerce env-string to typed value based on Settings dataclass."""
    if raw is None:
        return None
    if field_name in ("autostart", "show_floating_widget", "play_audio_cues",
                      "paste_after_transcribe", "auto_enter_after_paste",
                      "smart_paste", "continuous_mode"):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if field_name in ("sample_rate", "input_device",
                      "vad_min_speech_ms", "vad_min_silence_ms"):
        try:
            return int(raw)
        except ValueError:
            return None
    if field_name in ("preroll_sec", "vad_threshold", "vad_max_zcr", "vad_silence_ratio"):
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
    explicit_provider = (raw.get("VOICE2AI_PROVIDER") or raw.get("VOICE2CC_PROVIDER") or "").strip()
    for legacy_key, (provider_field, provider_value, dest_field) in _LEGACY_KEY_MAP.items():
        if legacy_key in raw and raw[legacy_key]:
            if (
                provider_field == "provider"
                and explicit_provider
                and provider_value != explicit_provider
                and dest_field in ("api_key", "model")
            ):
                continue
            v = _coerce(dest_field, raw[legacy_key])
            if v is None:
                continue
            setattr(s, dest_field, v)
            if provider_field == "provider" and not inferred_provider:
                # If user only set SILICONFLOW_API_KEY, infer provider=siliconflow
                inferred_provider = provider_value
    if inferred_provider and not raw.get("VOICE2AI_PROVIDER"):
        s.provider = inferred_provider

    return s


def save(s: Settings) -> None:
    """Persist Settings back to config.env. Keeps comments minimal — overwrites cleanly.

    Writing back atomically is important on Windows where text editors may have the file open;
    we write to a temp sibling and replace.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".env.tmp")

    # We persist the canonical VOICE2AI_* keys, plus provider-specific *_API_KEY for clarity.
    lines: list[str] = [
        "# voice2ai config — written by Settings dialog. Edits here are read on next launch.",
        "# https://github.com/lfzds4399-cpu/voice2ai",
        "",
        f"VOICE2AI_PROVIDER={s.provider}",
        f"STT_MODEL={s.model}",
        f"API_BASE={s.api_base}",
        "",
        "# Provider key — set the one matching VOICE2AI_PROVIDER above",
        f"SILICONFLOW_API_KEY={s.api_key if s.provider == 'siliconflow' else ''}",
        f"OPENAI_API_KEY={s.api_key if s.provider == 'openai' else ''}",
        f"GROQ_API_KEY={s.api_key if s.provider == 'groq' else ''}",
        f"AZURE_API_KEY={s.api_key if s.provider == 'azure' else ''}",
        f"AZURE_REGION={s.azure_region}",
        "",
        "# Hotkey — human-readable, e.g. ctrl+shift+space, ctrl+alt+v, f8",
        f"VOICE2AI_HOTKEY={s.hotkey}",
        f"VOICE2AI_CONTINUOUS_TOGGLE_HOTKEY={s.continuous_toggle_hotkey}",
        "",
        "# UX",
        f"VOICE2AI_LANGUAGE={s.language}",
        f"VOICE2AI_AUTOSTART={'true' if s.autostart else 'false'}",
        f"VOICE2AI_INPUT_DEVICE={s.input_device}",
        f"VOICE2AI_SHOW_WIDGET={'true' if s.show_floating_widget else 'false'}",
        f"VOICE2AI_PLAY_CUES={'true' if s.play_audio_cues else 'false'}",
        f"VOICE2AI_PASTE_AFTER={'true' if s.paste_after_transcribe else 'false'}",
        f"VOICE2AI_AUTO_ENTER_AFTER_PASTE={'true' if s.auto_enter_after_paste else 'false'}",
        f"VOICE2AI_SMART_PASTE={'true' if s.smart_paste else 'false'}",
        f"VOICE2AI_CONTINUOUS_MODE={'true' if s.continuous_mode else 'false'}",
        f"VOICE2AI_VAD_THRESHOLD={s.vad_threshold}",
        f"VOICE2AI_VAD_SILENCE_RATIO={s.vad_silence_ratio}",
        f"VOICE2AI_VAD_MAX_ZCR={s.vad_max_zcr}",
        f"VOICE2AI_VAD_MIN_SPEECH_MS={s.vad_min_speech_ms}",
        f"VOICE2AI_VAD_MIN_SILENCE_MS={s.vad_min_silence_ms}",
        f"VOICE2AI_LOG_LEVEL={s.log_level}",
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
