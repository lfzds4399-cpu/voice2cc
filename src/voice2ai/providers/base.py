"""STT provider abstract base."""
from __future__ import annotations

import abc
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("voice2ai.provider")


@dataclass
class TranscribeResult:
    text: str
    latency_ms: int
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class STTProvider(abc.ABC):
    name: str = "base"

    def __init__(self, api_key: str, model: str, api_base: str = "", **extras):
        self.api_key = api_key.strip()
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.extras = extras

    @abc.abstractmethod
    def transcribe(self, wav_path: str, language_hint: Optional[str] = None) -> TranscribeResult:
        """Transcribe a WAV file. Implementations must NOT raise — return result.error instead."""
        ...

    def health_check(self) -> TranscribeResult:
        """Send a tiny synthetic WAV and return whether the API is reachable.

        Provider implementations may override; default uses transcribe() with a 0.5s 440Hz tone.
        """
        import tempfile

        import numpy as np
        import soundfile as sf

        sr = 16000
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        y = (0.2 * np.sin(2 * np.pi * 440 * t)).astype("float32")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            sf.write(wav_path, y, sr)
            return self.transcribe(wav_path)
        finally:
            try:
                import os
                os.unlink(wav_path)
            except OSError:
                pass


# Shared utilities for OpenAI-compatible providers (SiliconFlow / OpenAI / Groq)
_TOKEN_RE = re.compile(r"<\|[^|]*\|>")


def clean_response_text(text: str) -> str:
    """Strip SenseVoice-style language/emotion tokens like <|zh|><|HAPPY|>."""
    return _TOKEN_RE.sub("", text or "").strip()
