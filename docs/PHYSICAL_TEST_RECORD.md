# Blank physical test record

**Prepared, not executed.** Copy this form per attempt. Keep failed/interrupted attempts. Blank means unobserved, not passed. No participant data belongs in this commissioning record.

| Setup field | Actual observation / evidence |
|---|---|
| Date/time/timezone; operator; designated stop operator | |
| Assigned robot ID; wireless MAC registration confirmed | |
| Course access guide/version; approved Telepresence version and antenna control | |
| Mac OS; Python/SDK; robot firmware/daemon version | |
| Approved laptop/robot network; verified host/IP (no credentials) | |
| Battery %; motor states and temperatures; system errors/status | |
| Stable surface; ≥30 cm clearance; cable clearance | |
| Course stop control identified and accessible | |
| Speaker/device; OS volume; fixed location; ambient conditions | |
| Calibration right/left neutral and sign mapping; uncertainty | |
| Code/config/calibration/audio fingerprints | |

| Telepresence check | Actual observation / evidence |
|---|---|
| Correct assigned robot connected | |
| One small manual head movement | |
| One small manual antenna movement; actual control used | |
| Return to neutral; distinguish recenter from sleep pose | |
| End session; tab closed; app lock free | |
| Stop/recovery errors and resolution | |

| One custom-app attempt | Actual value / evidence |
|---|---|
| UUID/log path; exact launch command | |
| Condition A/B; amplitude in degrees; commissioning or full check | |
| Start pose and initial-neutral confirmation | |
| PRE_HOLD_START / MOVEMENT_START / SPEECH_START times | |
| MOVEMENT_END / POST_HOLD_START / CYCLE_END times | |
| RETURN_TO_NEUTRAL / NEUTRAL_RESULT / TRIAL_END times | |
| Right/left extrema and full ranges; measurement method | |
| Head/base displacement; feedback quality | |
| Clearance; smoothness; timing; motor noise | |
| Listening observations; acoustic/video method and uncertainty | |
| Completion / interrupted / failed; error and operator-event details | |
| Stop method and time; recovery observed; safe-to-resume decision | |
| Final pose; reviewer and decision | |
| Uncut physical video path/link and matching time range | |
| Physical stage-marker excerpt path and source log lines | |

## Actual parameter adjustment after a safe first run

- First reduced run UUID and observations: **[ ]**
- Decision that permits the adjustment; observer/operator: **[ ]**
- Named parameter and units: `antenna_amplitude_deg`, degrees per antenna from calibrated neutral.
- Actual old → new value; condition: **[ ]**
- Reason grounded in actual clearance/smoothness/timing/recovery: **[ ]**
- Configuration diff/hash, or commissioning 0.5 → reviewed full 1.0 scale: **[ ]**
- Adjustment time and operator: **[ ]**
- Final recorded run UUID, actual value and outcome: **[ ]**
- Final physical video: **[ ]**
- Matching physical stage-marker evidence: **[ ]**
- Remaining issues and whether amplitudes may be frozen: **[ ]**

Do not prefill “safe,” two observed differences, or 10°/30° approval. If a smaller final setting is needed, preserve the original logs and repeat the corresponding simulation/physical verification before changing the study freeze.
