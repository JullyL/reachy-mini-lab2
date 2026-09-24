# Source integration map: expressive-performance-v2

| Source and pinned revision | Actual reused capability | Runtime and evidence |
| --- | --- | --- |
| [Reachy Mini Conversation App](https://github.com/pollen-robotics/reachy_mini_conversation_app/tree/b9f58a3587d79a3275d4402d1a8d210649d62d50), Apache-2.0 | Complete `HuggingFaceRealtimeHandler`, session allocation/configuration, microphone PCM receive, server transcription, response queue/lifecycle, streaming audio decoding, transcript observers | Installed directly from the pinned upstream archive by `requirements-lock.txt`; no duplicate repository checkout is needed. `reachy_lab2/conversation.py::make_handler` subclasses it; `capture_turn` invokes it. Six real captures are in `assets/conversation/q1` through `q6`, with backend response IDs and completion events. |
| [Pollen Robotics Emotions](https://huggingface.co/spaces/pollen-robotics/emotions/tree/cde39d23da61ada61d9ae4635bee051334434b44), README-declared MIT | Trajectory parsing/decimation, named emotion-library playback pattern, `trajectoryPlayer.ts` distance-scaled prelude policy | `motion.py` parser/decimator feeds `choreography.py::EmotionLibrary`. `emotion_player.py::transition_duration` ports `computeInitialGotoDuration`/`headMagicMm` and runs in `SimRobot.neutral`. The full original inspected TS sources are retained. |
| [Associated emotion dataset](https://huggingface.co/datasets/pollen-robotics/reachy-mini-emotions-library/tree/873ae49f0b89114b7e535eff0c1f7560d21d9357), Apache-2.0 | attentive1, inquiring1, curious1, understanding1, yes1, cheerful1, enthusiastic1, surprised1 | Real head/antenna performance assets, pinned and SHA-256 verified by `assets/motion/emotions/manifest.json`. This is content associated with Emotions, not a third independent source app. |

## What the custom integration adds

A single exclusive scheduler coordinates backend lifecycle states and emotional performances. Fixed study replay uses one manually authored phrase/state score per answer. Source motion is interpolated at 50 Hz, original offsets removed, scaled down only when needed, retimed and smoothed. Thinking clips ease into/out of neutral; speech crossfades the full source sequences and adds aligned accents. Bounds: translation norm 8 mm, head rotation norm 22 degrees, antenna norm 0.65 rad; retiming speeds are bounded at 0.04 m/s, 1.8 rad/s head and 3 rad/s antenna vector. These are simulator design bounds, not physical certification. Body yaw remains zero.

The Emotions transition policy measures head translation in millimeters plus rotation in degrees, weighted at 0.02 s/unit, and antenna change at 0.005 s/degree. It skips a prelude below 0.15 s, otherwise clamps to 0.2-1.5 s. Our recovery uses this duration and a minimum-jerk interpolation, then checks actual pose feedback.

The actual upstream conversation engine is not replaced with our PCM conversion helper. It runs in `live` mode and was used to produce all six active study answers. Overrides disable a startup greeting and arbitrary backend motion tools, set a concise science-explainer instruction, and use explicit audio commit with transcription-before-response ordering. The motor scheduler remains the sole writer. Live responses are fully buffered before playback; we do not claim upstream low-latency streaming playback or voice barge-in.

## Honest boundaries

- Study trials are operator-triggered replay of real backend captures. Microphone and LLM calls do not happen inside A/B study trials.
- Active capture voice is HF Aiden. There is no separate TTS preparation provider.
- The Emotion wheel UI, JS/WebRTC daemon-upload transport, OAuth, companion emotion sounds and camera are not used. Source playback policy is adapted to Python SDK transport.
- Per-question speech timing now uses local automatic forced word/phone alignment of the WAV. Word and vowel-nucleus timing is inspectable but has not been manually validated; acoustic prominence is not ground-truth linguistic stress.
- Physical robot output and physical microphone validation are not established by the simulator or synthetic audio tests.

## Emotion and speech-rhythm refinement

Speech uses the complete head/antenna sequences from the selected pinned Emotions recordings, not single extracted poses. Each beat names its source `motion`; the source's main head excursion is retimed toward an aligned salient word, with half-second crossfades between clips and temporal smoothing. Original movement order is retained, but timing, amplitude and transitions are adapted. The body-yaw channel is still disabled.

`reachy_lab2/prosody.py` uses the separate local PocketSphinx 5.1.1 package with its bundled English acoustic model and pronunciation dictionary to align the exact answer text and WAV in two passes. This capability does not come from the Emotions Space or Conversation App. The receipts preserve word/phone times, approximate syllable nuclei, engine/settings, vocabulary overrides and audio/text hashes. `choreography.py` adds sparse head accents from acoustic prominence and phrase endings and light antenna accents at vowel centers. It does not claim measured human-like behavior, exact linguistic stress, lip sync, or unchanged source playback.

Thinking and A trajectories are unchanged. Speech settings, source hashes and alignment receipt hashes are included in the compiled trajectory hash; prior perceptual review is invalidated. Companion emotion sounds and the Space UI remain unused. The source library has been integrated more deeply through its full recorded sequences, rather than through its browser transport.

Capture event logs retain event types, timing, final transcripts and response IDs/status. Duplicate base64 PCM is omitted because it is already stored in the hash-bound answer WAV. Existing receipts retain the original event-file hash to identify the pre-compaction evidence.
