"""tests/test_audio_preroll.py — pre-roll buffer correctness without opening real mic."""
from __future__ import annotations

from unittest.mock import patch

import numpy as np

from voice2ai.audio import MicCapture


def test_preroll_collects_chunks_during_idle():
    mic = MicCapture(sample_rate=16000, input_device=-1, preroll_sec=0.30)
    # simulate 5 audio callbacks while idle
    for i in range(5):
        chunk = np.random.randn(160).astype("float32")
        mic._cb(chunk, 160, None, None)
    assert len(mic.preroll) == 5
    assert mic.audio_q.empty()


def test_begin_record_returns_preroll_and_clears():
    mic = MicCapture(sample_rate=16000, input_device=-1, preroll_sec=0.30)
    for _ in range(3):
        mic._cb(np.zeros(160, dtype="float32"), 160, None, None)
    snap = mic.begin_record()
    assert len(snap) == 3
    assert len(mic.preroll) == 0
    assert mic.recording is True


def test_recording_chunks_go_to_queue_not_preroll():
    mic = MicCapture(sample_rate=16000, input_device=-1)
    mic.begin_record()
    for _ in range(4):
        mic._cb(np.zeros(160, dtype="float32"), 160, None, None)
    assert mic.audio_q.qsize() == 4
    assert len(mic.preroll) == 0


def test_end_record_concatenates_prepend_and_queue():
    mic = MicCapture(sample_rate=16000, input_device=-1)
    # idle → fill preroll
    for _ in range(2):
        mic._cb(np.ones(160, dtype="float32"), 160, None, None)
    snap = mic.begin_record()
    # recording → 3 more chunks
    for _ in range(3):
        mic._cb(np.ones(160, dtype="float32"), 160, None, None)
    audio, dur = mic.end_record(snap)
    assert audio is not None
    # 5 chunks * 160 samples = 800 samples → 800/16000 = 0.05s
    assert audio.shape[0] == 5 * 160
    assert abs(dur - 800 / 16000) < 1e-6
    assert mic.recording is False


def test_end_record_with_no_audio():
    mic = MicCapture(sample_rate=16000, input_device=-1)
    mic.begin_record()
    audio, dur = mic.end_record([])
    assert audio is None
    assert dur == 0.0
