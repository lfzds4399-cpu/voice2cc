"""audio.py — microphone capture with always-on pre-roll.

Why pre-roll: the user's first syllable is the highest-loss point. By keeping the
last ~300ms of audio buffered while idle, we can prepend it to the recording the
moment the hotkey fires, recovering the leading "嗨"/"hey".
"""
from __future__ import annotations

import collections
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger("voice2cc.audio")

CHANNELS = 1


@dataclass
class DeviceInfo:
    index: int
    name: str
    max_channels: int
    default_samplerate: float


def list_input_devices() -> list[DeviceInfo]:
    """Return all input-capable devices, sorted by index. Empty list on driver failure."""
    try:
        out = []
        for i, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) > 0:
                out.append(DeviceInfo(
                    index=i,
                    name=str(d.get("name", f"device {i}")),
                    max_channels=int(d["max_input_channels"]),
                    default_samplerate=float(d.get("default_samplerate", 16000.0)),
                ))
        return out
    except Exception as e:
        logger.exception("list_input_devices failed: %s", e)
        return []


def default_input_device() -> Optional[int]:
    try:
        info = sd.query_devices(kind="input")
        return info.get("index") if isinstance(info, dict) else None
    except Exception:
        return None


class MicCapture:
    """Holds the InputStream + a pre-roll ring buffer.

    State: callers set self.recording = True/False. While recording, all audio chunks
    flow into the queue. While idle, chunks rotate through the pre-roll deque.
    """

    def __init__(self, sample_rate: int = 16000, input_device: int = -1, preroll_sec: float = 0.30):
        self.sample_rate = sample_rate
        # sounddevice uses None for default device, not -1
        self.input_device = None if input_device < 0 else input_device
        self.preroll_sec = preroll_sec

        self.audio_q: "queue.Queue[np.ndarray]" = queue.Queue()
        # 64 chunks @ ~10ms each (default blocksize) ≈ 640ms — enough headroom for 300ms
        self.preroll: collections.deque = collections.deque(maxlen=64)
        self.volume_level: float = 0.0
        self._lock = threading.Lock()
        self._recording: bool = False
        self._stream: Optional[sd.InputStream] = None
        self._device_name: str = "?"
        # VAD / continuous-mode hook: every audio chunk is forwarded here when set.
        # Callback is invoked from the audio thread — keep it cheap or spawn a worker.
        self._frame_listener: Optional[Callable[[np.ndarray], None]] = None

    def set_frame_listener(self, fn: Optional[Callable[[np.ndarray], None]]) -> None:
        """Install a per-chunk callback (used by VAD in continuous mode). None to clear."""
        self._frame_listener = fn

    @property
    def recording(self) -> bool:
        return self._recording

    def device_name(self) -> str:
        return self._device_name

    def start(self) -> None:
        """Open the input stream. Raises sounddevice.PortAudioError on failure."""
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=CHANNELS,
            callback=self._cb,
            dtype="float32",
            device=self.input_device,
        )
        self._stream.start()
        try:
            qd = sd.query_devices(kind="input") if self.input_device is None else \
                 sd.query_devices(self.input_device)
            self._device_name = str(qd.get("name", "?")) if isinstance(qd, dict) else "?"
        except Exception:
            self._device_name = "?"
        logger.info("mic open: device=%r sr=%d", self._device_name, self.sample_rate)

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                logger.exception("mic stop")
            self._stream = None

    def begin_record(self) -> list[np.ndarray]:
        """Mark recording=True and return the current pre-roll snapshot for prepending."""
        with self._lock:
            snapshot = list(self.preroll)
            self.preroll.clear()
            self._recording = True
            # Drain stale audio_q in case of leftover from previous run
            while not self.audio_q.empty():
                try:
                    self.audio_q.get_nowait()
                except queue.Empty:
                    break
        return snapshot

    def end_record(self, prepend: list[np.ndarray]) -> tuple[Optional[np.ndarray], float]:
        """Stop recording, drain the queue, return (audio array or None, duration_sec)."""
        with self._lock:
            self._recording = False
        # Tiny sleep to let the audio_callback fire one last time
        import time
        time.sleep(0.05)

        chunks = list(prepend)
        while not self.audio_q.empty():
            try:
                chunks.append(self.audio_q.get_nowait())
            except queue.Empty:
                break

        if not chunks:
            return None, 0.0
        audio = np.concatenate(chunks, axis=0)
        duration = len(audio) / float(self.sample_rate)
        return audio, duration

    def _cb(self, indata, frames, time_info, status):
        chunk = indata.copy()
        with self._lock:
            if self._recording:
                self.audio_q.put(chunk)
            else:
                self.preroll.append(chunk)
            listener = self._frame_listener
        # volume level is updated regardless so the floating widget shows the mic is alive
        try:
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            self.volume_level = min(1.0, rms * 12)
        except Exception:
            self.volume_level = 0.0
        # Forward chunk to VAD listener (if any). Outside the lock so a slow
        # listener can never block the audio callback's `_recording` check.
        if listener is not None:
            try:
                listener(chunk)
            except Exception:
                logger.exception("frame_listener raised")
