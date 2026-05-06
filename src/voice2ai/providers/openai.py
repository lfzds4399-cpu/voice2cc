"""OpenAI Whisper STT (/v1/audio/transcriptions)."""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .base import STTProvider, TranscribeResult, clean_response_text

logger = logging.getLogger("voice2ai.provider.openai")


class OpenAIProvider(STTProvider):
    name = "openai"

    DEFAULT_BASE = "https://api.openai.com/v1"

    def transcribe(self, wav_path: str, language_hint: Optional[str] = None) -> TranscribeResult:
        if not self.api_key:
            return TranscribeResult("", 0, error="no api_key")
        base = self.api_base or self.DEFAULT_BASE
        url = f"{base}/audio/transcriptions"
        t0 = time.time()
        try:
            with open(wav_path, "rb") as f:
                data = {"model": self.model, "response_format": "json"}
                if language_hint:
                    data["language"] = language_hint
                r = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": ("voice.wav", f, "audio/wav")},
                    data=data,
                    timeout=60,
                )
        except requests.exceptions.RequestException as e:
            elapsed = int((time.time() - t0) * 1000)
            return TranscribeResult("", elapsed, error=f"{type(e).__name__}: {e}")
        elapsed = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            return TranscribeResult("", elapsed, error=f"HTTP {r.status_code}: {r.text[:200]}")
        try:
            text = r.json().get("text", "")
        except Exception as e:
            return TranscribeResult("", elapsed, error=f"bad json: {e}")
        return TranscribeResult(clean_response_text(text), elapsed)
