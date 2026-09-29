# Validation status — antenna-greeting-v1

Verified on 2026-09-29 on macOS arm64, Python 3.12.14, Reachy Mini SDK 1.11.0, MuJoCo 3.3.0 and the locked dependencies. No physical robot or participant was used.

## Completed

- `python -m pytest -q`: **16 passed** (28.88 s); output in `evidence/antenna-greeting/pytest.txt`. Tests cover the one-factor trajectory and derivative scaling, right/left mapping, neutral holds, half-amplitude commissioning, frozen speech, upstream PCM equivalence, Emotions transitions, device-clock scheduling, AB/BA order/repeat limits, separate/missing HRIES and emotion scores, paired analysis with failed-attempt retention, all three stop phases, socket exclusivity/TCP stop, stuck feedback and connection/recovery faults. Synthetic analysis fixtures exist only in temporary test directories, not the raw study templates.
- `python scripts/verify_sources.py`: three retained upstream hashes match the provenance manifest. The Emotions files were also byte-compared against fresh pinned downloads; Conversation source was fetched from its exact pinned GitHub revision.
- Compilation and CLI checks passed. A participant-session launch with the shipped review files fails **before connecting** with “Physical review/calibration pending.” Empty response templates reject analysis rather than generating results.
- Full MuJoCo + computer-speaker validation: `evidence/antenna-greeting/simulation-audio/summary.json` and its five JSONL logs. A/B completed; three deliberate B interruptions (0.3, 2.5 and 5.4 s) were recorded as interrupted with successful neutral recovery. A/B had zero skipped frames and stationary head/base within the configured tolerances. `technically_valid=true` for the two complete simulator trials does not make them physical or participant evidence; `study_eligible=false` throughout.

| MuJoCo result | A | B |
| --- | --- | --- |
| Command amplitude | 10° | 30° |
| Measured max absolute right / left displacement | 9.869° / 9.869° | 29.766° / 29.766° |
| Measured right / left full range | 19.712° / 19.712° | 59.524° / 59.524° |
| Achieved SDK feedback polling | 47.70 Hz | 47.96 Hz |
| Predicted DAC onset minus first motion command | −1.35 ms | −1.62 ms |
| Feedback crosses 0.5° after cycle start | 1.334 s | 1.252 s |
| Maximum unlagged command/feedback discrepancy | 2.113° | 5.299° |
| Neutral recovery | Confirmed in simulated feedback | Confirmed in simulated feedback |

The requested movement starts at t=1 s; the 0.5° threshold occurs later because minimum-jerk motion starts slowly and feedback includes transport/plant lag. A threshold crossing is not true motion onset. Predicted DAC timing is not microphone-measured acoustic timing. The speaker stream ran, but no human listening review, sound-pressure measurement or robot-side acoustic synchronization is claimed. The frozen WAV is 1.7493125 s, PCM16 mono at 16 kHz.

## Development findings retained

The first socket regression run had 13 passes and two failures caused by TCP TIME_WAIT after a stop request. POSIX SO_REUSEADDR fixed restart while a live listener still prevents concurrent controllers; the final suite passed. This historical test output was replaced by the final suite receipt; the failure is documented here.

`simulation-motion-verified/` contains the earlier motion-only run, including its failed B result. Its initial validation incorrectly used a 3° **instantaneous** command-to-feedback error as an excursion criterion, despite asynchronous feedback/plant lag. It measured B peaks near 29.76° but failed with ~5.30° raw discrepancy. The final validator checks both signed measured extrema within a fixed ±3° excursion tolerance, retains raw error and observed peak/onset times as diagnostics, and still checks endpoint/neutral, poll quality and command timing. No amplitude, duration or interpolation was changed to obtain a passing run. This revision is software validation policy, not evidence that physical tracking lag is acceptable. Physical review must inspect actual traces and audiovisual timing before approval.

The first simulator launch was blocked by the local socket sandbox; a later SDK launch needed explicit GStreamer bootstrap. `scripts/simulate.py` and `SDKRobot.connect` now use the installed GStreamer setup function. No SDK source was patched.

## Pending before participant collection

1. Physical neutral calibration, right/left/sign checks and robot identity; half-amplitude 5°/15° commissioning, then documented adjustment and full provisional 10°/30° verification.
2. Physical angle/timing traces and achieved feedback quality; stationary head/base, motor noise, clearance and repeatable neutral recovery, including stops in all phases. Reassess engineering tolerances using those observations.
3. Listening review of the exact greeting; fixed speaker/device/OS volume and location; acoustic/video synchronization and measurement uncertainty. The computer speaker arrangement must remain identical in A/B.
4. Complete `config/physical_review.json` with actual evidence and current hashes; verify calibration and freeze final settings. The shipped review is unapproved and `provisional=true`.
5. Resolve the report section 5.3 task-duration placeholder with the instructor: one six-second greeting plus instructions/measures versus the assignment's 3–5-minute task wording. No extra repetitions were silently added.
6. Robot-only demonstration videos: `[A full cycle link]`, `[B full cycle link]`, `[physical stage-marker excerpt]`, `[setup photograph]`, `[sim-to-real comparison and documented adjustment]`. No demonstration links or participant data have been invented.

## Report preservation

The updated DOCX changes only section 3, including 3.1–3.3. `docx-preservation.json` verifies every body subtree outside section 3 is canonically identical, and every other ZIP member is byte-identical to the supplied report. Pagination can shift because section 3 is longer; content/formatting in sections 1, 2, 4 and 5 is preserved. No necessary conceptual change to sections 4 or 5 was found. Physical results and the existing task-duration question may require later updates; the outstanding requirements are listed above and in `README.md`.

## Final cleanup regression

After removing legacy study files, unused in-memory log storage and stale comments, all 16 tests passed (26.78 s). Both full A/B cycles and three interruption/neutral-recovery checks passed again in MuJoCo with audio. `evidence/antenna-greeting/cleanup-verification.json` records the final code fingerprints and simulation outcomes; `cleanup-pytest.txt` records the test result. Upstream source hashes and installed dependency consistency also passed. The report is unchanged by cleanup; its numerical results refer to the earlier retained traces. Physical verification remains pending.
