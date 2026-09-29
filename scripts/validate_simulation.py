"""Reproducible real-daemon checks; never physical, never participant data."""
import argparse
import json
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reachy_lab2.trial import send_control

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", default="evidence/verified-run", help="Evidence directory relative to the app root")
args = parser.parse_args()
out = ROOT / args.out
if (out / "summary.json").exists():
    raise RuntimeError("Evidence summary already exists; choose a fresh --out directory to preserve the previous run")
out.mkdir(parents=True, exist_ok=True)
summaries = []
for condition, stop in [("A", None), ("B", None), ("B", 1.8), ("B", 8.0)]:
    command = [sys.executable, "-X", "utf8", "-u", "-m", "reachy_lab2", "trial",
               "--condition", condition, "--question", "q1", "--auto-accept", "--log-dir", str(out)]
    before = set(out.glob("*.jsonl"))
    proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    timers = []
    for line in proc.stdout:
        if any(marker in line for marker in ["CUE_START", "SPEECH_START", "STOP_REQUESTED", "TRIAL_END", "Cannot run"]):
            print(line.rstrip(), flush=True)
        if "QUESTION_ACCEPTED" in line and stop is not None:
            timer = threading.Timer(stop, lambda: send_control("stop"))
            timer.start()
            timers.append(timer)
    code = proc.wait(timeout=10)
    for timer in timers:
        timer.join(timeout=2)
    files = set(out.glob("*.jsonl")) - before
    if len(files) != 1:
        raise RuntimeError("Expected one new trial log")
    path = files.pop()
    records = [json.loads(s) for s in path.read_text().splitlines()]
    end = records[-1]
    expected = "completed" if stop is None else "interrupted"
    assert end["completion_status"] == expected and end["neutral_recovery_succeeded"], end
    assert code == (0 if stop is None else 2), code
    if stop is None:
        assert end["technically_valid"], end
    summaries.append({"file": str(path.relative_to(ROOT)), "condition": condition,
                      "study_version": end["study_version"], "expressive_motion":end["expressive_motion"],
                      "speech_motion_states": [r["state"] for r in records if r["marker"]=="EXPRESSION_STATE" and r["elapsed_s"] >= 5],
                      "speech_motion_feedback":end["speech_motion_feedback"],
                      "requested_stop_s": stop, "trial_id": end["trial_id"],
                      "status": expected, "cue_deviation_s": end["cue_deviation_s"],
                      "cue_observed_s": end["actual_cue_observed_s"],
                      "speech_deviation_s": end["speech_deviation_s"],
                      "neutral_recovery_succeeded": end["neutral_recovery_succeeded"],
                      "answer_sha256": end["answer_sha256"], "gesture_sha256": end["gesture_sha256"]})
assert summaries[0]["answer_sha256"] == summaries[1]["answer_sha256"]
assert summaries[0]["gesture_sha256"] != summaries[1]["gesture_sha256"]
assert not summaries[0]["speech_motion_states"] and summaries[1]["speech_motion_states"]
assert summaries[0]["speech_motion_feedback"]["peak_head_rad"] < .025
assert summaries[1]["speech_motion_feedback"]["peak_head_rad"] > .04
(out / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
print("Passed A, B, TCP stop during cue, TCP stop during speech; all neutral recoveries confirmed.")
