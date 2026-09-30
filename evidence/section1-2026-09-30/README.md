# Section 1 evidence — 30 September 2026

**Simulation only. No physical robot was controlled and no participant data was collected.** Open [index.html](index.html) to watch the recordings and follow the matching logs. The revised report is [Section 1 Prepared.docx](../../output/documents/HRI%20Report%20Lab%202%20Section%201%20Prepared.docx).

## Requirement and deliverable status

| Requirement / deliverable | Status | Evidence or remaining requirement |
|---|---|---|
| Read official Section 1 and current report | Completed | Assignment pp. 1–2, original Section 1 placeholders; assignment hash in `reproducibility.json` |
| Inspect Mac, instructions and existing app | Completed | `reproducibility.json`; no applicable local AGENTS.md found; working arm64 environment retained |
| Separate course access guide | Blocked | Not found in local search; Canvas access required fresh authentication; course-specific VM/version/stop details remain unverified |
| 1.1 RedRover registration and shared network | Prepared for physical execution | [Mac guide](../../docs/SECTION1_MAC.md); robot identity/MAC and approved network needed |
| 1.2 battery, motor/temperature and system checks | Prepared for physical execution | [Blank record](../../docs/PHYSICAL_TEST_RECORD.md); cannot observe physical values here |
| Telepresence Mac install/build | Completed | `telepresence-install.txt`, `telepresence-build.txt`; official revision f33ba997, JS SDK 1.10.0-rc.5 |
| Telepresence in real MuJoCo simulation | Completed with limitations | `telepresence/summary.json`; live camera, head joystick and recenter; no microphone/audio test |
| Requested Telepresence simulation recordings | Completed | [Live robot environment](media/SIMULATION-Telepresence-robot.mp4), [actual UI](media/SIMULATION-Telepresence-UI.mp4), events, feedback and captures |
| 1.3 small manual antenna movement in Telepresence | Blocked | Current official app has no independent antenna control. Course-approved version/control or clarification required; no substitution made |
| 1.3 physical head movement and manual-control termination | Prepared for physical execution | Mac checklist; simulation found End session returned live, closing tab released lock; preserve this caution |
| Full greeting simulation A/B and pose/timing checks | Completed | `recorded-simulation/summary.json`, `media/results.json`, raw JSONL and plots; both passed |
| Interruptions in all three phases | Completed | B at 0.3/2.5/5.4 s interrupted and recovered; matching videos and raw logs |
| 5°/15° reduced-amplitude rehearsal | Completed in simulation | Recorded commissioning A/B passed; never participant conditions |
| New reproducibility record / fingerprints | Completed | `reproducibility.json`, `manifest-sha256.json`, exact per-run argv JSON and source records |
| Raw logs, traceable stage markers and readable summary | Completed | `recorded-simulation/*.jsonl`, [markers](media/stage-markers.md), [results](media/RESULTS.md) |
| A/B, stop and neutral-recovery recordings | Completed | Seven recorded-trial MP4s plus standalone recovery video; all are simulation and have no audio track |
| 1.4 first physical cycle at ≤half amplitudes | Prepared for physical execution | Mac guide commands: commissioning A=5°, B=15°, run individually with inspection |
| 1.4 actual adjustment and final physical video | Prepared for physical execution | [Blank physical record](../../docs/PHYSICAL_TEST_RECORD.md); final 10°/30° not approved |
| Physical stage markers and ≥2 observed sim-to-real differences | Prepared for physical execution | [Comparison template](../../docs/SIM_TO_REAL.md), simulation column filled, physical column blank |
| Only Section 1 changed in DOCX | Completed | `docx-preservation.json`, `document-qa.json`; all outside body subtrees and other ZIP members preserved |

Exact execution records and repeat commands are indexed in [COMMANDS.md](COMMANDS.md). The file manifest covers this package and the final report.

## New results and historical evidence

`simulation/` is the first new seven-run validation batch. `recorded-simulation/` is the subsequent seven-run batch with live frame capture and is the source of **Section 1's numerical table**. Both passed A/B, three intended interruptions and commissioning A/B. `recorded-A/` and `capture-A/` retain successful A trials performed during initial recording attempts; neither is the final complete-cycle video source. `media/A-frames/` was an incomplete early low-rate screen capture; it is not presented as a complete-cycle movie.

`evidence/antenna-greeting/` remains unchanged and is **historical 29 September evidence** cited by the unchanged Section 3. Small numerical differences between the old and new simulator trials are expected; do not replace historical numbers with new measurements without identifying the run.

The two recorded full cycles had maximum absolute right/left excursions **A 10.164°/10.164°**, **B 29.809°/29.809°**; full ranges approximately **19.77°/19.77°** and **59.60°/59.60°**. Polling was **48.49/48.30 Hz**. Both had zero skipped command frames, stationary head/base within configured tolerances, confirmed initial neutral, acceptable scheduled endpoint and confirmed recovery. Reduced rehearsals measured approximately **4.937°** and **14.862°** maximum excursion per antenna. Exact values, pose errors, timing and UUIDs are in `media/results.json` and the raw logs.

SDK values are **simulated feedback**. Polling can repeat cached states. Dispatch timing, first 0.5° threshold crossing, predicted DAC onset and acoustic onset are different measurements. There was real Mac speaker playback, but no listening assessment, SPL measurement or recorded microphone timing. The movies contain no audio track.

## What the recordings show

- Seven greeting MP4s encode actual frames from the **running** MuJoCo model/data. The observer targeted 15 fps; achieved capture rates were about 14.2–14.3 fps. Timestamps preserve actual capture intervals. There was no log replay, trajectory reconstruction, generated animation or added speech track.
- `SIMULATION-Telepresence-robot.mp4` is the external simulator view during operation of the **official hosted Telepresence** app. Small observed yaw displacement was about 1.28°. Joystick, recenter and end-session timestamps are in `media/Telepresence-events.json`; `telepresence/feedback.jsonl` records simulated pose independently of any greeting trial.
- `SIMULATION-Telepresence-UI.mp4` contains actual browser captures. Sampling occurred in bursts, with real-time holds during gaps; use the continuously captured robot video and telemetry for movement review. The UI capture ends while the app is showing its sleep transition; the later return to live and release after tab closure are documented separately.
- The automatic antenna sleep motion at the end of Telepresence is **not** a manual antenna-control test. The app's recenter button controls head/body; it does not establish calibrated antenna neutral.
- `SIMULATION-standalone-neutral-recovery.mp4` shows subsequent recovery from the Telepresence sleep pose through the existing SDK adapter, with no greeting. The receipt is `telepresence/standalone-neutral-recovery.json`.
- `media/video-validation.json` records decode checks; first/middle/final decoded frames were visually inspected for all movies. Selected real screenshots and target-versus-feedback plots are provided.

## Failed checks and limitations retained

1. `pytest-controller-busy.txt`: 8 passed / 8 failed when pytest overlapped an active trial and port 18731 correctly refused a second controller. Serial rerun `pytest.txt`: **16 passed in 26.79 s**. Do not parallelize these tests with trials.
2. Native `screencapture` exited 1 and produced no movie. No screen-permission changes were made. An initial approval review also misidentified the intended window; a subsequent explicit owner check established it was MuJoCo. Live MuJoCo rendering supplied the complete recordings instead.
3. The first low-rate CUA A capture began late. Its original successful trial log is retained, but only the later full live capture is described as a complete A-cycle recording.
4. `media-encoding.txt`: the first summary formatter failed on the intentionally early stop, which has insufficient movement samples. Video encoding had succeeded. The formatter now reports those fields as unavailable and the final pass completed (`media-encoding-final.txt`); no data was imputed.
5. The first `hf auth login` could not reach the network inside the sandbox; the browser-based retry succeeded with the user's authorization. No credential is included in this evidence package.
6. Telepresence's README port/Node guidance lags its source: Vite is configured for **5183**, and the build was tested with Node 24.19.0. The real recorded app used hosted OAuth. The Mac simulator was authenticated separately, named uniquely, and verified as simulation before motion.
7. Telepresence has no independent antenna control at the inspected revision. End session returned to live/remote lock; closing the tab released it. Full physical 1.3 compliance remains open. No physical safety conclusion follows from simulation.
8. Missing Reachy USB audio-device warnings are expected on this Mac-only video test; no robot USB audio or microphone stream was substituted. The initial viewer also logged a GStreamer plugin-loader warning but ran successfully. SDK files were not patched.

## Preserved study safeguards

No changes were made to `reachy_lab2/`, `config/`, `assets/`, `study/`, `tests/` or the retained upstream integrations. The frozen speech, six-second trajectory, A/B design, logging, participant order/repeat checks and unapproved physical-review gate remain intact. Only simulator/evidence tooling and documentation were added or extended. No commit or push was performed.

Use [the execution guide](../../docs/SECTION1_MAC.md) at the robot. Physical video, system values, actual adjustment, listening/acoustic observations and two observed sim-to-real differences still require the real robot. Alienware was not used or technically required by the tested workflows.
