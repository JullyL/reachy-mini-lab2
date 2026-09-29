"""Explicit mock, MuJoCo and physical SDK adapters; never spawns a daemon."""
import json
import time
import urllib.request

import numpy as np

from .motion import rotation, rotvec
from .emotion_player import transition_duration

SDK_VERSION = "1.11.0"


def api(path, host="127.0.0.1"):
    with urllib.request.urlopen(f"http://{host}:8000/api/{path}", timeout=2) as response:
        return json.load(response)


class SDKRobot:
    def __init__(self, backend="sim", host="127.0.0.1", neutral=None):
        self.backend, self.host, self.mini = backend, host, None
        self.neutral_angles = np.zeros(2) if neutral is None else np.asarray(neutral, dtype=float)

    def connect(self):
        status = api("daemon/status", self.host)
        is_sim = status.get("simulation_enabled") is True
        if status.get("mockup_sim_enabled") or is_sim != (self.backend == "sim"):
            raise RuntimeError("Daemon type differs from explicitly selected backend")
        if status.get("version") != SDK_VERSION or status.get("state") != "running":
            raise RuntimeError(f"Requires running SDK {SDK_VERSION}; found {status}")
        self.check_exclusive()
        # Some Python distributions do not execute the GStreamer .pth bootstrap.
        import gstreamer_libs
        gstreamer_libs.setup_python_environment()
        from reachy_mini import ReachyMini
        self.mini = ReachyMini(host=self.host, connection_mode="network", spawn_daemon=False,
                              media_backend="no_media", automatic_body_yaw=False,
                              timeout=3, log_level="WARNING")
        self.mini.disable_wobbling()
        self.mini.stop_head_tracking()
        self.mini.enable_motors()
        return status

    def check_exclusive(self):
        lock = api("daemon/robot-app-lock-status", self.host)
        if lock.get("state") != "free" or api("move/running", self.host):
            raise RuntimeError("Close managed apps and all other motion controllers")

    def pose(self):
        head = self.mini.get_current_head_pose()
        joints, antennas = self.mini.get_current_joint_positions()
        # SDK head joint list: body_rotation followed by six Stewart platform motors.
        return head, np.asarray(antennas), float(joints[0])

    def send(self, frame):
        self.mini.set_target(head=np.asarray(frame["head"], dtype=np.float64),
                             antennas=frame["antennas"], body_yaw=0.0)

    def neutral(self, stop=None):
        head, antennas, body = self.pose()
        rv, xyz = rotvec(head[:3, :3]), head[:3, 3].copy()
        # Ported Emotions prelude duration, with a custom minimum recovery time.
        duration = max(.5, transition_duration(head, antennas, target_antennas=self.neutral_angles),
                       min(1.5, abs(np.rad2deg(body))*.015))
        start = time.perf_counter()
        while True:
            if stop is not None and stop.is_set():
                raise InterruptedError("Stopped while initializing neutral")
            u = min(1, (time.perf_counter()-start)/duration)
            w = 1-(10*u**3-15*u**4+6*u**5)
            target = np.eye(4)
            target[:3, :3], target[:3, 3] = rotation(rv*w), xyz*w
            self.mini.set_target(head=target, antennas=(self.neutral_angles+(antennas-self.neutral_angles)*w).tolist(), body_yaw=body*w)
            if u == 1:
                break
            time.sleep(.01)
        deadline, consecutive = time.perf_counter()+2, 0
        errors = {}
        while time.perf_counter() < deadline:
            head, antennas, body = self.pose()
            errors = {"head_translation_m": float(np.linalg.norm(head[:3, 3])),
                      "head_rotation_deg": float(np.rad2deg(np.linalg.norm(rotvec(head[:3, :3])))),
                      "antenna_error_deg_right_left": np.rad2deg(antennas-self.neutral_angles).tolist(),
                      "body_yaw_deg": float(np.rad2deg(body))}
            finite = np.isfinite([*head.ravel(), *antennas, body]).all()
            good = finite and errors["head_translation_m"] <= .002 and errors["head_rotation_deg"] <= 2 and max(abs(x) for x in errors["antenna_error_deg_right_left"]) <= 2 and abs(errors["body_yaw_deg"]) <= 2
            consecutive = consecutive+1 if good else 0
            if consecutive >= 5:
                return {"succeeded": True, "basis": "five SDK feedback polls within tolerance", **errors}
            time.sleep(.02)
        return {"succeeded": False, "basis": "SDK feedback outside tolerance", **errors}

    def close(self):
        if self.mini is not None:
            self.mini.__exit__(None, None, None)


class MockRobot:
    backend = "mock"
    host = "none"

    def __init__(self, neutral=None):
        self.neutral_angles = np.zeros(2) if neutral is None else np.asarray(neutral)
        self.head, self.antennas, self.body = np.eye(4), self.neutral_angles.copy(), 0.0

    def connect(self):
        return {"backend": "mock; command echo only, no robot physics"}

    def check_exclusive(self):
        pass

    def pose(self):
        return self.head.copy(), self.antennas.copy(), self.body

    def send(self, frame):
        self.head, self.antennas = np.asarray(frame["head"]), np.asarray(frame["antennas"])
        self.body = frame["body_yaw"]

    def neutral(self, stop=None):
        if stop is not None and stop.is_set():
            raise InterruptedError("Stopped")
        self.head, self.antennas, self.body = np.eye(4), self.neutral_angles.copy(), 0.0
        return {"succeeded": True, "basis": "mock command echo only"}

    def close(self):
        pass
