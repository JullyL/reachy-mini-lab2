"""Emotions app trajectory processing plus an explicitly adapted study cue.

parse_trajectory / downsample_by_hz port src/lib/emotionsLibrary.ts, MIT,
cde39d23da61ada61d9ae4635bee051334434b44. Extra validation rejects malformed
study assets rather than silently inventing timestamps. Adaptation is new code.
"""
import math

import numpy as np


def downsample_by_hz(times, frames, hz=50):
    if len(frames) <= 2 or (len(frames) - 1) / (times[-1] - times[0]) <= hz * 1.1:
        return times, frames
    kept, last = [], -math.inf
    for i, t in enumerate(times):
        if i in (0, len(times) - 1) or t - last >= 1 / hz:
            kept.append(i)
            last = t
    return [times[i] for i in kept], [frames[i] for i in kept]


def parse_trajectory(raw):
    frames = raw.get("set_target_data", raw.get("frames", []))
    times = raw.get("time", [])
    if len(times) != len(frames) or len(times) < 2:
        raise ValueError("Trajectory needs matching time and frame arrays")
    if not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("Trajectory times must be finite and strictly increasing")
    for frame in frames:
        head, antennas = np.asarray(frame["head"]), np.asarray(frame["antennas"])
        if head.shape != (4, 4) or antennas.shape != (2,):
            raise ValueError("Invalid pose dimensions")
        if not np.isfinite(head).all() or not np.isfinite(antennas).all():
            raise ValueError("Nonfinite pose")
        if not np.allclose(head[3], [0, 0, 0, 1]):
            raise ValueError("Invalid homogeneous pose")
        if not np.allclose(head[:3, :3].T @ head[:3, :3], np.eye(3), atol=1e-4):
            raise ValueError("Invalid rotation")
    return downsample_by_hz(times, frames)


def rotvec(matrix):
    angle = math.acos(float(np.clip((np.trace(matrix) - 1) / 2, -1, 1)))
    if angle < 1e-8:
        return np.zeros(3)
    if angle > math.pi - 1e-3:
        raise ValueError("Source rotation too close to 180 degrees")
    return angle / (2 * math.sin(angle)) * np.array([
        matrix[2, 1] - matrix[1, 2], matrix[0, 2] - matrix[2, 0],
        matrix[1, 0] - matrix[0, 1],
    ])


def rotation(vector):
    angle = np.linalg.norm(vector)
    if angle < 1e-10:
        return np.eye(3)
    x, y, z = vector / angle
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)

