"""tests/test_vad.py — energy-based VAD state machine.

We don't run real audio; we feed synthetic numpy chunks of known RMS.
"""
from __future__ import annotations

import numpy as np

from voice2cc.vad import EnergyVAD, VADConfig


def _silence(ms: int, sr: int = 16000) -> np.ndarray:
    return np.zeros(int(sr * ms / 1000), dtype=np.float32)


def _speech(ms: int, level: float = 0.05, sr: int = 16000) -> np.ndarray:
    # Constant-amplitude tone — RMS = level (since sqrt(mean(level^2)) = level)
    n = int(sr * ms / 1000)
    return np.full(n, level, dtype=np.float32)


def _new(threshold=0.015, min_speech=200, min_silence=400):
    starts, ends = [0], [0]
    vad = EnergyVAD(
        VADConfig(
            threshold=threshold,
            min_speech_ms=min_speech,
            min_silence_ms=min_silence,
        ),
        on_speech_start=lambda: starts.__setitem__(0, starts[0] + 1),
        on_speech_end=lambda: ends.__setitem__(0, ends[0] + 1),
    )
    return vad, starts, ends


def test_pure_silence_never_fires():
    vad, starts, ends = _new()
    for _ in range(10):
        vad.process(_silence(100))
    assert starts[0] == 0
    assert ends[0] == 0


def test_short_blip_below_min_speech_does_not_trigger():
    vad, starts, ends = _new(min_speech=300)
    vad.process(_speech(100, level=0.1))   # 100ms speech, < min_speech 300ms
    vad.process(_silence(500))
    assert starts[0] == 0


def test_continuous_speech_fires_start_once():
    vad, starts, ends = _new(min_speech=200)
    vad.process(_speech(150, level=0.1))
    vad.process(_speech(150, level=0.1))
    assert starts[0] == 1
    # More speech doesn't fire start again
    vad.process(_speech(200, level=0.1))
    assert starts[0] == 1
    assert ends[0] == 0


def test_speech_then_silence_fires_end():
    vad, starts, ends = _new(min_speech=200, min_silence=400)
    vad.process(_speech(300, level=0.1))    # → speech_start
    assert starts[0] == 1
    vad.process(_silence(500))              # → speech_end
    assert ends[0] == 1


def test_brief_silence_inside_utterance_does_not_end():
    vad, starts, ends = _new(min_speech=200, min_silence=500)
    vad.process(_speech(300, level=0.1))    # speech_start
    vad.process(_silence(200))              # 200ms gap < min_silence 500
    vad.process(_speech(300, level=0.1))    # still speaking
    vad.process(_silence(600))              # now end
    assert starts[0] == 1
    assert ends[0] == 1


def test_threshold_filters_low_amplitude_noise():
    vad, starts, ends = _new(threshold=0.05, min_speech=100)
    # Constant-level 0.02 signal: noise; below threshold 0.05
    vad.process(_speech(500, level=0.02))
    assert starts[0] == 0


def test_reset_clears_state():
    vad, starts, ends = _new(min_speech=200)
    vad.process(_speech(150, level=0.1))   # accumulate 150ms speech but not yet trigger
    vad.reset()
    vad.process(_speech(150, level=0.1))   # if reset was clean, this is also <200ms
    assert starts[0] == 0
