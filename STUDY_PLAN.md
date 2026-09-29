# Study plan: expressive-performance-v2

## Part 3: custom integration and experimental conditions

Potential final-project topic: how an embodied assistant's emotional nonverbal performance changes human perceptions and the experience of waiting and listening. The actual Conversation App supplies backend-generated question answers and speech; the Emotions component supplies a repertoire of recorded head/antenna performances and playback/transition logic. `SOURCE_INTEGRATION.md` identifies the exact reused code and limitations.

This exploratory within-participant study compares the original brief-cue style with a sustained expressive performance. The factor is `expressive_motion`, unit: binary, A=0, B=1. It is one categorical performance treatment, comprising thinking and speaking motion together. Do not describe it as an isolated amplitude, timing, semantic-congruence or emotion manipulation.

| Element | A: brief cue | B: expressive performance | Control |
| --- | --- | --- | --- |
| expressive_motion | 0 | 1 | Only condition selector |
| Thinking | Original one-second cue | Curious/thinking sequence through the wait | First motion command at 0.5 s |
| Speech movement | Neutral | Phrase-specific emotional performance | Identical answer WAV |
| Answer start | 5.0 s | 5.0 s | Measured from operator acceptance |
| Content / voice | q1-q6 backend captures, Aiden | Exact same captures | Same order, wording, volume and device |
| Question input | Enter after participant finishes | Same | Standard operator rule |
| Initial/final pose | Neutral | Neutral | Feedback checked |

The differing movement content may cross a visibility threshold at different times despite equal command starts. B intentionally changes movement quantity, amplitude, semantic association and duration as a bundle. Interpret effects at the bundle level. Different constituent contributions need a later factorial or tightly isolated manipulation.

All six active answers were genuinely generated through the pinned Conversation App handler from text-submitted questions. The study replays those captures so provider variation is held constant. It does not run live recognition or generation during participant trials. Live microphone/text/WAV mode demonstrates that integration separately and is excluded from study analysis. Never pool the archived timing experiment or older Bella voice version with this study.

## Part 4: constructs and exploratory research questions

1. How does a sustained emotional performance, compared with a brief preparation cue, affect perceived robot animacy in a fixed-answer Q&A interaction?
2. How does the performance affect repeated/rephrased questions during waiting, and how do participants interpret its movements during preparation and speech?

No directional claim that more motion is better is assumed. The primary HRIES dimension is now **animacy**, selected before any data collection. Exaggeration could raise some impressions while reducing naturalness or increasing disturbance.

| Construct | Operationalization | Limit |
| --- | --- | --- |
| Emotional performance | Binary expressive_motion, frozen source/score/compiled-motion hashes | A bundle, not a calibrated expressiveness scale |
| Perceived animacy | Mean of four HRIES animacy items | Subjective perception, not actual feelings or intelligence |
| Sociability / agency / disturbance | Separate four-item HRIES means | Secondary exploratory outcomes; higher disturbance is more disturbance |
| Perceived manipulation | Expression-check item after each block | Study-specific, not validated |
| Waiting behavior | Observer-counted repeated/rephrased question utterances before speech | May have floor effects; not a direct measure of confusion |
| Interpretation | Neutral open-ended response | Do not instruct participants to see curiosity/happiness |

Use the [original HRIES paper](https://doi.org/10.1007/s12369-020-00667-4) and [course-linked implementation](https://doi.org/10.3389/frobt.2025.1585589) for measurement background. [Robot Feedback Design for Response Delay](https://doi.org/10.1007/s12369-023-01068-z) remains relevant background for waiting behavior; it does not establish the effect of this performance. The final report needs a source-grounded argument specifically for emotional motion/animacy, rather than transferring the old cue-timing rationale unchanged.

## Part 5: pilot procedure

Recruit at least four adult volunteers outside the team. Use de-identified P01-P04. Preassign P01/P03=AB, P02/P04=BA. Collect only relevant optional demographics and robot familiarity. Explain the limits of a small convenience sample. No participant data has been collected.

Before recruitment, watch/listen to every B answer, tune exact phrase timing if needed and mark each frozen score reviewed. Pilot whether the states are legible and whether the performance is distracting. Resolve the HRIES anchor discrepancy documented in `study/SURVEY.md`. The `session` command refuses unreviewed scores. This review does not establish physical safety or authorize hardware use.

Each block uses q1-q6 once in the same order, with five ten-second pauses. Current captured speech totals about 85.5 s, plus 30 s of scheduled waiting, reading time and neutral recovery. Rehearse to verify the course's 3-5 minute target; adjust only a shared protocol if necessary. Collect the questionnaire after the block, not after every question.

Standardize room, robot display, participant distance, lighting, noise, speaker placement/volume, operator stance and question presentation. Hide A/B labels and emotion labels from participants. Use a second observer when available and record complete/missing coverage.

Facilitator script:

1. Verify both conditions, stop, speakers, logs and neutral recovery before arrival.
2. Say: "We are studying people's experience of a robot question-and-answer interaction. You will try two versions and answer a short questionnaire after each. Participation is voluntary; you may stop at any time."
3. Obtain agreement, assign ID/order and explain the activity without claiming one version is better.
4. Say: "Please read each displayed question aloud to the robot and listen to its answer. We will move through six questions. You can interact naturally while waiting. Tell us if you want to stop."
5. Press Enter immediately after each completed question. The observer marks one event per distinct repeated/rephrased question during the acceptance-to-speech interval and records operator errors.
6. After each block, administer all 16 HRIES items, the expression check and the open question. Record the session ID.
7. Debrief: "One version used a brief movement; the other used a longer expressive performance during preparation and speech. The spoken answers were generated beforehand and were identical in both versions. The waiting interval was scheduled, not live model thinking. We are studying how people interpret these movements."
8. Preserve original logs and document missingness, faults, repeats and exclusions before comparing ratings.

Completed means speech finished and neutral recovery succeeded. Interrupted means a stop was requested. Failed means an execution/timing resource error or unsuccessful neutral recovery. `technically_valid` additionally requires real audio, simulator feedback, timing tolerance and no skipped frames or recorded operator errors; it is not a perceptual-validity or consent flag. Repeated blocks require new IDs and `--repeat-of`; retain originals and explicitly adjudicate inclusion.

The behavioral count excludes the original question, ordinary backchannels and utterances after speech begins. Zero requires continuous observation; missing coverage remains missing. Do not repurpose motion telemetry as the human behavioral outcome.

## Parts 6-7: data and analysis

Use `study/data/raw/` templates with `study_version=expressive-performance-v2`. Preserve raw originals read-only after collection, with corrections documented separately. Analysis joins each response to six matching operator-mediated trials and checks study version, condition/order, questions, score-review flag and engineering validity. It rejects old timing-study data and never invents observations from an empty dataset.

Compute the four HRIES means separately, requiring all four observed items per dimension. No combined score or imputation. Report per-measure n, mean, sample SD, median and paired B-minus-A differences. The plot labels are A: brief cue and B: expressive. The separate expression check is not part of HRIES.

Develop 2-4 qualitative categories from actual responses, with definitions, inclusion/exclusion rules and de-identified examples. Compare qualitative interpretations with ratings and observed behavior, including disagreements. Answer each RQ as supported, contradicted, mixed or insufficient for this pilot.

Discuss small N, convenience sampling, repetition/order carryover, operator/observer expectancy, floor effects, emotional ambiguity, approximate phrase synchronization, the bundled manipulation and simulator/computer-speaker context. A follow-up can isolate thinking versus speaking motion or compare congruent versus incongruent emotion while controlling motion quantity. Physical testing and robot-only A/B clips remain required course work before claiming Part 3 physical completion.
