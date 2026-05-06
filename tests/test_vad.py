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


def _new(threshold=0.015, min_speech=200, min_silence=400, max_zcr=1.0):
    """max_zcr=1.0 disables the ZCR gate so the older energy-only tests still pass."""
    starts, ends = [0], [0]
    vad = EnergyVAD(
        VADConfig(
            threshold=threshold,
            max_zcr=max_zcr,
            min_speech_ms=min_speech,
            min_silence_ms=min_silence,
        ),
        on_speech_start=lambda: starts.__setitem__(0, starts[0] + 1),
        on_speech_end=lambda: ends.__setitem__(0, ends[0] + 1),
    )
    return vad, starts, ends


def _broadband_noise(ms: int, level: float = 0.05, sr: int = 16000, seed: int = 0) -> np.ndarray:
    """Synthetic random-amplitude noise — simulates breath / wind. High ZCR."""
    n = int(sr * ms / 1000)
    rng = np.random.RandomState(seed)
    # White-ish noise with constant RMS = level
    raw = rng.uniform(-1.0, 1.0, size=n).astype(np.float32)
    raw *= level / max(np.sqrt(np.mean(raw ** 2)), 1e-9)
    return raw


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


def test_zcr_gate_filters_broadband_noise():
    """High-RMS broadband noise (breath / fan) must NOT trigger speech_start when ZCR gate is on."""
    vad, starts, ends = _new(threshold=0.015, max_zcr=0.18, min_speech=200)
    # Loud broadband noise — RMS well above threshold but ZCR is ~0.5
    for _ in range(10):
        vad.process(_broadband_noise(100, level=0.1))
    assert starts[0] == 0, "broadband noise should be rejected by ZCR gate"


def test_zcr_gate_passes_periodic_speech():
    """Constant-amplitude tone (ZCR≈0) passes both gates and triggers."""
    vad, starts, ends = _new(threshold=0.015, max_zcr=0.18, min_speech=200)
    vad.process(_speech(300, level=0.05))   # constant amplitude → 0 zero-crossings
    assert starts[0] == 1


def test_zcr_disabled_when_max_zcr_is_one():
    """max_zcr=1.0 disables the ZCR gate — broadband noise will trigger."""
    vad, starts, ends = _new(threshold=0.015, max_zcr=1.0, min_speech=200)
    for _ in range(5):
        vad.process(_broadband_noise(100, level=0.1))
    assert starts[0] == 1
