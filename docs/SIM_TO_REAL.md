# Sim-to-real comparison template

**Simulation completed 2026-09-30; physical observations intentionally blank.** New recorded runs, not historical Section 3 values.

| Measure | New simulation A / B | Physical observation, method and uncertainty |
|---|---|---|
| Trial IDs | 1da29572-85b1-47c5-9b4d-de0da2f193a1 / 5fee46d0-c0e6-4770-b78f-455b6f8bb5a0 | |
| Command amplitudes | 10° / 30°; provisional | |
| Max displacement right / left | A: 10.164° / 10.164°; B: 29.809° / 29.809° | |
| Full range right / left | A: 19.766° / 19.767°; B: 59.600° / 59.600° | |
| Feedback polling | 48.49 / 48.30 Hz; cached sensor states possible | |
| Maximum unlagged tracking discrepancy | 1.976° / 4.777°; diagnostic | |
| Predicted DAC minus movement dispatch | -0.071 / -0.978 ms; not acoustic measurement | |
| Head/base | Stationary within 2°/2 mm provisional tolerances in both | |
| Initial and final pose | Initial neutral and recovery confirmed by SDK feedback in both | |
| Stops | 0.3/2.5/5.4 s interrupted; all recovered | |
| Reduced rehearsal | 5°/15° complete, recovered; simulation only | |
| Audio and motor noise | Mac playback dispatched; no listening, SPL or acoustic-onset assessment | |
| Telepresence | Real app camera and head control ran; no antenna control exposed; close tab required to release lock | |

## At least two actual differences (complete after physical execution)

| Difference | Specific simulation evidence | Actual physical observation | Likely explanation / uncertainty | Consequence or adjustment |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

Final parameter adjustment and physical run UUID: **[ ]**

Physical final video: **[ ]**; physical stage markers: **[ ]**.

Do not turn predicted differences into observations. Use `PHYSICAL_TEST_RECORD.md` for the actual old/new parameter values and the safe-to-adjust decision.
