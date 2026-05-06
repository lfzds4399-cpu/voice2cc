"""tests/test_providers.py — provider factory + http stub for transcribe()."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from voice2ai.providers import DEFAULT_MODELS, PROVIDERS, get_provider
from voice2ai.providers.base import clean_response_text


def test_registry_has_four_providers():
    assert set(PROVIDERS) == {"siliconflow", "openai", "groq", "azure"}


def test_get_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_provider("doesnotexist")


def test_default_models_per_provider():
    for name in PROVIDERS:
        assert name in DEFAULT_MODELS
        assert len(DEFAULT_MODELS[name]) >= 1


def test_clean_response_strips_sensevoice_tokens():
    raw = "<|zh|><|HAPPY|>你好世界 "
    assert clean_response_text(raw) == "你好世界"


def test_clean_response_handles_empty():
    assert clean_response_text("") == ""
    assert clean_response_text(None) == ""


def test_no_api_key_returns_error_not_raises(tmp_path):
    """Each provider must short-circuit gracefully when api_key is empty."""
    wav = tmp_path / "x.wav"
    # Write a tiny valid WAV file (44-byte header + a few zero samples)
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00" * 320)

    for name, cls in PROVIDERS.items():
        p = cls(api_key="", model=DEFAULT_MODELS[name][0])
        r = p.transcribe(str(wav))
        assert r.ok is False
        assert "no api_key" in (r.error or "").lower()


def test_siliconflow_post_invocation(tmp_path):
    """Verify SiliconFlowProvider posts to the right URL with bearer auth."""
    wav = tmp_path / "x.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00" * 320)

    fake = MagicMock(status_code=200, text="{}")
    fake.json.return_value = {"text": "hello"}

    with patch("voice2ai.providers.siliconflow.requests.post", return_value=fake) as mock_post:
        from voice2ai.providers import get_provider
        cls = get_provider("siliconflow")
        p = cls(api_key="sk-x", model="FunAudioLLM/SenseVoiceSmall")
        r = p.transcribe(str(wav))

    assert r.ok
    assert r.text == "hello"
    args, kwargs = mock_post.call_args
    assert "siliconflow.cn" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer sk-x"


def test_openai_uses_response_format_json(tmp_path):
    wav = tmp_path / "x.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00" * 320)

    fake = MagicMock(status_code=200, text="{}")
    fake.json.return_value = {"text": "world"}

    with patch("voice2ai.providers.openai.requests.post", return_value=fake) as mock_post:
        from voice2ai.providers import get_provider
        cls = get_provider("openai")
        p = cls(api_key="sk-y", model="whisper-1")
        r = p.transcribe(str(wav), language_hint="en")

    assert r.text == "world"
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["response_format"] == "json"
    assert kwargs["data"]["language"] == "en"
