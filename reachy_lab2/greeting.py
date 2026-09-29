"""One amplitude-scaled greeting; SDK antenna order is RIGHT, LEFT."""
import hashlib
import json

import numpy as np

from .motion import parse_trajectory
from .trial import ROOT, digest, load_json

STUDY_VERSION = "antenna-greeting-v1"


def software_digest():
    h = hashlib.sha256()
    for path in sorted((ROOT / "reachy_lab2").glob("*.py")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def settings():
    cfg = load_json(ROOT / "config/conditions.json")
    if cfg["study_version"] != STUDY_VERSION or cfg["parameter"] != "antenna_amplitude_deg":
        raise ValueError("Wrong study configuration")
    if set(cfg["conditions"]) != {"A", "B"} or not all(
        np.isfinite(v) and 0 < v <= 30 for v in cfg["conditions"].values()
    ) or cfg["conditions"]["A"] >= cfg["conditions"]["B"]:
        raise ValueError("Require 0 < A < B <= 30 degrees; physical review still required")
    if (cfg["pre_hold_s"], cfg["segment_durations_s"], cfg["post_hold_s"],
        cfg["interpolation"], cfg["command_hz"], cfg["feedback_hz"], cfg["audio_gain"]) != (
        1, [1, 2, 1], 1, "minimum_jerk", 50, 50, 1):
        raise ValueError("Timing, interpolation, rates and audio gain must match the protocol")
    return cfg


def minimum_jerk(u):
    return 10*u**3 - 15*u**4 + 6*u**5


def compile_greeting(condition, cfg=None, neutral=None, commissioning=False):
    cfg = settings() if cfg is None else cfg
    amplitude = cfg["conditions"][condition] * (0.5 if commissioning else 1.0)
    neutral = np.zeros(2) if neutral is None else np.asarray(neutral, dtype=float)
    if neutral.shape != (2,) or not np.isfinite(neutral).all():
        raise ValueError("Need two finite calibrated neutral angles")
    times = np.arange(301) / 50
    frames = []
    for t in times:
        if t <= 1 or t >= 5:
            left = 0.0
        elif t <= 2:
            left = amplitude * minimum_jerk(t-1)
        elif t <= 4:
            left = amplitude * (1 - 2*minimum_jerk((t-2)/2))
        else:
            left = -amplitude * (1-minimum_jerk(t-4))
        frames.append({"head": np.eye(4).tolist(),
                       "antennas": (neutral + np.deg2rad([-left, left])).tolist(),
                       "body_yaw": 0.0})
    # The Emotions parser/decimator is actually on the runtime path.
    times, frames = parse_trajectory({"time": times.tolist(), "set_target_data": frames})
    trajectory = {"time": times, "set_target_data": frames}
    return {**trajectory, "amplitude_deg": amplitude,
            "sha256": hashlib.sha256(json.dumps(trajectory, sort_keys=True).encode()).hexdigest()}


def require_physical_review():
    review = load_json(ROOT / "config/physical_review.json")
    calibration = load_json(ROOT / "config/calibration.json")
    cfg = settings()
    expected = {"configuration_sha256": digest(ROOT / "config/conditions.json"),
                "calibration_sha256": digest(ROOT / "config/calibration.json"),
                "audio_sha256": digest(ROOT / cfg["audio"]), "software_sha256": software_digest()}
    if not review["approved"] or not calibration["physically_verified"] or cfg["provisional"]:
        raise ValueError("Physical review/calibration pending; commissioning and technical trials only")
    if any(review.get(k) != v for k, v in expected.items()):
        raise ValueError("Physical review does not match the frozen assets/code/configuration")
    if any(not review.get(k) or str(review[k]).startswith("PENDING") for k in (
        "reviewer", "robot_id", "simulation_evidence", "half_amplitude_evidence",
        "full_amplitude_evidence", "audio_listening_review")):
        raise ValueError("Physical evidence is incomplete")
    if review["robot_id"] != calibration["robot_id"]:
        raise ValueError("Calibration/review robot identity mismatch")
    return review
