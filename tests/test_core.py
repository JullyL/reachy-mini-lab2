import json

import numpy as np
import pytest

from reachy_lab2.conversation_audio import audio_to_float32
from reachy_lab2.motion import downsample_by_hz, parse_trajectory, rotvec
from reachy_lab2.robot import MockRobot
from reachy_lab2.trial import Controller, ROOT, digest, load_json, run_trial


def test_conditions_are_one_factor():
    cfg = load_json(ROOT / "config/conditions.json")
    assert cfg["conditions"] == {"A": 0, "B": 1}
    assert cfg["parameter"] == "expressive_motion"
    assert cfg["cue_start_s"] == .5
    assert cfg["cue_duration_s"] == 1
    assert cfg["cue_start_s"] + cfg["cue_duration_s"] < cfg["speech_target_s"]


def test_motion_is_rigid_bounded_and_neutral():
    times, frames = parse_trajectory(load_json(ROOT / "assets/motion/processing.json"))
    assert len(frames) == 51 and times[0] == 0 and times[-1] == 1
    for frame in [frames[0], frames[-1]]:
        np.testing.assert_allclose(frame["head"], np.eye(4))
        np.testing.assert_allclose(frame["antennas"], [0, 0])
    for frame in frames:
        h = np.array(frame["head"])
        assert np.linalg.det(h[:3, :3]) == pytest.approx(1)
        assert np.linalg.norm(rotvec(h[:3, :3])) <= np.deg2rad(8.01)
        assert np.max(np.abs(frame["antennas"])) <= .20001
        assert np.linalg.norm(h[:3, 3]) <= .003001
    assert np.max(np.abs([f["antennas"] for f in frames])) > .05


def test_source_decimator_keeps_ends():
    t, f = downsample_by_hz([i/100 for i in range(101)], list(range(101)))
    assert t[0] == 0 and t[-1] == 1 and f[0] == 0 and f[-1] == 100
    assert len(t) < 101


def test_malformed_trajectory_rejected():
    with pytest.raises(ValueError):
        parse_trajectory({"time": [0, 1], "frames": []})


def test_conversation_pcm_conversion():
    np.testing.assert_allclose(audio_to_float32(np.array([-32768, 0, 16384], dtype=np.int16)), [-1, 0, .5])
    with pytest.raises(TypeError):
        audio_to_float32(np.ones(2, dtype=np.float64))


def test_assets_are_frozen_and_real_speech_length():
    questions = load_json(ROOT / "config/questions.json")
    for q in questions["questions"]:
        assert digest(ROOT / q["audio"]) == q["sha256"]
        assert 5 < q["duration_s"] < 20


def test_overlap_is_refused():
    with Controller():
        with pytest.raises(RuntimeError, match="Another trial"):
            with Controller():
                pass


def test_interruption_retains_log_and_recovers(tmp_path):
    with Controller() as control:
        path, status = run_trial(MockRobot(), control, "A", "q1", tmp_path,
                                  silent=True, stop_after=.03)
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    assert status == "interrupted"
    assert rows[-1]["completion_status"] == "interrupted"
    assert rows[-1]["neutral_recovery_succeeded"]
    assert not rows[-1]["technically_valid"]
    assert not any(r["marker"] == "SPEECH_START" for r in rows)


def test_motion_failure_logs_failed_recovery(tmp_path):
    class BrokenRobot(MockRobot):
        def send(self, frame):
            raise ConnectionError("simulated disconnect")
        def neutral(self, stop=None):
            if getattr(self, "initial_done", False):
                raise ConnectionError("still disconnected")
            self.initial_done = True
            return super().neutral(stop)
    with Controller() as control:
        path, status = run_trial(BrokenRobot(), control, "A", "q1", tmp_path, silent=True)
    end = json.loads(path.read_text().splitlines()[-1])
    assert status == "failed" and not end["neutral_recovery_succeeded"]
    assert "ConnectionError" in end["error"]
