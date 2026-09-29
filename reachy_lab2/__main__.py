"""Operator CLI for the fixed greeting; no microphone or live generation path."""
import argparse
import json
import re
from pathlib import Path

import numpy as np

from .greeting import require_physical_review, settings, software_digest
from .robot import MockRobot, SDKRobot
from .trial import Controller, ROOT, digest, load_json, run_trial, send_control


def previous_attempts(directory, participant):
    rows = []
    for path in Path(directory).glob("*.jsonl"):
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if records and records[0].get("participant_id") == participant:
            if records[-1]["marker"] != "TRIAL_END":
                raise ValueError("Incomplete earlier log: document recovery before continuing")
            rows.append(records[-1])
    return rows


def session_attempt(rows, condition, order, repeat_of):
    prior = [r for r in rows if r["condition"] == condition]
    position = order.index(condition)+1
    if position == 2 and not any(r["condition"] == order[0] and r["completion"] == 1 for r in rows):
        raise ValueError("Complete the assigned first condition before the second")
    if any(r["completion"] == 1 for r in prior):
        raise ValueError("Use the first completed attempt; do not repeat based on ratings")
    if len(prior) >= 2:
        raise ValueError("Only one replacement attempt is permitted")
    if prior and repeat_of != prior[0]["trial_id"]:
        raise ValueError("Replacement requires --repeat-of with the original failed/interrupted trial ID")
    if not prior and repeat_of:
        raise ValueError("No original attempt matches --repeat-of")
    return position, len(prior)+1


def main():
    parser = argparse.ArgumentParser(description="Reachy Mini antenna-amplitude greeting")
    sub = parser.add_subparsers(dest="command", required=True)
    trial = sub.add_parser("trial", help="Technical preview, never participant data")
    session = sub.add_parser("session", help="One participant condition; physical review required")
    for p in (trial, session):
        p.add_argument("--condition", choices=["A", "B"], required=True)
        p.add_argument("--backend", choices=["mock", "sim", "physical"], default="sim")
        p.add_argument("--host", default="127.0.0.1", help="Explicit daemon host; physical: reachy-mini.local")
        p.add_argument("--audio-device", type=int)
        p.add_argument("--log-dir", default=str(ROOT/"logs"))
    trial.add_argument("--silent", action="store_true")
    trial.add_argument("--auto-accept", action="store_true")
    trial.add_argument("--stop-after", type=float)
    trial.add_argument("--commissioning", action="store_true", help="Technical half-amplitude 5/15 degree cycle")
    trial.add_argument("--physical-check", action="store_true", help="Explicit full-amplitude technical physical validation")
    session.add_argument("--participant", required=True)
    session.add_argument("--operator", required=True)
    session.add_argument("--repeat-of", default="")
    session.add_argument("--deviation", default="")
    sub.add_parser("stop")
    mark = sub.add_parser("mark")
    mark.add_argument("kind", choices=["operator_error", "interruption"])
    sub.add_parser("devices")
    sub.add_parser("fingerprint", help="Print hashes for a completed physical review record")
    args = parser.parse_args()
    if args.command in {"stop", "mark"}:
        print(send_control("stop" if args.command == "stop" else args.kind))
        return 0
    if args.command == "devices":
        import sounddevice
        print(sounddevice.query_devices())
        return 0
    if args.command == "fingerprint":
        print(json.dumps({"configuration_sha256": digest(ROOT/"config/conditions.json"),
            "calibration_sha256": digest(ROOT/"config/calibration.json"),
            "audio_sha256": digest(ROOT/settings()["audio"]), "software_sha256": software_digest()}, indent=2))
        return 0
    study = args.command == "session"
    if study:
        if args.backend != "physical":
            raise ValueError("Participant sessions require the physical robot")
        require_physical_review()
        if not re.fullmatch(r"P\d{2,3}", args.participant):
            raise ValueError("Use a de-identified participant ID")
        protocol = load_json(ROOT/"study/protocol.json")
        order = protocol["assignments"][args.participant]
    elif args.backend == "physical" and not (args.commissioning or args.physical_check):
        raise ValueError("Physical technical trials require --commissioning or --physical-check")
    calibration = load_json(ROOT/"config/calibration.json")
    neutral = np.deg2rad(calibration["neutral_deg_right_left"]) if args.backend == "physical" else np.zeros(2)
    with Controller() as control:
        if study:
            position, attempt = session_attempt(previous_attempts(args.log_dir, args.participant), args.condition, order, args.repeat_of)
        robot = MockRobot(neutral) if args.backend == "mock" else SDKRobot(args.backend, args.host, neutral)
        try:
            print(json.dumps(robot.connect()))
            if study:
                print(f"{args.participant}: greeting {position}/2; assigned order {order}; attempt {attempt}")
                if position == 2:
                    input("After first-condition questionnaires, press Enter to begin the 30-second neutral reset. ")
                    if not robot.neutral(control.stop)["succeeded"] or control.stop.wait(30):
                        raise InterruptedError("Neutral reset did not complete")
                accept = lambda: input("Read the fixed instructions; confirm agreement, observer and room ready. Enter starts one greeting. ")
            else:
                accept = None if args.auto_accept else lambda: input("Ready for one technical greeting; Enter starts, Ctrl+C stops. ")
            path, status = run_trial(robot, control, args.condition, args.log_dir,
                participant=args.participant if study else "TECH", order=order if study else "",
                position=position if study else 0, attempt=attempt if study else 1,
                repeat_of=args.repeat_of if study else "", accept=accept,
                silent=False if study else args.silent, stop_after=None if study else args.stop_after,
                commissioning=False if study else args.commissioning, audio_device=args.audio_device,
                operator=args.operator if study else "TECH", deviation=args.deviation if study else "")
            print(f"{status}: {path}")
            if study:
                print("Record trial ID and outcome. After completion collect HRIES, valence, arousal, open response, then movement-size rating.")
            return 0 if status == "completed" else 2
        finally:
            robot.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Stopped.")
        raise SystemExit(2)
    except Exception as exc:
        print(f"Cannot run: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
