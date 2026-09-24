# Data dictionary

Templates contain headers only. Blank or `NA` means unobserved; a real zero is valid only for counts. No missing values are imputed.

| Field | Definition / units / permissible values |
| --- | --- |
| participant_id | De-identified P01-P04, extended in protocol before recruiting more participants; TECH is software validation only |
| condition | A or B |
| order | Preassigned AB or BA; must match protocol |
| session_id | App-printed UUID for one six-question condition block |
| study_version | Must be expressive-performance-v2; archived timing-study rows cannot be pooled |
| survey_version | Identifier for the documented course-approved wording/anchors; required |
| observer_coverage | complete / missing; missing coverage leaves the behavioral count unscored while retaining eligible subjective ratings |
| include | 1 include this block, 0 exclude; explicit adjudication of repeats |
| exclusion_reason | Required when include=0; retain original data |
| soc_1..4 | Four sociability item responses, integer 1-7 |
| ani_1..4 | Four animacy item responses, integer 1-7 |
| age_1..4 | Four agency item responses, integer 1-7; these columns are not participant age |
| dis_1..4 | Four disturbance item responses, integer 1-7; higher means more disturbance |
| expression_check | Separate study-specific item, integer 1-7 |
| qualitative_response | De-identified verbatim or explicitly labeled faithful paraphrase |
| protocol_deviation | Room, operator, timing, observation-coverage or other deviation |
| adult_confirmed | yes/no; only adults are eligible under this assignment |
| age_band | Participant-provided age category; avoid unnecessary precision |
| gender_optional / field_optional | Optional self-description; blank allowed |
| robot_familiarity | Brief standardized category such as none / occasional / frequent, fixed before collection |
| language_comfort | Self-reported comfort with study language, relevant to question reading |

Trial JSONL fields include trial/session IDs; participant/order/position; question and answer IDs; answer/gesture SHA-256; input mode; backend; condition; delay in seconds; monotonic seconds; mapped UTC timestamps; elapsed seconds since acceptance; status/errors; observer events; cue dispatch and feedback onset; predicted audio DAC onset; neutral feedback errors; and completion/timing checks. Monotonic seconds are meaningful within their process/run; use UTC for human records and IDs for joins.

`answer_preparation` records the active text/audio provenance. V2 uses actual Conversation App captures: `audio_metadata` points to `assets/conversation/qN/capture.json`, with backend response ID/status, voice Aiden, 16 kHz sample rate, input mode, answer text, duration and WAV SHA-256. `events.jsonl` preserves selected response events. These six captures came from text input, not microphones; the remote model version was not recorded and must not be invented. `answer_text_sha256` binds the exact transcript and the choreography score also binds the audio hash.

Archived/optional ElevenLabs sidecars additionally contain synthesis request settings, seed and generation UTC time. Those provider-specific fields do not describe the active HF captures. API keys are never stored. Saved WAV hashes, not provider seeds, establish identical A/B playback. Preserve each stimulus version and its source receipts.

`technically_valid` is an engineering flag, not participant consent, physical validation or automatic approval to include a block. Observer timing and acoustic latency remain measurement limits. `actual_cue_observed_s` is threshold-crossing feedback time, not exact visual onset. `SPEECH_START` is predicted device presentation time, not an acoustic microphone measurement. `repeat_prompt_count` is recalculated from observer timestamps in the acceptance-to-speech interval. Unobserved observer coverage must be handled as missing during review.

Analysis outputs: each separate dimension mean requires four observed items; dimension_n_items records observed item count. `condition_summary.csv` gives n, mean, sample SD and median per measure. `paired_differences.csv` retains A, B and B-minus-A, blank for incomplete pairs. `qualitative_coding.csv` retains source text and empty category/note fields. `audit.json` identifies input hashes. Do not use excluded or technical trials as participants.

V2 trial metadata adds `study_version`, `expressive_motion` (0/1), common `cue_start_s`, `choreography_reviewed`, `choreography_timing_basis`, and `motion_source_hashes`. `EXPRESSION_STATE` records the intended state, source motion, exact phrase and scheduled interval. `speech_motion_feedback` reports sample count and peak measured head/antenna displacement during speech; it is engineering evidence, not human response data. A/B motion hashes intentionally differ; answer hashes must match. The expression-check item replaces the old timing-check item and must not be pooled with it.

Speech-rhythm refinement: `speech_motion` records smoothing, blending and accent settings; `speech_alignment_sha256` identifies the exact local word/phone timing receipt. Speech `EXPRESSION_STATE` intervals come from aligned phrase anchors and include `accents` (seconds relative to audio start, word, and acoustic-prominence or phrase-ending reason). Vowel centers estimate syllable timing; acoustic prominence does not establish linguistic stress. Automatic alignments remain unreviewed until a listening pass.
