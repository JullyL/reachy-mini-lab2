"""Actual MuJoCo feedback tests; never participant data or physical validation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", required=True)
parser.add_argument("--silent", action="store_true", help="Motion-only check; cannot establish audio timing")
parser.add_argument("--audio-device", type=int)
parser.add_argument("--commissioning", action="store_true", help="Also rehearse half-amplitude A/B in simulation")
args = parser.parse_args()
out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=False)
summary=[]
cases = [("A",None,False),("B",None,False),("B",.3,False),("B",2.5,False),("B",5.4,False)]
if args.commissioning:
    cases += [("A",None,True),("B",None,True)]
for condition, stop, commissioning in cases:
    before=set(out.glob("*.jsonl"))
    cmd=[sys.executable,"-m","reachy_lab2","trial","--condition",condition,"--backend","sim","--auto-accept","--log-dir",str(out)]
    if args.silent: cmd.append("--silent")
    if args.audio_device is not None: cmd += ["--audio-device",str(args.audio_device)]
    if stop is not None: cmd += ["--stop-after",str(stop)]
    if commissioning: cmd.append("--commissioning")
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=35)
    print(result.stdout,flush=True)
    label = f"{condition}-{'commissioning' if commissioning else 'full'}-{'complete' if stop is None else stop}"
    (out/f"{label}.txt").write_text(result.stdout+result.stderr)
    (out/f"{label}-command.json").write_text(json.dumps({"argv":cmd,"cwd":str(ROOT),"exit_code":result.returncode},indent=2)+"\n")
    files=set(out.glob("*.jsonl"))-before
    if len(files)!=1: raise RuntimeError(result.stdout+result.stderr)
    path=files.pop()
    end=json.loads(path.read_text().splitlines()[-1])
    expected="completed" if stop is None else "interrupted"
    ok=end["completion_status"]==expected and end["neutral_recovery_succeeded"]
    if stop is None: ok=ok and end["software_checks_passed"]
    summary.append({"file":path.name,"condition":condition,"commissioning":commissioning,"stop_after_s":stop,"passed":ok,"end":end})
(out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
if not all(r["passed"] for r in summary): raise SystemExit("One or more checks failed; inspect logs")
print("Passed both conditions and three interruption/recovery checks. Physical tests remain pending.")
