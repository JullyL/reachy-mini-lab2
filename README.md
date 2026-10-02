# Reachy Mini antenna-amplitude greeting study

The final Part 8 report is [HRI Lab 2 Final Report](output/documents/HRI%20Lab%202%20Final%20Report.docx), rewritten from the newly supplied `HRI Report Lab 2 (1).docx`, rather than an earlier repository DOCX. The report covers Introduction, Method, Results, Discussion, References, and complete study appendices. [Analysis outputs and participant materials](study/final_submission/) reproduce its questionnaire results.

The pilot has **4 participants, 8 condition records, 4 complete A/B pairs, and no missing questionnaire ratings or excluded records**. Condition A is **10°** and Condition B is **30°** maximum displacement from neutral per antenna. Recorded completion is **4/4 in each condition**. Mean sociability is **A 3.6875, B 4.3125, paired B−A +0.625**; arousal is **A 3.75, B 4.50, +0.75**; valence is **A 4.75, B 5.25, +0.50**. Report figures use these same underlying values.

**Physical participant logs are missing from this submission.** The study team reports that they are retained on another person's computer. Calibration, physical review, achieved excursion/timing, and exact room/audio settings cannot be independently verified here. Pending review/configuration fields remain unchanged. Recorded completion must not be treated as telemetry-verified delivery. The questionnaire analysis is reproducible; full physical-session verification remains incomplete.

Earlier Section 1 work is retained as technical history: [Mac workflow](docs/SECTION1_MAC.md), [evidence/status](evidence/section1-2026-09-30/README.md), and [simulation recordings](evidence/section1-2026-09-30/index.html). Earlier repository DOCX revisions are not the final report.

One reproducible greeting, one manipulation: `antenna_amplitude_deg`, provisionally **A=10°**, **B=30°** maximum displacement per antenna from calibrated neutral. SDK antenna array order is **right, left**. Left follows neutral → +A → −A → neutral; right signs are reversed. Segment durations are 1, 2, 1 s with minimum-jerk interpolation. One second of neutral precedes and follows the movement, giving a six-second cycle. The same prerecorded “Hello, nice to meet you” WAV starts at t=1 s. Increasing amplitude at fixed timing also increases speed and acceleration.

The head target is identity and base yaw zero throughout the greeting. Wobbling, head tracking and automatic body yaw are disabled. There is no microphone, live LLM response, spontaneous emotion playback, or per-condition audio setting. Computer-speaker output is used; fix the device, speaker location and OS volume across A/B, and document these in the session sheet.

The previous processing/expressive-response implementation and its assets have been removed; the original implementation remains in Git history. Active commands are `trial`, `session`, `stop`, `mark`, `devices`, and `fingerprint`.

## Reproducible setup

Use Python 3.12 and `uv` from this repository's root. The checked-in lock captures the tested macOS arm64 Python 3.12 environment, SDK 1.11.0, NumPy 2.5.3, SoundDevice 0.5.3 and MuJoCo 3.3.0. Other platforms need their own verified lock; no Windows/Linux run is claimed.

```sh
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python requirements-lock.txt
uv pip install --python .venv/bin/python --no-deps -e .
source .venv/bin/activate
python scripts/verify_sources.py
python -m pytest -q
python -m reachy_lab2 devices
```

The frozen WAV, transcript, generation command and SHA-256 are in `assets/greeting/`; do not regenerate it between trials. `config/conditions.json` controls the study; changing it invalidates the physical-review hashes. The Emotions and Conversation component source revisions and verification are in [SOURCE_INTEGRATION.md](SOURCE_INTEGRATION.md). No Conversation App account or backend is needed for replay.

## Simulation and technical preview

Close other robot controllers. In an activated terminal, run:

```sh
python scripts/simulate.py
```

This starts only a local headless MuJoCo daemon, with media disabled and explicit GStreamer initialization. Do not launch it against the physical robot. In a second activated terminal:

```sh
python -m reachy_lab2 trial --condition A --backend sim --audio-device 2
python -m reachy_lab2 trial --condition B --backend sim --audio-device 2
```

Replace `2` with the output device from `devices` (2 was MacBook Pro Speakers in this verification). Enter starts the six-second cycle after preflight neutral checks. All preflight, log hashing and recovery happen outside the stimulus. `--auto-accept` is for technical automation; `--silent` suppresses audio and can never be study-valid.

```sh
python scripts/validate_simulation.py --audio-device 2 --out evidence/new-simulation-run
python -m reachy_lab2 trial --condition A --backend mock --silent --auto-accept
```

The validator runs A/B, then interrupts B during the pre-hold, movement and post-hold. Its output directory must be new. `mock` echoes commands and is not robot/simulator evidence. MuJoCo checks use simulated joint feedback; the physical robot must still be tested.

## Physical commissioning and freeze

The wireless robot already has a daemon: **do not start another daemon on it**. Use the course-approved network, check battery, temperatures and motor/system state in Reachy Mini Control, clear at least 30 cm, assign an operator to stop, end teleoperation and close every other SDK client. The local TCP lock excludes this app's other instances but cannot prevent an unrelated SDK writer or a controller on another computer.

Use a daemon matching SDK 1.11.0; a mismatch fails clearly. Verify neutral and right/left/sign mapping, then put calibrated joint angles (degrees, right then left) and robot identity in `config/calibration.json`. Do not mark it verified without measurements. Head neutral is the SDK identity pose; base neutral is 0 rad.

As required by the assignment, first test at half of the simulated amplitudes (A=5°, B=15°). These are commissioning runs, never participant conditions:

```sh
python -m reachy_lab2 trial --condition A --backend physical --host reachy-mini.local --commissioning --audio-device 2
python -m reachy_lab2 trial --condition B --backend physical --host reachy-mini.local --commissioning --audio-device 2
```

After checking clearance, smoothness and recovery, document the adjustment to the proposed full 10°/30° values and test both:

```sh
python -m reachy_lab2 trial --condition A --backend physical --host reachy-mini.local --physical-check --audio-device 2
python -m reachy_lab2 trial --condition B --backend physical --host reachy-mini.local --physical-check --audio-device 2
```

Inspect measured angle traces, both lobes and per-antenna ranges, stationary head/base, actual movement timing, motor noise, speaker output, and neutral recovery, including stop at each phase. Log all attempts. Use calibrated fixed-view video if SDK feedback cannot support physical angle verification, and document uncertainty; the current automatic session gate requires SDK feedback. Observe/listen to the exact WAV and measure acoustic timing with a robot-only recording. Predicted DAC time is not microphone-measured onset.

After satisfactory physical tests, keep final condition values consistent with report sections 4/5, mark `provisional=false` and the calibration verified, record the result/evidence, then run `python -m reachy_lab2 fingerprint`. Copy the resulting hashes into `config/physical_review.json`, complete its reviewer/robot/evidence fields and set `approved=true`. This is a manual evidence record, not an automatic physical-safety certification. Study sessions reject an incomplete or stale review. This repository deliberately ships that gate **unapproved**.

## Participant sessions

Use the preserved report's consent, facilitator script and room controls. `study/protocol.json` preassigns P01/P03=AB and P02/P04=BA. Add balanced enrollment slots before recruitment if needed. Use one shared log directory throughout collection so order/repeat checks see all prior attempts. Do not move/delete logs between conditions.

```sh
python -m reachy_lab2 session --participant P01 --condition A --operator OP1 --backend physical --host reachy-mini.local --audio-device 2
python -m reachy_lab2 session --participant P01 --condition B --operator OP1 --backend physical --host reachy-mini.local --audio-device 2
```

In each condition, have the response ready and ask the participant to say “Hello” to initiate the exchange. The facilitator then presses Enter to start Reachy Mini’s prepared “Hello, nice to meet you” response; the archived app does not automatically recognize speech. Each command performs one robot response only. After A, collect HRIES, valence, arousal, open response, then movement size. The B command prompts after the first questionnaire and enforces a 30-second neutral reset; reverse A/B for a BA assignment. Allow 3–5 minutes for instructions, the greeting exchange and questionnaire; actual session durations were not recorded.

The first completed attempt supplies ratings. If interrupted or failed, document the problem, resolve it and allow only one replacement with `--repeat-of ORIGINAL_TRIAL_UUID`; preserve both logs and record prior exposure. Stop after a second failure. Never repeat or exclude based on ratings. `study/SURVEY.md` preserves the HRIES label swaps 2/3 and 5/6, sociability as primary, and separate exploratory valence/arousal.

## Stop and faults

Press **Ctrl+C**, or from another activated terminal in this checkout:

```sh
python -m reachy_lab2 stop
python -m reachy_lab2 mark operator_error
python -m reachy_lab2 mark interruption
```

`stop` interrupts the scheduler, aborts audio and attempts smooth, feedback-checked neutral recovery. `interruption` also stops; `operator_error` records an intervention that invalidates completion. During an Enter prompt, Ctrl+C exits immediately; a remote stop is honored before any greeting begins once the prompt returns. An app stop is not a physical emergency stop. If motion is unsafe, the app is unresponsive, or recovery fails, use the robot's course-approved hardware/Control stop and do not resume until inspected. Ctrl+C in the simulator terminal stops the test daemon.

## Logs and acceptance rules

`logs/<UUID>.jsonl` is append-only during a trial; preserve the original files. Records include UTC/monotonic timestamps, participant/order/attempt/repeat, condition and amplitude, robot backend, exact code/configuration/audio/trajectory/calibration hashes, requested and actual output device, all dispatched antenna targets, measured joint angles, head/base deviations, operator errors, audio events, completion and neutral recovery. Markers are identical for simulator and physical adapters.

Actual neutral is averaged from five SDK samples. The measured movement summary keeps right and left maximum absolute displacement and full range separate. It targets 50 feedback polls/s and requires at least 20/s with no gap over 100 ms; SDK polls may repeat cached sensor states, so this is an achieved **polling rate**, not an independently measured sensor refresh rate. Both positive and negative peaks must fall within a provisional ±3° excursion tolerance, head/base within 2°/2 mm, and the scheduled endpoint within ±2° of measured neutral. Final recovery requires five consecutive polls inside neutral tolerances. These engineering tolerances require physical review.

Command and predicted-DAC onset target t=1 s (±50 ms), motion end t=5 s (±50 ms); skipped command frames invalidate a full trial. Raw instantaneous tracking error and observed movement onset (>0.5°) are logged as diagnostics; feedback transport/plant lag means they are not a zero-lag accuracy guarantee. Review actual traces and acoustic/video timing before physical approval. The final one-second neutral hold is completed even though the 1.749-second WAV ends earlier.

## Analysis and evidence

```sh
python -m pip install -r study/analysis-requirements.txt
python scripts/analyze_report_data.py --out analysis/reproduced-pilot
```

This descriptive path reads the retained raw questionnaire XLSX, cross-checks its numeric and text responses against `responses.csv`, merges the participant register, and reproduces all scores, paired summaries, recorded completion, qualitative coding, and both paired figures. Its audit records source hashes and the missing physical logs. Original spreadsheets remain unchanged: the older analysis-ready workbook contains stray `40` entries in date/failure/notes cells and is retained only for provenance. The regenerated CSV uses raw responses and register dates/deviations instead.

The original `python -m reachy_lab2.analysis` module is a separate, stricter path for its richer response schema and matching eligible physical trial logs. The present raw files lack those trial identifiers, so that command does not reproduce this submission as-is. No synthetic logs are substituted. [VALIDATION.md](VALIDATION.md) preserves earlier software/simulation checks and their historical pending status; they are not participant evidence.

## Repository contents

`reachy_lab2/`, `config/`, and `assets/greeting/` contain the active app. `scripts/` and `tests/` support reproducibility; `study/` contains the protocol, survey, data dictionary, collected raw data, and final descriptive analysis/materials. `third_party/` retains the exact reused source and license evidence. `evidence/antenna-greeting/` retains the technical validation runs, including the documented earlier failure.

The earlier Section 1 Prepared, Section 3 Revised, and Section 5 Draft DOCX files are historical revisions, not the submission copy. The local `.venv/` remains installed for running the app and is excluded from Git.
