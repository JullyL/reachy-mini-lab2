# Reachy Mini: brief cue versus emotional performance

The redesigned Part 3 demo integrates the **actual Reachy Mini Conversation App realtime handler** with an **Emotions-based emotional performance system**. The study compares human responses to a brief preparation gesture (A) and sustained expressive thinking plus speech choreography (B).

The current target is **MuJoCo, SDK 1.11.0, Windows Python 3.12**, with sound through the computer speakers. Physical execution is disabled.

## Run the expressive demo

The installed working copy is `C:\Users\alexx\reachy-lab2-custom`. Keep the existing simulator running and close other robot controllers. If needed, start the simulator in a separate PowerShell terminal:

```powershell
cd "$env:USERPROFILE\reachy-lab2"
.\.venv312\Scripts\reachy-mini-daemon.exe --sim
```

In a second terminal:

```powershell
cd "$env:USERPROFILE\reachy-lab2-custom"
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 trial --condition B --question q1
```

Read the displayed question and press Enter at its end. B begins curious thinking at a scheduled 0.5 s, starts the answer at 5 s, and performs phrase-specific curious, explanatory and happy movements during the answer. It returns to neutral. Try q2-q6 for different performances.

Compare with the brief-cue baseline:

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 trial --condition A --question q1
```

A has the same 0.5 s cue start and 5 s answer start, but only the original one-second gesture and no speech movement. A/B play the identical frozen WAV for each question. The named factor is `expressive_motion`: A=0, B=1, a binary complete-performance factor. It is not an isolated test of amplitude or of one emotion.

Preview a single emotional state before watching the full choreography:

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 emotion --state happy --duration 3
```

Other states: `attentive`, `curious`, `thinking`, `explaining`, `affirming`, `enthusiastic`, `surprised`.

## Actual live conversation

This mode imports and runs the pinned upstream `HuggingFaceRealtimeHandler`: backend connection, audio input, transcription, response lifecycle, audio decoding and transcript output. It has no fallback to `questions.json`. Generation is buffered until a complete response arrives, then speech and a sentence-level emotional draft play together. This is live turn-taking, not low-latency streaming playback or a controlled study trial.

Text input tests the real backend without recording a microphone:

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 live --text "Why does the Moon appear to change shape?"
```

For microphone input, first find your input device:

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 devices
# Replace 16 with the actual microphone index. Wait for 'Speak now'.
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 live --input-device 16 --seconds 6
```

This explicitly records six seconds and sends the audio to the configured Hugging Face backend. No microphone is opened in `trial` or `session`. The raw microphone recording is not saved; recognized question, generated answer, response events and answer WAV are saved under `captures/<id>/`. A supplied mono PCM16 16 kHz WAV can be tested with `live --audio-file PATH`. Such a test is not microphone-hardware evidence.

The upstream hosted backend is the default. Availability and rate limits are external; an error stops the turn rather than playing a canned answer. To use your own compatible endpoint, set `HF_REALTIME_CONNECTION_MODE=local` and `HF_REALTIME_WS_URL` in your terminal. See the [pinned upstream README](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/b9f58a3587d79a3275d4402d1a8d210649d62d50/README.md) for configuration. Do not put tokens in JSON or commit them.

## Emotional choreography and voice

`config/choreography.json` contains a distinct score for each exact answer/audio hash. Every beat has an exact text phrase, an emotion/state and a pinned `motion` recording. Phrase starts come from the matching `assets/conversation/qN/alignment.json`, bound to the exact WAV and transcript. `at` is a derived display value; changing it no longer changes timing.

| State | Source performance | Purpose |
| --- | --- | --- |
| Attentive | attentive1 | Listening in live mode |
| Curious | inquiring1 | Inquisitive tilts and antenna movement |
| Thinking | curious1 | Sustained exploratory movement |
| Explaining | understanding1 | Explanatory phrasing |
| Affirming | yes1 | Conclusion or confirmation |
| Happy | cheerful1 | Light positive resolution |
| Enthusiastic | enthusiastic1 | Emphasis on an interesting mechanism |
| Surprised | surprised1 | A counterintuitive contrast |

These are designed expressive signals, not claims about internal feelings. Thinking retains its existing recorded movement, including q1's downward curious tilt. Speech preserves each selected Emotions recording's head/antenna sequence, retimes its main excursion toward an aligned prominent word, and crossfades neighboring performances.

Local PocketSphinx forced alignment estimates word and phoneme timing from the actual WAV. Vowel centers approximate syllable nuclei. Sparse head accents follow acoustically prominent content words and phrase endings; antennas add small, smoother vowel-timed accents. Acoustic prominence is an estimate, not verified linguistic stress or exact syllabification. Motion is smoothed and bounded; body yaw remains zero and companion emotion sounds are not mixed into the answer.

The top-level `speech_motion` settings control `blend_s` (0.5 s), `smoothing_s` (0.12 s), `head_accent_deg` (2 degrees) and `antenna_accent_rad` (0.025 rad). Head speed/acceleration caps are 65 deg/s and 350 deg/s^2; these are ceilings, not constant movement speeds. Each beat can choose a `motion` from the pinned manifest and an `intensity` in (0,1]. To change phrase placement, edit its exact `phrase` anchor and regenerate timing:

```powershell
.\.venv312\Scripts\python.exe -X utf8 scripts/align_speech.py
```

This runs locally, preserves the WAVs, updates alignment hashes and derived `at` values, and resets review flags. Unrecognized vocabulary fails explicitly and requires a pronunciation entry; the study-specific number 340 is normalized to 'three hundred forty'. Live mode also aligns its complete captured answer before playback, adding preparation latency. All automatically aligned scores still need watch/listen review before setting `reviewed: true`; `session` enforces that gate and `trial` permits preview.

The six answers are genuine Conversation App captures with **Aiden** voice, mono PCM16 16 kHz. Each answer has one WAV, its transcript/response receipt, compact event metadata and alignment receipt. Changing an answer invalidates its audio, score and alignment bindings.

## Stop, logs and tests

Press Ctrl+C during a trial/live turn, or from another terminal in the app folder:

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 stop
```

The app stops audio and motion and attempts feedback-confirmed neutral recovery. One local TCP controller owns the robot; close unrelated SDK clients. This is not a physical emergency stop.

Trial logs are in `logs/`, including version, condition, binary factor, audio/motion hashes, emotional-state markers, command timing, measured pose feedback during speech, stop/errors and neutral recovery. Live captures and logs are separate and never count as participant data.

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m pytest -q
$run = "evidence/check-$(Get-Date -Format yyyyMMdd-HHmmss)"
.\.venv312\Scripts\python.exe -X utf8 .\scripts\validate_simulation.py --out $run
```

Validation plays A/B and stops B during thinking and during speech. It makes no backend requests. Successful software/simulator tests do not establish perceived emotion, physical safety or microphone-measured acoustic timing.

## Setup and study materials

From the Git workspace, `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1` copies the demo to the installed folder, preserves existing raw data, installs locked dependencies and the pinned Conversation App package. It leaves the simulator environment alone. `uv` is required. `requirements-lock.txt` is the single environment lock, specific to Windows/Python 3.12. It installs the Conversation App directly from its exact upstream revision; a fresh setup needs internet access.

Read `SOURCE_INTEGRATION.md`, `STUDY_PLAN.md`, `study/SURVEY.md`, and `VALIDATION.md`. After stimulus review, session commands remain:

```powershell
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 session --participant P01 --condition A
# Questionnaire between conditions.
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2 session --participant P01 --condition B
.\.venv312\Scripts\python.exe -X utf8 -m reachy_lab2.analysis --responses .\study\data\raw\responses.csv --logs .\logs --out .\analysis\pilot-v2
```

P01/P03 use AB; P02/P04 use BA. Analysis requires version-matched reviewed study logs and rejects the archived timing study. Raw templates contain no participant observations. Physical Part 3 demonstration and actual user-study collection remain separate unfinished course deliverables.
