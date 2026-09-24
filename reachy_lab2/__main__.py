import argparse
import asyncio
import json
import re
import time
import uuid

from .robot import MockRobot, SimRobot
from .trial import Controller, ROOT, load_json, run_trial, send_control


def main():
    parser = argparse.ArgumentParser(description="Reachy Lab 2: brief cue versus emotional performance")
    sub = parser.add_subparsers(dest="command", required=True)
    trial = sub.add_parser("trial")
    trial.add_argument("--condition", choices=["A", "B"], required=True)
    trial.add_argument("--question", default="q1")
    trial.add_argument("--auto-accept", action="store_true", help="Technical validation only; no human question")
    trial.add_argument("--stop-after", type=float, help="Technical interruption test, seconds after acceptance")
    session = sub.add_parser("session")
    session.add_argument("--participant", required=True)
    session.add_argument("--condition", choices=["A", "B"], required=True)
    session.add_argument("--repeat-of", default="", help="Previous condition session ID; retains original logs")
    for p in (trial, session):
        p.add_argument("--backend", choices=["sim", "mock"], default="sim")
        p.add_argument("--silent", action="store_true", help="Explicit no-audio technical test, never study-valid")
        p.add_argument("--log-dir", default=str(ROOT / "logs"))
    sub.add_parser("stop")
    mark = sub.add_parser("mark")
    mark.add_argument("kind", choices=["repeat_prompt", "operator_error"])
    sub.add_parser("devices")
    from .choreography import STATES
    emotion = sub.add_parser("emotion", help="Preview one named emotional performance in the simulator")
    emotion.add_argument("--state", choices=sorted(STATES), required=True)
    emotion.add_argument("--duration", type=float, default=3.0)
    live = sub.add_parser("live", help="Actual Conversation App input/backend with emotional motion; not study data")
    source = live.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Text question; tests backend but not microphone")
    source.add_argument("--input-device", type=int, help="Explicit microphone number from devices")
    source.add_argument("--audio-file", help="Upload a mono PCM16 16kHz WAV; not a microphone test")
    live.add_argument("--seconds", type=float, default=6, help="Push-to-talk capture length, 1-30 seconds")
    live.add_argument("--out", default=None, help="New capture directory")
    live.add_argument("--capture-only", action="store_true", help="Save backend answer without playing it")
    args = parser.parse_args()
    if args.command in {"stop", "mark"}:
        print(send_control("stop" if args.command == "stop" else args.kind))
        return 0
    if args.command == "devices":
        import sounddevice
        print(sounddevice.query_devices())
        return 0
    if args.command == "emotion":
        from .choreography import EmotionLibrary, frame, HZ
        clip = EmotionLibrary().clip(args.state, args.duration)
        with Controller() as control:
            robot = SimRobot()
            try:
                print(json.dumps(robot.connect()))
                if not robot.neutral(control.stop)["succeeded"]:
                    raise RuntimeError("Initial neutral not confirmed")
                start = time.perf_counter()
                index = 0
                while index < len(clip) and not control.stop.is_set():
                    index = min(int((time.perf_counter()-start)*HZ),len(clip)-1)
                    robot.send(frame(clip[index]))
                    if index == len(clip)-1:
                        break
                    control.stop.wait(1/HZ)
                return 2 if control.stop.is_set() else 0
            finally:
                try:
                    if robot.mini is not None and not robot.neutral()["succeeded"]:
                        raise RuntimeError("Emotion preview neutral recovery failed")
                finally:
                    robot.close()
    if args.command == "live":
        from .live import live_turn
        with Controller() as control:
            robot = SimRobot()
            try:
                print(json.dumps(robot.connect()))
                destination = args.out or str(ROOT / "captures" / str(uuid.uuid4()))
                asyncio.run(live_turn(robot, control, destination, text=args.text,
                    input_device=args.input_device, input_wav=args.audio_file, seconds=args.seconds, capture_only=args.capture_only))
                return 0
            finally:
                robot.close()
    with Controller() as control:
        robot = SimRobot() if args.backend == "sim" else MockRobot()
        try:
            print(json.dumps(robot.connect()))
            if args.command == "trial":
                accept = None if args.auto_accept else lambda: input("After the complete question, press Enter to accept. Ctrl+C stops. ")
                path, status = run_trial(robot, control, args.condition, args.question, args.log_dir,
                                         accept=accept, silent=args.silent, stop_after=args.stop_after)
                print(f"{status}: {path}")
                return 0 if status == "completed" else 2
            if not re.fullmatch(r"P\d{2,3}", args.participant):
                raise ValueError("Use a de-identified ID such as P01")
            protocol = load_json(ROOT / "study/protocol.json")
            scores = load_json(ROOT / "config/choreography.json")["questions"]
            if not all(scores[q].get("reviewed") for q in protocol["question_order"]):
                raise ValueError("Listen/watch each B trial and review its score before study sessions. Trials remain available for preview.")
            order = protocol["assignments"][args.participant]
            position = order.index(args.condition) + 1
            print(f"{args.participant}: assigned {order}; condition {position}/2 = {args.condition}")
            print("Check the session sheet: run condition 1 before condition 2; administer HRIES after each.")
            session_id = str(uuid.uuid4())
            print(f"Session ID: {session_id}. Repeats must specify --repeat-of with the original ID.")
            input("Confirm neutral script, observer ready, and condition order recorded; press Enter. ")
            for seq, question in enumerate(protocol["question_order"], 1):
                if control.stop.is_set():
                    return 2
                path, status = run_trial(robot, control, args.condition, question, args.log_dir,
                    participant=args.participant, order=order, condition_position=position, sequence=seq,
                    session_id=session_id, repeat_of=args.repeat_of,
                    accept=lambda: input("Participant asks the displayed question; Enter immediately after completion. "),
                    silent=args.silent)
                print(f"{status}: {path}")
                if status != "completed":
                    print("Condition interrupted. Preserve logs and document whether the whole condition will be repeated.")
                    return 2
                if seq < len(protocol["question_order"]):
                    if control.stop.wait(protocol["intertrial_pause_s"]):
                        return 2
            print("Condition complete. Administer all 16 HRIES items, the expression check, and the open question now.")
            return 0
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
