# Validation: expressive-performance-v2

Validated on Windows, Python 3.12, Reachy Mini SDK 1.11.0 and MuJoCo. Physical execution remains disabled.

## Current evidence

- `assets/conversation/q1` through `q6`: six genuine Conversation App text-input backend captures, with unchanged Aiden WAVs, successful response IDs/status, transcripts and compact event metadata. Audio is stored once per answer; receipts identify the original event-file hash before duplicate PCM removal.
- `alignment.json` beside each WAV: local PocketSphinx word/phone alignment, bound to the audio and transcript. The receipts cover 235 words and 328 estimated vowel nuclei. Automatic alignment and acoustic prominence are not manually verified syllabification or linguistic stress.
- `evidence/emotion-prosody/compiled-checks.json`: all six current motion hashes and phrase/accent schedules; A and thinking frames remained identical through the speech refinement, including q1's downward tilt.
- `evidence/emotion-prosody/summary.json` and its three logs: actual q1 and q5 B playback, plus a stop at eight seconds into q1. Both complete trials passed technical validation; all three returned to neutral. Observed speech head displacement reached about 12.3 degrees for q1 and 6.7 degrees for q5. This establishes simulator movement, not perceived naturalness or acoustic-to-mechanical latency.

## Software and installation checks

The retained suite checks rigid bounded trajectories, source/audio/alignment hashes, phrase matching, real alignment under a half-second audio shift, emotional source variation, speed/acceleration bounds, stop/failure recovery, transcript-before-generation ordering, metadata-only event logging, and study analysis/missingness. Removed tests covered only retired TTS and event-import code.

The directly downloaded upstream package was built and its 92 packaged source/resource files matched the installed vendored build byte for byte. The environment uses one Windows/Python 3.12 lock, `requirements-lock.txt`; the full upstream checkout is not needed in this repository.

Cleanup verification: all 31 retained tests passed in both the working environment and a fresh setup. The fresh installation passed dependency checks and imported the real upstream handler. All six expressive performance hashes remained identical to the simulator-tested artifacts; active WAVs, alignments, source motions and study configuration were unchanged.

## Remaining acceptance

All six scores remain `reviewed: false` pending watch/listen review; participant sessions reject unreviewed scores. Resolve the questionnaire anchors in `study/SURVEY.md` before collection. Live capture is implemented, but successful end-to-end microphone input and a new hosted turn with local alignment have not been validated; earlier hosted attempts encountered rate limiting. No backend requests were made during cleanup.

Still outstanding: microphone/speaker calibration, manual timing and perceived-emotion review, participant rehearsal and collection, and physical robot adaptation/testing. Superseded development runs and retired stimulus versions are excluded from the commit-ready tree.
