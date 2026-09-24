"""Explicitly simulation-only SDK adapter; no daemon creation or upgrades."""
import json
import time
import urllib.request

import numpy as np

from .motion import rotation, rotvec
from .emotion_player import transition_duration


def api(path, post=False):
    request = urllib.request.Request("http://127.0.0.1:8000/api/" + path,
                                     data=b"" if post else None)
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.load(response)


class SimRobot:
    def __init__(self):
        self.mini = None

    def connect(self):
        status = api("daemon/status")
        if not status.get("simulation_enabled") or status.get("mockup_sim_enabled"):
            raise RuntimeError("This build requires MuJoCo simulation; physical execution is disabled")
        if status.get("version") != "1.11.0" or status.get("state") != "running":
            raise RuntimeError("Requires the running SDK 1.11.0 simulator")
        self.check_exclusive()
        from reachy_mini import ReachyMini
        self.mini = ReachyMini(connection_mode="localhost_only", media_backend="no_media",
                              automatic_body_yaw=False, timeout=3, log_level="WARNING")
        self.mini.disable_wobbling()
        self.mini.stop_head_tracking()
        self.mini.enable_motors()
        return status

    def check_exclusive(self):
        lock = api("daemon/robot-app-lock-status")
        if lock.get("state") != "free":
            raise RuntimeError(f"Managed robot controller active: {lock}")
        running = api("move/running")
        if running:
            raise RuntimeError(f"Another motion is running: {running}")

    def pose(self):
        return (self.mini.get_current_head_pose(),
                np.array(self.mini.get_present_antenna_joint_positions()))

    def send(self, frame):
        self.mini.set_target(head=np.array(frame["head"], dtype=np.float64),
                             antennas=frame["antennas"], body_yaw=0.0)

    def neutral(self, stop=None):
        head, antennas = self.pose()
        rv, xyz = rotvec(head[:3, :3]), head[:3, 3].copy()
        duration = transition_duration(head, antennas)
        start = time.perf_counter()
        while True:
            u = 1 if duration == 0 else min(1, (time.perf_counter() - start) / duration)
            w = 1 - (10*u**3 - 15*u**4 + 6*u**5)
            target = np.eye(4)
            target[:3, :3], target[:3, 3] = rotation(rv * w), xyz * w
            self.send({"head": target, "antennas": antennas * w})
            if u == 1:
                break
            if stop is not None and stop.is_set():
                raise InterruptedError("Stopped while initializing neutral")
            time.sleep(.01)
        # Poll actual SDK feedback; a sent neutral command is not success.
        deadline = time.perf_counter() + 1.5
        while time.perf_counter() < deadline:
            head, antennas = self.pose()
            errors = {"head_translation_m": float(np.linalg.norm(head[:3, 3])),
                      "head_rotation_rad": float(np.linalg.norm(rotvec(head[:3, :3]))),
                      "antenna_max_rad": float(np.max(np.abs(antennas)))}
            if errors["head_translation_m"] < .002 and errors["head_rotation_rad"] < .025 and errors["antenna_max_rad"] < .025:
                return {"succeeded": True, "basis": "SDK feedback tolerances", **errors}
            time.sleep(.02)
        return {"succeeded": False, "basis": "SDK feedback outside tolerance", **errors}

    def close(self):
        if self.mini is not None:
            self.mini.__exit__(None, None, None)


class MockRobot:
    def __init__(self):
        self.head, self.antennas = np.eye(4), np.zeros(2)
    def connect(self):
        return {"simulation_enabled": False, "backend": "mock; no robot"}
    def check_exclusive(self):
        pass
    def pose(self):
        return self.head.copy(), self.antennas.copy()
    def send(self, frame):
        self.head, self.antennas = np.array(frame["head"]), np.array(frame["antennas"])
    def neutral(self, stop=None):
        self.head, self.antennas = np.eye(4), np.zeros(2)
        return {"succeeded": True, "basis": "mock only"}
    def close(self):
        pass
