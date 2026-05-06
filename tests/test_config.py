"""tests/test_config.py — config save/load roundtrip + legacy v0.1 key migration."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Point CONFIG_PATH at a tmp file before importing config."""
    cfg = tmp_path / "config.env"
    # patch install_root so config writes to tmp
    import voice2cc.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "CONFIG_PATH", cfg)
    return cfg


def test_load_missing_returns_defaults(tmp_config):
    from voice2cc.config import load
    s = load()
    assert s.provider == "siliconflow"
    assert s.api_key == ""
    assert s.hotkey == "ctrl+shift+space"


def test_legacy_siliconflow_key_inferred(tmp_config):
    tmp_config.write_text("SILICONFLOW_API_KEY=sk-foo\nSTT_MODEL=FunAudioLLM/SenseVoiceSmall\n",
                          encoding="utf-8")
    from voice2cc.config import load
    s = load()
    assert s.provider == "siliconflow"
    assert s.api_key == "sk-foo"
    assert s.model == "FunAudioLLM/SenseVoiceSmall"


def test_explicit_provider_overrides_inferred(tmp_config):
    tmp_config.write_text(
        "SILICONFLOW_API_KEY=sk-foo\n"
        "OPENAI_API_KEY=sk-bar\n"
        "VOICE2CC_PROVIDER=openai\n"
        "STT_MODEL=whisper-1\n",
        encoding="utf-8",
    )
    from voice2cc.config import load
    s = load()
    assert s.provider == "openai"


def test_save_roundtrip(tmp_config):
    from voice2cc.config import Settings, load, save
    orig = Settings(
        provider="groq", api_key="gsk-test123", model="whisper-large-v3",
        hotkey="ctrl+alt+v", language="zh", autostart=True, paste_after_transcribe=False,
    )
    save(orig)
    loaded = load()
    assert loaded.provider == "groq"
    assert loaded.api_key == "gsk-test123"
    assert loaded.model == "whisper-large-v3"
    assert loaded.hotkey == "ctrl+alt+v"
    assert loaded.language == "zh"
    assert loaded.autostart is True
    assert loaded.paste_after_transcribe is False


def test_effective_api_base_falls_back_to_provider_default(tmp_config):
    from voice2cc.config import Settings
    s = Settings(provider="openai")
    assert "openai.com" in s.effective_api_base


def test_asdict_safe_redacts_key(tmp_config):
    from voice2cc.config import Settings, asdict_safe
    # NOTE: this is a test-only mock value — not a real API key. The "sk-" prefix
    # was triggering naive secret-scanners. Renamed to make the fakeness obvious.
    s = Settings(api_key="dummy-mock-test-api-key-not-real-1234")
    d = asdict_safe(s)
    assert "dummy-mock-test-api-key-not-real-1234" not in d["api_key"]
    assert "****" in d["api_key"]
