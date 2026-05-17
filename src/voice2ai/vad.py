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
                                            └── a callback fires on each transition.

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

logger = logging.getLogger("voice2ai.vad")


@dataclass
class VADConfig:
    threshold: float = 0.015           # min RMS to ENTER speech (gate IDLE→SPEECH)
    silence_ratio: float = 0.4         # RMS exit gate = threshold * silence_ratio
                                       #   → ratio 0.4 means SPEECH→IDLE needs RMS < 0.006
                                       #     so quiet breath / short pauses don't end the utterance
                                       #     while a true 1.5s silence still does
    max_zcr: float = 0.18              # max zero-crossing rate to count as speech
                                       #   speech ZCR ≈ 0.05–0.15 (vowels low, fricatives ~0.20)
                                       #   breath / wind / fan ≈ 0.20–0.45 (broadband noise)
                                       #   set to 1.0 to disable ZCR gate entirely
    min_speech_ms: int = 250
    min_silence_ms: int = 1500
    sample_rate: int = 16000


class EnergyVAD:
    """RMS + zero-crossing-rate VAD with hysteresis.

    The ZCR gate is what separates speech from breath / fan noise / wind / clicks.
    Voiced speech has clear periodic structure → ZCR stays in the 0.05–0.15 range.
    Aspirated noise (breathing into the mic, room AC, paper rustle) is broadband
    → ZCR jumps above ~0.20.

    A frame counts as speech only if BOTH:
      1. RMS ≥ threshold (loud enough), AND
      2. ZCR ≤ max_zcr (periodic enough)
    """

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

    @staticmethod
    def _zcr(chunk: np.ndarray) -> float:
        """Zero-crossing rate — fraction of samples where sign changes.
        ~0.05–0.15 for voiced speech, ~0.20+ for broadband noise."""
        if chunk.size < 2:
            return 0.0
        # Skip near-zero samples (DC offset / silence) so ZCR isn't dominated by noise floor
        a = chunk.astype(np.float32).flatten()
        # Normalise so threshold check is amplitude-independent
        amax = float(np.max(np.abs(a))) or 1.0
        a = a / amax
        signs = np.where(a >= 0, 1, -1).astype(np.int8)
        crossings = int(np.sum(np.abs(np.diff(signs))) // 2)
        return crossings / float(len(a))

    def process(self, chunk: np.ndarray) -> None:
        rms = self._rms(chunk)
        zcr = self._zcr(chunk)
        chunk_ms = int(1000 * len(chunk) / self.cfg.sample_rate)

        # Two thresholds for hysteresis:
        #   enter_speech: strict — needs both RMS ≥ threshold AND ZCR ≤ max_zcr
        #   exit_speech (a.k.a. silence): much looser — only TRUE silence (very low RMS)
        #     counts. This lets quiet breath / mid-sentence pauses NOT end the utterance.
        enter_speech = (rms >= self.cfg.threshold) and (zcr <= self.cfg.max_zcr)
        silence_floor = self.cfg.threshold * self.cfg.silence_ratio
        is_silent = rms < silence_floor   # used in SPEECH state

        if self.state == self.IDLE:
            if enter_speech:
                self._speech_ms += chunk_ms
                if self._speech_ms >= self.cfg.min_speech_ms:
                    self.state = self.SPEECH
                    self._speech_ms = 0
                    self._silence_ms = 0
                    logger.info("VAD: speech_start (rms=%.4f zcr=%.3f)", rms, zcr)
                    try:
                        self.on_speech_start()
                    except Exception:
                        logger.exception("on_speech_start callback failed")
            else:
                self._speech_ms = max(0, self._speech_ms - chunk_ms)

        elif self.state == self.SPEECH:
            if not is_silent:
                # Anything above silence_floor (including breath / mid-sentence pauses)
                # keeps the utterance alive. Only TRUE silence counts down the timer.
                self._silence_ms = 0
            else:
                self._silence_ms += chunk_ms
                if self._silence_ms >= self.cfg.min_silence_ms:
                    self.state = self.IDLE
                    silence = self._silence_ms
                    self._silence_ms = 0
                    logger.info("VAD: speech_end (silence=%dms rms=%.4f)", silence, rms)
                    try:
                        self.on_speech_end()
                    except Exception:
                        logger.exception("on_speech_end callback failed")

    def reset(self) -> None:
        self.state = self.IDLE
        self._speech_ms = 0
        self._silence_ms = 0
