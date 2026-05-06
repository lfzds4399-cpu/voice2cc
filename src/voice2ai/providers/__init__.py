"""STT provider registry.

Each provider implements `STTProvider` (see base.py) and registers itself in PROVIDERS.
The orchestrator picks one based on Settings.provider.
"""
from __future__ import annotations

from typing import Type

from .base import STTProvider, TranscribeResult
from .siliconflow import SiliconFlowProvider
from .openai import OpenAIProvider
from .groq import GroqProvider
from .azure import AzureProvider

PROVIDERS: dict[str, Type[STTProvider]] = {
    "siliconflow": SiliconFlowProvider,
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "azure": AzureProvider,
}

DEFAULT_MODELS: dict[str, list[str]] = {
    "siliconflow": ["FunAudioLLM/SenseVoiceSmall", "iic/SenseVoiceSmall"],
    "openai": ["whisper-1", "gpt-4o-mini-transcribe", "gpt-4o-transcribe"],
    "groq": ["whisper-large-v3-turbo", "whisper-large-v3", "distil-whisper-large-v3-en"],
    "azure": ["whisper"],
}

PROVIDER_KEY_HELP_URL: dict[str, str] = {
    "siliconflow": "https://cloud.siliconflow.cn/account/ak",
    "openai": "https://platform.openai.com/api-keys",
    "groq": "https://console.groq.com/keys",
    "azure": "https://portal.azure.com (Speech Service → Keys)",
}


def get_provider(name: str) -> Type[STTProvider]:
    if name not in PROVIDERS:
        raise ValueError(f"unknown provider {name!r}; valid: {list(PROVIDERS)}")
    return PROVIDERS[name]


__all__ = [
    "STTProvider",
    "TranscribeResult",
    "PROVIDERS",
    "DEFAULT_MODELS",
    "PROVIDER_KEY_HELP_URL",
    "get_provider",
]
