"""Single-controller monotonic trial scheduler and append-only evidence."""
import hashlib
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
from .choreography import compile_performance, STUDY_VERSION

ROOT = Path(__file__).resolve().parents[1]
CONTROL_PORT = 18731


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Controller:
    """Exclusive local TCP endpoint: blocks duplicate app processes across copies.

    External SDK tools do not honor this lock; the operator must close them.
    Managed apps and daemon motions are checked separately by SimRobot.
    """
    def __enter__(self):
        self.stop = threading.Event()
        self.events = queue.SimpleQueue()
        self.closed = threading.Event()
        self.server = socket.socket()
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            self.server.bind(("127.0.0.1", CONTROL_PORT))
            self.server.listen(4)
            self.server.settimeout(.1)
        except OSError:
            self.server.close()
            raise RuntimeError("Another trial controller is active (port 18731)") from None
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
                    if command in {"stop", "repeat_prompt", "operator_error"}:
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
        self.records = []

    def event(self, marker, at=None, **values):
        at = time.perf_counter() if at is None else at
        record = {**self.metadata, "marker": marker, "monotonic_s": at,
                  "wall_time_utc": datetime.fromtimestamp(self.wall + at - self.origin, timezone.utc).isoformat(),
                  "elapsed_s": None if self.accepted is None else at - self.accepted, **values}
        self.records.append(record)
        self.file.write(json.dumps(record, allow_nan=False) + "\n")
        self.file.flush()
        elapsed = "pre" if record["elapsed_s"] is None else f"{record['elapsed_s']:.3f}s"
        print(f"{record['wall_time_utc']} {marker} {elapsed}", flush=True)

    def close(self):
        self.file.close()


def run_trial(robot, control, condition, question_id, log_dir, *, participant="TECH",
              order="", condition_position=0, sequence=1, session_id="", repeat_of="",
              accept=None, silent=False, stop_after=None):
    config = load_json(ROOT / "config/conditions.json")
    questions = load_json(ROOT / "config/questions.json")
    question = next(q for q in questions["questions"] if q["id"] == question_id)
    delay = config["cue_start_s"]
    answer_path = ROOT / question["audio"]
    if question.get("answer_text_sha256") and hashlib.sha256(question["answer"].encode("utf-8")).hexdigest() != question["answer_text_sha256"]:
        raise ValueError("Answer text changed: capture matching backend audio and update its choreography before trials")
    if digest(answer_path) != question.get("sha256"):
        raise ValueError("Answer hash mismatch: restore the frozen WAV or bind the new backend capture and choreography")
    rate, samples = read_wav(answer_path)
    if abs(len(samples)/rate - question["duration_s"]) > 1/rate:
        raise ValueError("Answer duration does not match frozen WAV")
    gesture = compile_performance(question, {**config, "selected_condition": condition})
    log = TrialLog(log_dir, {"study_version": STUDY_VERSION,
                            "condition": condition, "expressive_motion": config["conditions"][condition],
                            "cue_start_s": delay, "parameter_units": config["units"],
                            "question_id": question_id, "answer_asset_id": question["answer_asset_id"],
                            "answer_sha256": digest(answer_path), "gesture_sha256": gesture["sha256"],
                            "motion_source_hashes": gesture["source_hashes"],
                            "choreography_reviewed": gesture["score"].get("reviewed", False),
                            "choreography_timing_basis": gesture["timing_basis"],
                            "speech_motion":gesture["speech_motion"],
                            "speech_alignment_sha256":gesture["score"]["alignment_sha256"],
                            "participant_id": participant, "condition_order": order,
                            "condition_position": condition_position, "trial_sequence": sequence,
                            "session_id": session_id, "repeat_of": repeat_of,
                            "input_mode": "operator-mediated" if accept else "automated technical test", "silent": silent,
                            "robot_backend": type(robot).__name__, "answer_preparation": questions["preparation"]})
    output = AudioOutput(rate, samples, silent)
    status, error, recovery, cue_at, speech_at, observed_at = "failed", None, None, None, None, None
    frame_deviations, speech_end, prompt_count, stop_timer = [], None, 0, None
    speech_feedback = {"samples":0, "peak_head_rad":0.0, "peak_antenna_rad":0.0}
    try:
        log.event("TRIAL_START", cue_target_s=delay, speech_target_s=config["speech_target_s"])
        robot.check_exclusive()
        initial = robot.neutral(control.stop)
        log.event("INITIAL_NEUTRAL", **initial)
        if not initial["succeeded"]:
            raise RuntimeError("Initial neutral was not confirmed")
        output.open()
        print(f"{question_id}: {question['question']}", flush=True)
        if accept:
            accept()
        if control.stop.is_set():
            raise InterruptedError("Stop before acceptance")
        log.accepted = time.perf_counter()
        log.event("QUESTION_ACCEPTED", at=log.accepted)
        output.arm(log.accepted + config["speech_target_s"])
        if stop_after is not None:
            stop_timer = threading.Timer(stop_after, control.stop.set)
            stop_timer.start()
        frame_index, next_feedback, state_index = 0, 0.0, 0
        while True:
            now = time.perf_counter()
            elapsed = now - log.accepted
            output.poll_silent(now)
            while not output.events.empty():
                marker, at, info = output.events.get()
                if marker == "AUDIO_ERROR":
                    raise RuntimeError(info["error"])
                if marker == "SPEECH_START":
                    speech_at = at
                    info["deviation_s"] = at - log.accepted - config["speech_target_s"]
                elif marker == "SPEECH_END":
                    speech_end = at
                log.event(marker, at=at, **info)
            while not control.events.empty():
                name, at = control.events.get()
                eligible = log.accepted <= at and (speech_at is None or at < speech_at)
                if name == "repeat_prompt" and eligible:
                    prompt_count += 1
                log.event("OPERATOR_EVENT", at=at, event=name, in_waiting_interval=eligible)
            if control.stop.is_set():
                log.event("STOP_REQUESTED")
                raise InterruptedError("Operator or validation stop")
            if state_index < len(gesture["cues"]) and elapsed >= gesture["cues"][state_index]["start_s"]:
                log.event("EXPRESSION_STATE", **gesture["cues"][state_index])
                state_index += 1
            if frame_index < len(gesture["time"]) and elapsed >= gesture["time"][frame_index]:
                # Do not dump overdue frames in a burst after a scheduling stall.
                desired = int(np.searchsorted(gesture["time"], elapsed, side="right") - 1)
                desired = min(desired, len(gesture["time"]) - 1)
                if desired > frame_index:
                    log.event("FRAME_SKIP", count=desired - frame_index)
                frame_index = desired
                dispatched = time.perf_counter()
                robot.send(gesture["set_target_data"][frame_index])
                if cue_at is None and elapsed >= delay:
                    cue_at = dispatched
                    log.event("CUE_START", at=dispatched, basis="first trajectory command dispatch",
                              deviation_s=dispatched - log.accepted - delay)
                frame_deviations.append(dispatched - log.accepted - gesture["time"][frame_index])
                frame_index += 1
                if frame_index == len(gesture["time"]):
                    log.event("PERFORMANCE_END", basis="final neutral trajectory command dispatched")
            if elapsed >= next_feedback:
                head, antennas = robot.pose()
                if speech_at is not None and now >= speech_at:
                    speech_feedback["samples"] += 1
                    speech_feedback["peak_head_rad"] = max(speech_feedback["peak_head_rad"],float(np.linalg.norm(rotvec(head[:3,:3]))))
                    speech_feedback["peak_antenna_rad"] = max(speech_feedback["peak_antenna_rad"],float(np.max(np.abs(antennas))))
                moved = float(np.linalg.norm(rotvec(head[:3, :3]))) > .004 or float(np.max(np.abs(antennas))) > .004
                if cue_at is not None and observed_at is None and moved:
                    observed_at = time.perf_counter()
                    log.event("CUE_OBSERVED", at=observed_at,
                              basis="SDK feedback exceeds 0.004 rad; poll and transport latency included",
                              deviation_s=observed_at - log.accepted - delay)
                next_feedback = elapsed + .01
            if speech_end is not None and now >= speech_end:
                break
            if elapsed > config["speech_target_s"] + len(samples) / rate + 3:
                raise TimeoutError("Audio did not complete")
            control.stop.wait(.002)
        if cue_at is None or speech_at is None or observed_at is None:
            raise RuntimeError("Missing required cue or speech onset evidence")
        status = "completed"
    except (KeyboardInterrupt, InterruptedError) as exc:
        control.stop.set()
        status, error = "interrupted", str(exc) or "KeyboardInterrupt"
    except Exception as exc:
        status, error = "failed", f"{type(exc).__name__}: {exc}"
        log.event("ERROR", error=error)
    finally:
        if stop_timer:
            stop_timer.cancel()
        try:
            output.stop()
        except Exception as exc:
            log.event("ERROR", error=f"Audio stop: {exc}")
            status = "failed"
        log.event("RETURN_TO_NEUTRAL")
        try:
            recovery = robot.neutral()
        except Exception as exc:
            recovery = {"succeeded": False, "error": str(exc)}
        log.event("NEUTRAL_RESULT", **recovery)
        if not recovery["succeeded"]:
            status = "failed"
        cue_dev = None if cue_at is None else cue_at - log.accepted - delay
        speech_dev = None if speech_at is None else speech_at - log.accepted - config["speech_target_s"]
        timing_ok = all(v is not None and abs(v) <= config["timing_tolerance_s"] for v in [cue_dev, speech_dev])
        skips = sum(r.get("count", 0) for r in log.records if r["marker"] == "FRAME_SKIP")
        operator_error = any(r.get("event") == "operator_error" for r in log.records)
        prompt_count = sum(r.get("event") == "repeat_prompt" and log.accepted is not None
                           and r["monotonic_s"] >= log.accepted
                           and (speech_at is None or r["monotonic_s"] < speech_at)
                           for r in log.records)
        from .robot import SimRobot
        study_valid = status == "completed" and timing_ok and not skips and not operator_error and not silent and isinstance(robot, SimRobot)
        log.event("TRIAL_END", completion_status=status, error=error,
                  neutral_recovery_succeeded=recovery["succeeded"],
                  cue_deviation_s=cue_dev, speech_deviation_s=speech_dev,
                  actual_cue_observed_s=None if observed_at is None else observed_at-log.accepted,
                  max_frame_deviation_s=max(frame_deviations, default=None), skipped_frames=skips,
                  timing_ok=timing_ok, technically_valid=study_valid,
                  speech_motion_feedback=speech_feedback,
                  repeat_prompt_count=prompt_count,
                  acceptance_to_end_s=None if log.accepted is None else time.perf_counter()-log.accepted)
        log.close()
    return log.path, status
