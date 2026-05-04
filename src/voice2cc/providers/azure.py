"""Azure OpenAI Whisper.

Azure Whisper has a different URL shape than OpenAI/SiliconFlow/Groq:
  POST https://<resource>.openai.azure.com/openai/deployments/<deployment>/audio/transcriptions?api-version=2024-02-15-preview

So `azure_region` here is actually the resource subdomain (or full base override).
For most users we recommend setting `api_base` to the full deployment URL prefix.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .base import STTProvider, TranscribeResult, clean_response_text

logger = logging.getLogger("voice2cc.provider.azure")

DEFAULT_API_VERSION = "2024-06-01"


class AzureProvider(STTProvider):
    name = "azure"

    def transcribe(self, wav_path: str, language_hint: Optional[str] = None) -> TranscribeResult:
        if not self.api_key:
            return TranscribeResult("", 0, error="no api_key")

        base = self.api_base.rstrip("/") if self.api_base else ""
        if not base:
            region = self.extras.get("azure_region", "").strip()
            if not region:
                return TranscribeResult(
                    "", 0,
                    error="azure provider needs api_base or azure_region (resource subdomain)"
                )
            base = f"https://{region}.openai.azure.com/openai/deployments/{self.model}"

        url = f"{base}/audio/transcriptions?api-version={DEFAULT_API_VERSION}"
        t0 = time.time()
        try:
            with open(wav_path, "rb") as f:
                data = {"response_format": "json"}
                if language_hint:
                    data["language"] = language_hint
                r = requests.post(
                    url,
                    headers={"api-key": self.api_key},
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
