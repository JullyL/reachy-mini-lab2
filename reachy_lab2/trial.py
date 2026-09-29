"""Single-controller monotonic trial scheduler and append-only evidence."""
import hashlib
import errno
import json
import queue
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .audio import AudioOutput
from .conversation_audio import read_wav
from .motion import rotvec


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PORT = 18731


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Controller:
    """Exclusive local TCP endpoint: blocks duplicate app processes across copies.

    External SDK tools do not honor this lock; the operator must close them.
    Managed apps and daemon motions are checked separately by SDKRobot.
    """
    def __enter__(self):
        self.stop = threading.Event()
        self.events = queue.SimpleQueue()
        self.closed = threading.Event()
        self.server = socket.socket()
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            # Reopen after TCP TIME_WAIT; an active listening socket still excludes us.
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind(("127.0.0.1", CONTROL_PORT))
            self.server.listen(4)
            self.server.settimeout(.1)
        except OSError as exc:
            self.server.close()
            if exc.errno == errno.EADDRINUSE:
                raise RuntimeError("Another trial controller is active (port 18731)") from None
            raise RuntimeError(f"Cannot bind local stop-control port 18731: {exc}") from exc
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        return self

    def _listen(self):
        while not self.closed.is_set():
            try:
                conn, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with conn:
                conn.settimeout(.2)
                try:
                    command = conn.recv(128).decode().strip()
                    if command == "stop":
                        self.stop.set()
                    if command in {"stop", "operator_error", "interruption"}:
                        self.events.put((command, time.perf_counter()))
                        conn.sendall(b"recorded\n")
                    else:
                        conn.sendall(b"unknown command\n")
                except (OSError, UnicodeError):
                    pass

    def __exit__(self, *args):
        self.closed.set()
        self.server.close()
        self.thread.join(timeout=.3)


def send_control(command):
    with socket.create_connection(("127.0.0.1", CONTROL_PORT), timeout=1) as conn:
        conn.sendall(command.encode())
        return conn.recv(128).decode().strip()


class TrialLog:
    def __init__(self, directory, metadata):
        self.id = str(uuid.uuid4())
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.path = Path(directory) / (self.id + ".jsonl")
        self.file = self.path.open("x", encoding="utf-8")
        self.origin = time.perf_counter()
        self.wall = time.time()
        self.accepted = None
        self.metadata = {"trial_id": self.id, **metadata}

    def event(self, marker, at=None, **values):
        at = time.perf_counter() if at is None else at
        record = {**self.metadata, "marker": marker, "monotonic_s": at,
                  "wall_time_utc": datetime.fromtimestamp(self.wall + at - self.origin, timezone.utc).isoformat(),
                  "elapsed_s": None if self.accepted is None else at - self.accepted, **values}
        self.file.write(json.dumps(record, allow_nan=False) + "\n")
        self.file.flush()
        elapsed = "pre" if record["elapsed_s"] is None else f"{record['elapsed_s']:.3f}s"
        if marker not in {"FEEDBACK", "COMMAND"}:
            print(f"{record['wall_time_utc']} {marker} {elapsed}", flush=True)

    def close(self):
        self.file.close()


def summarize_feedback(rows, baseline, amplitude, cfg):
    """Separate right/left measured excursions; never infer delivery from commands."""
    if len(rows) < 2:
        return {"verified": False, "reason": "insufficient feedback", "samples": len(rows)}
    times = np.array([r["elapsed_s"] for r in rows])
    angles = np.array([r["angles_deg_right_left"] for r in rows])-baseline
    moving = (times >= 1) & (times <= 5.05)
    if moving.sum() < 2:
        return {"verified": False, "reason": "no movement interval feedback"}
    actual = angles[moving]
    gaps = np.diff(times)
    peaks, ranges = np.max(np.abs(actual), axis=0), np.ptp(actual, axis=0)
    rate = (len(rows)-1)/(times[-1]-times[0])
    head_ok = all(r["head_translation_m"] <= cfg["head_translation_tolerance_m"] and
                  r["head_rotation_deg"] <= cfg["head_rotation_tolerance_deg"] and
                  abs(r["body_yaw_deg"]) <= cfg["body_yaw_tolerance_deg"] for r in rows)
    error = max(r["tracking_error_deg"] for r in rows)
    tolerance = cfg["excursion_tolerance_deg"]
    # Both signed lobes, not just one absolute peak, must actually occur.
    excursion_ok = np.all(np.abs(np.max(actual, axis=0)-amplitude) <= tolerance) and np.all(np.abs(np.min(actual, axis=0)+amplitude) <= tolerance)
    return {"verified": bool(rate >= cfg["minimum_feedback_hz"] and np.max(gaps) <= .1 and head_ok and excursion_ok),
            "basis": "measured joint feedback; mock backend is command echo only",
            "samples": len(rows), "achieved_poll_hz": float(rate), "max_poll_gap_s": float(max(gaps)),
            "right": {"maximum_abs_displacement_deg": float(peaks[0]), "range_deg": float(ranges[0])},
            "left": {"maximum_abs_displacement_deg": float(peaks[1]), "range_deg": float(ranges[1])},
            "stationary_head_base": bool(head_ok), "max_tracking_error_deg": float(error),
            "tracking_error_basis": "unlagged command-to-feedback diagnostic; not an excursion acceptance threshold",
            "right_positive_peak_s": float(times[moving][np.argmax(actual[:, 0])]),
            "right_negative_peak_s": float(times[moving][np.argmin(actual[:, 0])]),
            "left_positive_peak_s": float(times[moving][np.argmax(actual[:, 1])]),
            "left_negative_peak_s": float(times[moving][np.argmin(actual[:, 1])])}


def run_trial(robot, control, condition, log_dir, *, participant="TECH", order="", position=0,
              attempt=1, repeat_of="", accept=None, silent=False, stop_after=None,
              commissioning=False, audio_device=None, operator="", deviation=""):
    from .greeting import STUDY_VERSION, compile_greeting, settings, software_digest, require_physical_review
    if participant != "TECH":
        require_physical_review()
        if robot.backend != "physical" or silent or commissioning or accept is None:
            raise ValueError("Participant trials require reviewed physical, audible operator-triggered execution")
    cfg = settings()
    asset = ROOT / cfg["audio"]
    receipt = load_json(ROOT / "assets/greeting/manifest.json")
    if digest(asset) != receipt["sha256"]:
        raise ValueError("Frozen greeting WAV hash mismatch")
    rate, samples = read_wav(asset)
    duration = len(samples)/rate
    if not 0 < duration <= 4 or receipt["text"] != "Hello, nice to meet you":
        raise ValueError("Greeting must fit inside the four-second movement interval")
    gesture = compile_greeting(condition, cfg, robot.neutral_angles, commissioning)
    log = TrialLog(log_dir, {"study_version": STUDY_VERSION, "condition": condition,
        "antenna_amplitude_deg": gesture["amplitude_deg"], "provisional": cfg["provisional"],
        "condition_order": order, "condition_position": position, "participant_id": participant,
        "attempt": attempt, "repeat_of": repeat_of, "operator": operator, "protocol_deviation": deviation,
        "robot_backend": robot.backend, "robot_host": robot.host,
        "silent": silent, "commissioning": commissioning, "input_mode": "operator" if accept else "technical",
        "audio_sha256": digest(asset), "audio_device_requested": audio_device, "audio_duration_s": duration,
        "configuration_sha256": digest(ROOT / "config/conditions.json"), "settings": cfg,
        "calibration_sha256": digest(ROOT / "config/calibration.json"),
        "software_sha256": software_digest(), "trajectory_sha256": gesture["sha256"],
        "neutral_target_deg_right_left": np.rad2deg(robot.neutral_angles).tolist()})
    output = AudioOutput(rate, samples, silent, device=audio_device)
    status, error, recovery, baseline = "failed", None, {"succeeded": False}, None
    feedback, deviations = [], []
    speech_start, speech_end, movement_start, movement_end = None, None, None, None
    timer, skips, intervention = None, 0, False
    observed_start = None
    try:
        log.event("TRIAL_START")
        robot.check_exclusive()
        initial = robot.neutral(control.stop)
        log.event("INITIAL_NEUTRAL", **initial)
        if not initial["succeeded"]:
            raise RuntimeError("Initial neutral not confirmed")
        # Average five actual neutral samples before the common one-second hold.
        neutral_samples = []
        for _ in range(5):
            if control.stop.wait(.02):
                raise InterruptedError("Stopped during neutral calibration")
            head, antennas, body = robot.pose()
            neutral_samples.append(np.rad2deg(antennas))
        baseline = np.mean(neutral_samples, axis=0)
        if not np.isfinite(baseline).all() or np.max(np.abs(baseline-np.rad2deg(robot.neutral_angles))) > 2:
            raise RuntimeError("Measured baseline is not calibrated neutral")
        log.event("BASELINE", measured_neutral_deg_right_left=baseline.tolist(), raw_samples_deg= [a.tolist() for a in neutral_samples])
        output.open()
        log.event("AUDIO_DEVICE", **output.device_info)
        if accept:
            accept()
        if control.stop.is_set():
            raise InterruptedError("Stop before greeting")
        log.accepted = time.perf_counter()
        log.event("PRE_HOLD_START", at=log.accepted)
        output.arm(log.accepted+1)
        if stop_after is not None:
            timer = threading.Timer(stop_after, control.stop.set)
            timer.start()
        index, next_feedback = 0, 0
        while True:
            now = time.perf_counter()
            elapsed = now-log.accepted
            output.poll_silent(now)
            while not output.events.empty():
                marker, at, info = output.events.get()
                log.event(marker, at=at, **info)
                if marker == "AUDIO_ERROR":
                    raise RuntimeError(info["error"])
                if marker == "SPEECH_START":
                    speech_start = at-log.accepted
                elif marker == "SPEECH_END":
                    speech_end = at-log.accepted
            while not control.events.empty():
                name, at = control.events.get()
                log.event("OPERATOR_EVENT", at=at, event=name)
                intervention = True
                if name == "interruption":
                    control.stop.set()
            if control.stop.is_set():
                log.event("STOP_REQUESTED")
                raise InterruptedError("Operator/technical stop")
            if index < len(gesture["time"]) and elapsed >= gesture["time"][index]:
                desired = min(int(elapsed*50), 300)
                if desired > index:
                    skips += desired-index
                    log.event("FRAME_SKIP", count=desired-index)
                index = desired
                dispatched = time.perf_counter()
                robot.send(gesture["set_target_data"][index])
                deviations.append(dispatched-log.accepted-gesture["time"][index])
                log.event("COMMAND", at=dispatched, scheduled_s=gesture["time"][index],
                          antennas_rad_right_left=gesture["set_target_data"][index]["antennas"])
                if movement_start is None and index >= 50:
                    movement_start = dispatched-log.accepted
                    log.event("MOVEMENT_START", at=dispatched, basis="dispatch; actual angle samples logged separately")
                if movement_end is None and index >= 250:
                    movement_end = dispatched-log.accepted
                    log.event("MOVEMENT_END", at=dispatched)
                    log.event("POST_HOLD_START", at=dispatched)
                index += 1
            if elapsed >= next_feedback:
                head, antennas, body = robot.pose()
                measured_at = time.perf_counter()
                if not np.isfinite([*np.asarray(head).ravel(), *antennas, body]).all():
                    raise RuntimeError("Nonfinite feedback")
                target_index = min(max(index-1, 0), 300)
                target = np.asarray(gesture["set_target_data"][target_index]["antennas"])
                row = {"elapsed_s": measured_at-log.accepted,
                    "angles_deg_right_left": np.rad2deg(antennas).tolist(),
                    "head_translation_m": float(np.linalg.norm(head[:3, 3])),
                    "head_rotation_deg": float(np.rad2deg(np.linalg.norm(rotvec(head[:3, :3])))),
                    "body_yaw_deg": float(np.rad2deg(body)),
                    "tracking_error_deg": float(np.max(np.abs(np.rad2deg(antennas-target))))}
                if observed_start is None and elapsed >= 1 and max(abs(x) for x in np.asarray(row["angles_deg_right_left"])-baseline) > .5:
                    observed_start = measured_at-log.accepted
                    log.event("MOVEMENT_OBSERVED", at=measured_at, threshold_deg=.5, basis="SDK feedback; includes transport and threshold-crossing delay")
                feedback.append(row)
                log.event("FEEDBACK", at=measured_at, **row)
                next_feedback = elapsed+1/cfg["feedback_hz"]
            if elapsed >= 6 and index >= 301 and speech_end is not None and elapsed >= speech_end:
                log.event("CYCLE_END")
                break
            if elapsed > 7:
                raise TimeoutError("Greeting/audio failed to complete on schedule")
            control.stop.wait(.001)
        if intervention:
            raise RuntimeError("Operator intervention during greeting")
        # Completion checks the scheduled endpoint BEFORE cleanup can repair it.
        if max(abs(x) for x in np.asarray(feedback[-1]["angles_deg_right_left"])-baseline) > 2:
            raise RuntimeError("Scheduled endpoint outside ±2 degrees of measured neutral")
        status = "completed"
    except (KeyboardInterrupt, InterruptedError) as exc:
        control.stop.set()
        status, error = "interrupted", str(exc) or "KeyboardInterrupt"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        log.event("ERROR", error=error)
    finally:
        if timer:
            timer.cancel()
        try:
            output.stop()
        except Exception as exc:
            status, error = "failed", f"Audio stop failed: {exc}"
        log.event("RETURN_TO_NEUTRAL")
        try:
            recovery = robot.neutral()
        except Exception as exc:
            recovery = {"succeeded": False, "error": str(exc)}
        log.event("NEUTRAL_RESULT", **recovery)
        if not recovery["succeeded"]:
            status = "failed"
        movement = summarize_feedback(feedback, baseline, gesture["amplitude_deg"], cfg) if baseline is not None else {"verified": False}
        timing_ok = (speech_start is not None and movement_start is not None and movement_end is not None and
            abs(speech_start-1) <= cfg["timing_tolerance_s"] and abs(movement_start-1) <= cfg["timing_tolerance_s"] and
            abs(movement_end-5) <= cfg["timing_tolerance_s"] and abs(speech_start-movement_start) <= cfg["timing_tolerance_s"] and
            max(deviations, default=1) <= cfg["timing_tolerance_s"] and skips == 0)
        verified = status == "completed" and timing_ok and movement["verified"]
        # Fidelity faults invalidate completion, independent of participants' ratings.
        if status == "completed" and not verified:
            status, error = "failed", "Movement or timing verification failed"
        log.event("TRIAL_END", completion_status=status, completion=int(status == "completed"), error=error,
            neutral_recovery_succeeded=recovery["succeeded"], measured_movement=movement,
            observed_movement_start_s=observed_start, speech_start_s=speech_start, speech_end_s=speech_end, movement_start_s=movement_start, movement_end_s=movement_end,
            synchronization_error_s=None if speech_start is None or movement_start is None else speech_start-movement_start,
            skipped_frames=skips, max_dispatch_deviation_s=max(deviations, default=None), timing_ok=timing_ok,
            software_checks_passed=verified, technically_valid=bool(verified and not silent and robot.backend != "mock"),
            study_eligible=bool(verified and not silent and robot.backend == "physical" and not commissioning and participant != "TECH"))
        log.close()
    return log.path, status
