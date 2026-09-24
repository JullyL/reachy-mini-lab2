"""Adapted from Pollen Robotics Conversation App (Apache-2.0).

Revision b9f58a3587d79a3275d4402d1a8d210649d62d50:
streaming.audio_to_float32.
See third_party/conversation/LICENSE and SOURCE_INTEGRATION.md.
"""
import wave
from pathlib import Path

import numpy as np


def audio_to_float32(audio):
    """Upstream PCM conversion, used by every cached-answer playback."""
    if audio.dtype == np.int16:
        return audio.astype(np.float32) / 32768.0
    if audio.dtype == np.float32:
        return audio.astype(np.float32, copy=False)
    raise TypeError(f"Unsupported audio data type: {audio.dtype}")


def read_wav(path: Path):
    with wave.open(str(path), "rb") as stream:
        if stream.getsampwidth() != 2 or stream.getnchannels() != 1:
            raise ValueError("Answer must be mono signed 16-bit PCM WAV")
        rate = stream.getframerate()
        audio = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
    if not len(audio) or not np.any(audio):
        raise ValueError("Answer has no speech samples")
    return rate, audio_to_float32(audio)

