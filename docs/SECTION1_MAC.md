# Section 1 execution from the Mac

Verified 2026-09-30. All new execution was simulation on this Mac. **No physical robot was connected or moved.** The current assignment was read from `~/Downloads/Lab 2 - Research Methods.pdf`, pp. 1–2. Sections 1.1–1.3 concern **Telepresence**; Section 1.4 deploys the **Section 3 greeting app** as the final simulated candidate. This interpretation follows “final simulated candidate,” because the greeting is the existing two-condition, simulation-tested application; implementation details remain in Section 3.

## Requirements and unresolved course details

No technical dependency on Alienware, Windows, or a VM was found. Both the existing greeting simulator and official Telepresence ran on macOS arm64. The assignment mentions VM setup through a separate **Lab 2 – Reachy Mini Access and Basic Testing Guide.pdf**. Searches of Downloads, Documents, Desktop, attachments and Spotlight did not locate it; Canvas navigation required reauthentication. Its required environment/version, assigned robot identity and credentials, registration responsibilities, course stop-control procedure, and any prescribed Telepresence version remain unverified. A working Mac route does not establish that an instructor has waived a course VM instruction.

The assignment's actual Telepresence hyperlink is `https://huggingface.co/spaces/tfrere/telepresence`; it resolves to Pollen Robotics' current app, revision `f33ba997b0c7aee479e8cb113315c912c6124f88`. That version exposes a head/body joystick and recenter button, **no independent antenna control**. Do not count automatic wake/sleep antenna motion, the custom greeting, or another controller as the required small Telepresence antenna movement. Obtain the course-approved version/control or instructor clarification before marking 1.3 complete. The separate guide may resolve this mismatch.

## A — Telepresence on the Mac

### Official installation and launch

The current app is a browser React/Vite/WebRTC application, not a Python app to install with pip. The supported hosted route requires no local Telepresence installation. Pollen's Reachy Mini Control desktop application supports Apple Silicon macOS. On the assigned wireless robot, use Control's app catalog to launch/favorite the assignment-linked Telepresence, or open the same hosted app from the Mac browser. Authenticate the robot daemon and browser with the same Hugging Face account. Verify the assigned robot's identity before connecting: connection can wake the robot.

**Mac terminal** (physical setup only, after system checks):

```sh
open 'http://reachy-mini.local:8000/'
open 'https://huggingface.co/spaces/tfrere/telepresence'
```

Select the assigned robot, then use a very small joystick deflection. Release the joystick to stop adding motion. Use **Recenter head and body to neutral**, observe the result, then **End session**, close the Telepresence tab, and confirm the daemon's app lock is free before another controller starts. Recenter is not an emergency stop. The current host may execute a sleep trajectory when ending a session; that pose is not the greeting's calibrated neutral.

**Observed stop issue:** in the verified simulation, End session displayed “Putting Reachy to sleep…” and later returned to the live UI; the lock remained `remote_session`. Closing the tab released it to `free`. This is a recorded limitation, not a successful normal-stop claim. Do not launch the greeting while the lock remains occupied.

The assignment's alternative onboard terminal launch is not verified for this current JavaScript/WebRTC revision. Use the Control/browser route above. Do not invent a Python launch command, install a second daemon, or move the web app onto the robot merely to follow an outdated recipe.

### Local developer installation (tested)

Keep Telepresence separate from the Python study environment. The README says Node 18+, but the locked Vite 7 toolchain requires a newer Node; Node **24.19.0** was used successfully. Commands run on the **Mac**, in a new checkout:

```sh
git clone https://huggingface.co/spaces/pollen-robotics/telepresence /tmp/section1-telepresence
cd /tmp/section1-telepresence
git checkout f33ba997b0c7aee479e8cb113315c912c6124f88
npm ci
npm run build
npm run dev -- --host 127.0.0.1
# Actual configured URL is http://127.0.0.1:5183 (README's 5173 is stale).
```

For local authentication, follow that checkout's `.env.example`: `VITE_HF_TOKEN` and `VITE_HF_USERNAME`, or a registered OAuth client ID. Keep credentials out of this repository, logs, videos and commits. Prefer the hosted OAuth route for the execution demonstration: that is the route actually recorded. Local installation, build and sign-in screen succeeded; local authenticated motion was not used as the final evidence. Ctrl+C stops the dev server after ending/closing the browser session.

### Actual Telepresence simulation and recording

**Supported with media enabled**, not with the greeting's default `--no-media` daemon. SDK 1.11.0 has a MuJoCo camera source and central WebRTC relay. Authenticate locally using the existing environment; the user completed browser authorization during this task:

```sh
cd /Users/pandora2/Documents/GitHub/reachy-mini-lab2
source .venv/bin/activate
hf auth login
mjpython scripts/simulate.py --viewer --media --video-only --log-level INFO \
  --record-dir /tmp/telepresence-live-NEW --record-seconds 180
```

`--video-only` explicitly suppresses the Mac microphone source. It is a simulator-only runtime adaptation, not an edit to the installed SDK or the official Telepresence app. No bidirectional-audio claim is made. `--sim` is unconditional; this launcher cannot start a physical daemon. Its advertised name is `lab2-simulation`.

In another Mac terminal, verify local identity and find the simulator's central peer in the INFO console (`central welcome received peer_id=…; registering … lab2-simulation`). Never select an unidentified or physical robot during rehearsal:

```sh
curl --fail http://127.0.0.1:8000/api/daemon/status
curl --fail http://127.0.0.1:8000/api/hf-auth/central-robot-status
```

Open the hosted Telepresence URL with `?robot_peer_id=SIMULATOR_PEER_ID`, sign in through its normal Hugging Face OAuth flow, and confirm **Lab2-simulation** in its header. The SDK badges this Mac daemon “Lite/USB”; this does not make it a physical Lite robot. The local status must say `simulation_enabled: true`, `mockup_sim_enabled: false`, and `camera_specs_name: mujoco`.

Operate the joystick gently, recenter, end the session, close its tab, and verify `GET /api/daemon/robot-app-lock-status` says `free`. Ctrl+C in the simulator terminal stops the **local simulator only**. Restart without `--media` for isolated greeting trials. The remote app lock correctly prevents simultaneous custom-app control.

**Evidence:** `evidence/section1-2026-09-30/media/SIMULATION-Telepresence-robot.mp4` is continuous capture of the live MuJoCo environment during actual official-app control. `SIMULATION-Telepresence-UI.mp4` captures the real browser UI and live simulated camera; sampling gaps retain their actual elapsed timing. Events, feedback and the lock-release receipts are alongside these recordings. No greeting app, reconstructed trajectory, or mock robot was substituted.

## B — Greeting simulation

The existing `.venv` is ready. Do not recreate it routinely. For a clean reconstruction only, follow the Python 3.12 / `uv` commands in the root README. The lock includes the existing plotting/Pillow and GStreamer dependencies; no additional package was introduced for capture.

**Mac, terminal 1:**

```sh
cd /Users/pandora2/Documents/GitHub/reachy-mini-lab2
source .venv/bin/activate
python scripts/verify_sources.py
python -m reachy_lab2 devices
# Device 2 was MacBook Pro Speakers; verify each session.
mjpython scripts/simulate.py --viewer
# Or, with no visible viewer: python scripts/simulate.py
```

**Mac, terminal 2** (activate the same environment):

```sh
python -m reachy_lab2 trial --condition A --backend sim --audio-device 2
python -m reachy_lab2 trial --condition B --backend sim --audio-device 2
# Press Enter for one six-second cycle; retain each UUID log.
python scripts/validate_simulation.py --audio-device 2 --commissioning \
  --out evidence/simulation-NEW
```

The validator runs A=10°, B=30°, B interrupted at 0.3/2.5/5.4 s, then simulation-only A=5° and B=15° rehearsals. It retains exact argv, return codes, terminal stage markers and raw JSONL. Direct half-amplitude rehearsals:

```sh
python -m reachy_lab2 trial --condition A --backend sim --commissioning --audio-device 2
python -m reachy_lab2 trial --condition B --backend sim --commissioning --audio-device 2
```

Do not run pytest concurrently with trials: they deliberately share controller port 18731. Run `python -m pytest -q` while no trial is active. All 16 tests passed in the serial rerun. The earlier 8 failures from running tests alongside a trial are retained, not erased.

### Recording complete greeting cycles

Start a fresh simulator with enough capture time, then run the validator in terminal 2 before capture expires:

```sh
# Mac terminal 1; new capture directory each time
mjpython scripts/simulate.py --viewer --record-dir /tmp/greeting-live-NEW --record-seconds 120
# Mac terminal 2
python scripts/validate_simulation.py --audio-device 2 --commissioning --out evidence/recorded-NEW
MPLCONFIGDIR=/tmp/reachy-plots python scripts/simulation_evidence.py \
  --runs evidence/recorded-NEW --frames /tmp/greeting-live-NEW --out evidence/recorded-NEW/media
```

The capture observer renders the **currently running MuJoCo model/data**, targeting 15 fps, at 640×480 from the same external camera as the viewer. It does not replay commands or re-simulate logs. The encoder preserves capture timestamps and refuses clips that do not cover the complete trial plus one second on either side. MP4s contain **no audio track**; playback still ran on the fixed Mac speaker in the trials. Preserve frame receipts, trial logs and file hashes. Screen recordings with actual sound, if needed later: use macOS Shift–Command–5, record the simulator region plus the stage-marker terminal; select an audio input only deliberately and record only the robot session. Stop with the menu-bar recording button.

### Normal stop, interruption and recovery

A completed cycle returns to neutral and logs `NEUTRAL_RESULT` and `TRIAL_END`. For interruption press Ctrl+C in the **trial terminal**, or from a second Mac terminal:

```sh
python -m reachy_lab2 stop
python -m reachy_lab2 mark interruption
# Records a deviation; invalidates completion:
python -m reachy_lab2 mark operator_error
```

`stop` requests scheduler interruption, audio abort and feedback-checked neutral recovery. A stopped trial is retained as interrupted, not completed. Remote stop during an Enter prompt is honored after the prompt returns; Ctrl+C exits the prompt immediately. Do not force-kill as a normal stop. A disconnected process cannot guarantee neutral. After resolving the fault, use the standalone recovery recipe below; it does not deliver another greeting. Ctrl+C in terminal 1 stops the simulator after trials finish.

## C — Mac controlling the physical wireless robot

### Physical execution checklist (not executed)

1. Obtain the separate course guide and assigned robot identity. Verify the required Telepresence antenna control/version with the instructor.
2. **Mac browser:** open [Cornell Wi-Fi](https://it.cornell.edu/wifi), select Register an IoT Device on RedRover / My Computers, authenticate with NetID/Duo, choose **Add Device with No Browser**, enter the **robot's wireless MAC address** and description, and register. This is not the Mac laptop's address. Cornell's registration portal requires campus access or VPN. Avoid duplicate registration of a course-managed robot; ask the responsible course operator for its record.
3. Put the laptop and wireless robot on the **same course-approved network**, as the assignment requires. Cornell generally directs laptops to eduroam and IoT devices to RedRover, so confirm the course's approved arrangement rather than assuming cross-SSID discovery works. VPN access to registration does not establish local robot reachability. Record actual SSID, robot IP, hostname and identity; do not publish credentials.
4. Power on the robot and wait for startup. **Mac:** open Reachy Mini Control or `http://reachy-mini.local:8000/`. If mDNS fails, use the verified IP shown in Control/course records, not a guessed address. `dns-sd -G v4v6 reachy-mini.local` can check resolution; Ctrl+C stops that lookup. An IP can work when multicast discovery is filtered; failure still requires course/IT assistance.
5. Record actual battery %, motor enabled/disabled state and temperatures, errors, firmware/daemon version, and system health. Follow course thresholds; none are invented here. Do not use simulation to fill these fields. Require daemon **1.11.0** for this locked greeting adapter; if different, stop and align versions through the course-approved process before movement.
6. Stable surface; at least **30 cm clearance** around the motion envelope; cables clear; designated stop operator and verified course stop control. No participants during commissioning. Close all other SDK writers.
7. **Mac, Telepresence:** select the verified assigned robot. Make one small head movement and one small **manual antenna** movement using the course-approved Telepresence controls. The currently checked public revision lacks the latter: leave this check open until resolved. Recenter and visually verify neutral, end session, close its tab, and verify lock release. End-session sleep is distinct from calibrated greeting neutral. Record any stop fault.
8. Measure neutral, right/left ordering and sign mapping. Update `config/calibration.json` with actual measured angles (degrees, SDK right then left) and robot identity. Do not mark calibration verified before measurement. The greeting preflight will attempt a smooth transition to the configured neutral; observe it with the stop operator present.
9. Run **one** reduced-amplitude cycle first (A=5° is the smallest prepared start). Inspect clearance, smoothness, timing and neutral recovery. Only after that result is judged safe, run the other reduced condition (B=15°) if appropriate. Stop on faults; do not automatically chain physical commands.
10. Document an actual parameter adjustment with old/new value, rationale, observations, operator and time. After approval by the present stop operator, execute a final recorded cycle. The prepared adjustment is from commissioning half-scale to full proposed scale, but **10°/30° remain provisional** until actual physical evidence supports them. Never record a future adjustment as accomplished.

**No commands need to run onboard the robot for the recommended route.** Its existing daemon remains running. All commands below run on the **Mac**; never run `scripts/simulate.py` or `reachy-mini-daemon` on the physical robot.

### Physical command reference

```sh
cd /Users/pandora2/Documents/GitHub/reachy-mini-lab2
source .venv/bin/activate
export REACHY_HOST=reachy-mini.local  # replace only with verified assigned robot IP if needed
python -m reachy_lab2 devices
curl --fail "http://${REACHY_HOST}:8000/api/daemon/status"
curl --fail "http://${REACHY_HOST}:8000/api/daemon/robot-app-lock-status"
# Check physical backend (simulation_enabled=false), running version 1.11.0, lock free.

# Run individually, with inspection between commands. Enter starts a cycle.
python -m reachy_lab2 trial --condition A --backend physical --host "$REACHY_HOST" --commissioning --audio-device 2 --log-dir logs/section1-physical
python -m reachy_lab2 trial --condition B --backend physical --host "$REACHY_HOST" --commissioning --audio-device 2 --log-dir logs/section1-physical

# ONLY after safe reduced runs and a documented decision to adjust to the proposed values:
python -m reachy_lab2 trial --condition A --backend physical --host "$REACHY_HOST" --physical-check --audio-device 2 --log-dir logs/section1-physical
python -m reachy_lab2 trial --condition B --backend physical --host "$REACHY_HOST" --physical-check --audio-device 2 --log-dir logs/section1-physical
python -m reachy_lab2 fingerprint
```

`--commissioning` multiplies the configured condition amplitudes by 0.5; with the unchanged configuration it yields **5°/15°**, never participant conditions. `--physical-check` uses the configured full **10°/30°**. If observations require smaller final amplitudes, revise `conditions.json`, document and retest the final simulation/physical pair, and reconcile report Sections 3–5 before collection. Do not change timings, audio or study design simply to pass commissioning. The physical-review gate remains unapproved and conditions remain provisional after this task.

Keep the same speaker device, fixed OS volume and location for A/B. Log motor noise, actual listening assessment and acoustic timing separately; no such assessment has been completed. Preserve every failed attempt and its original log.

### Recovery after a stopped or lost process

First use the normal app stop above. If it is unresponsive, movement is unsafe, or neutral fails, use the **course-approved robot hardware/Control stop** and inspect before any restart. Do not send repeated recovery commands into an uninspected fault.

After the robot is inspected, all manual clients are closed, the daemon lock is free, and the stop operator confirms it is safe to re-enable control, the existing SDK adapter can recover neutral without a greeting. This recipe was exercised **only in simulation**, after Telepresence's sleep pose:

```sh
# Mac; defaults below are simulation. For an inspected physical robot, REPLACE
# the next export with: export RECOVERY_BACKEND=physical RECOVERY_HOST="$REACHY_HOST"
export RECOVERY_BACKEND=sim RECOVERY_HOST=127.0.0.1
python - <<'PY'
import json, os, time
from pathlib import Path
import numpy as np
from reachy_lab2.robot import SDKRobot
from reachy_lab2.trial import Controller
backend = os.environ['RECOVERY_BACKEND']
assert backend in {'sim', 'physical'}
cal = json.loads(Path('config/calibration.json').read_text())
neutral = np.deg2rad(cal['neutral_deg_right_left']) if backend == 'physical' else np.zeros(2)
with Controller():
    robot = SDKRobot(backend, os.environ['RECOVERY_HOST'], neutral)
    try:
        status = robot.connect()  # checks backend/version/lock, then enables motors
        result = robot.neutral()
        receipt = {'utc_s': time.time(), 'backend': backend, 'daemon': status, 'neutral': result}
        Path('logs').mkdir(exist_ok=True)
        Path(f'logs/recovery-{time.time_ns()}.json').write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt, indent=2))
        if not result['succeeded']: raise SystemExit('Recovery failed; stop and inspect')
    finally:
        robot.close()
PY
```

This recovery command itself moves toward neutral; it is not an emergency stop. The standalone receipt is not a completed stimulus trial. Record the actual result and do not resume participant testing until reviewed.

## Recording shot list and templates

Use [PHYSICAL_TEST_RECORD.md](PHYSICAL_TEST_RECORD.md) for each attempt and [SIM_TO_REAL.md](SIM_TO_REAL.md) for comparison. Required physical shots: robot identity/setup with clearance; system-check evidence; Telepresence head and antenna movement; visible neutral and end of manual control; reduced first cycle; documented adjustment; **one uncut final robot-only cycle from initial neutral through final neutral recovery**. Record A and B robot-only cycles for Section 3 as well. Keep a second screen recording or terminal excerpt containing the same UUID/stage markers, with a shared clock/clap if measuring audiovisual timing. Avoid participant faces/voices in technical demonstrations.

The physical video, physical stage markers, at least **two actually observed sim-to-real differences**, and final adjustment remain blank. Simulation recordings supplement them; they do not satisfy the assignment's physical deliverables.

## Technical sources checked 2026-09-30

- [Official assignment-linked Telepresence](https://huggingface.co/spaces/tfrere/telepresence), redirects to [Pollen Telepresence source](https://huggingface.co/spaces/pollen-robotics/telepresence/tree/f33ba997b0c7aee479e8cb113315c912c6124f88). README, package lock, joystick and host source establish launch, authentication, controls and stop behavior; the installed source/configuration takes precedence over stale README port/version details.
- [Pollen getting started](https://pollen-robotics.com/reachy-mini/getting-started/): Apple Silicon Control support and wireless setup.
- [SDK simulation guide](https://github.com/pollen-robotics/reachy_mini/blob/main/docs/source/platforms/simulation/get_started.md); installed SDK 1.11.0 `daemon/backend/mujoco/backend.py`, `media/media_server.py`, `media/central_signaling_relay.py` inspected for actual media/capture behavior.
- [Cornell IoT registration](https://it.cornell.edu/wifi/register-device-doesnt-have-browser) and [Wi-Fi](https://it.cornell.edu/wifi): MAC-based registration, campus/VPN portal access and recommended device networks.

To encode an entire Telepresence live-environment capture after stopping the simulator:

```sh
MPLCONFIGDIR=/tmp/reachy-plots python scripts/simulation_evidence.py \
  --frames /tmp/telepresence-live-NEW --out evidence/telepresence-NEW --capture-only
```

This produces a genuine live-simulation recording, not an animation derived from the joystick targets. To capture the Telepresence UI too, use Shift–Command–5 on the browser region while the simulator recorder runs. Retain wall-clock events for joystick, recenter and End session; the delivered UI example uses actual browser frame captures with visible sampling gaps.
