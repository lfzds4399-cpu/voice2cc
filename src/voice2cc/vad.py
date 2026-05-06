"""vad.py — energy-based Voice Activity Detection for continuous capture.

Why energy-based (not webrtcvad/silero-vad):
  - webrtcvad needs Microsoft C++ Build Tools (no Python 3.14 wheel as of 2026-05).
  - silero-vad needs onnxruntime (~50 MB) — overkill for a quiet desktop user.
  - RMS energy + dwell counters give 90%+ accuracy at zero dependencies in
    typical home/office environments and is upgradeable later (the EnergyVAD
    interface stays the same; swap the `_rms` helper for a model probe).

State machine:

  IDLE  ──speech ≥ min_speech_ms──→  SPEECH  ──silence ≥ min_silence_ms──→  IDLE
                                            │
                                            └── on each transition we fire a callback.

Tuning:
  - Default threshold 0.015 was empirically OK on a built-in laptop array mic
    in a quiet room. Loud ambient → bump to 0.025; lapel mic → drop to 0.01.
  - min_speech_ms guards against single-click / cough false-positives.
  - min_silence_ms is the natural pause between sentences (1.5 s feels human).

Thread safety:
  `process()` is single-producer (the mic callback). Callbacks fire in that
  same thread — keep them short or spawn a worker thread inside the callback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import numpy as np

logger = logging.getLogger("voice2cc.vad")


@dataclass
class VADConfig:
    threshold: float = 0.015
    min_speech_ms: int = 250
    min_silence_ms: int = 1500
    sample_rate: int = 16000


class EnergyVAD:
    """Energy-based VAD with hysteresis."""

    IDLE = "idle"
    SPEECH = "speech"

    def __init__(
        self,
        config: VADConfig,
        on_speech_start: Callable[[], None],
        on_speech_end: Callable[[], None],
    ) -> None:
        self.cfg = config
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.state = self.IDLE
        self._speech_ms = 0
        self._silence_ms = 0

    @staticmethod
    def _rms(chunk: np.ndarray) -> float:
        if chunk.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

    def process(self, chunk: np.ndarray) -> None:
        rms = self._rms(chunk)
        is_speech = rms >= self.cfg.threshold
        chunk_ms = int(1000 * len(chunk) / self.cfg.sample_rate)

        if self.state == self.IDLE:
            if is_speech:
                self._speech_ms += chunk_ms
                if self._speech_ms >= self.cfg.min_speech_ms:
                    self.state = self.SPEECH
                    self._speech_ms = 0
                    self._silence_ms = 0
                    logger.info("VAD: speech_start (rms=%.4f)", rms)
                    try:
                        self.on_speech_start()
                    except Exception:
                        logger.exception("on_speech_start callback failed")
            else:
                self._speech_ms = max(0, self._speech_ms - chunk_ms)

        elif self.state == self.SPEECH:
            if is_speech:
                self._silence_ms = 0
            else:
                self._silence_ms += chunk_ms
                if self._silence_ms >= self.cfg.min_silence_ms:
                    self.state = self.IDLE
                    silence = self._silence_ms
                    self._silence_ms = 0
                    logger.info("VAD: speech_end (silence=%dms)", silence)
                    try:
                        self.on_speech_end()
                    except Exception:
                        logger.exception("on_speech_end callback failed")

    def reset(self) -> None:
        self.state = self.IDLE
        self._speech_ms = 0
        self._silence_ms = 0
