# Greeting data dictionary

Raw templates have headers only; no participants or observations are fabricated. `study_version=antenna-greeting-v1`; `survey_version=HRIES-greeting-v1`.

| Fields | Meaning |
| --- | --- |
| participant_id; order; condition | De-identified P01…; assigned AB/BA; A/B |
| trial_id | UUID of the attempt rated; joins JSONL trial log |
| include; exclusion_reason | 1/0 analysis decision; reason required for 0 |
| soc_1–4; ani_1–4; age_1–4; dis_1–4 | HRIES integer 1–7; terms and corrected labels in SURVEY.md |
| valence; arousal | Separate exploratory integer 1–7 ratings; higher is more positive/more activated |
| movement_size | Integer 1–7; higher is larger perceived excursion |
| qualitative_response | Verbatim neutral open response, without identifying information |
| protocol_deviation | Relevant deviations; details in deviations.csv |
| agreement; age_band; robot_experience; reachy_experience | Participant sheet: yes/no; optional 18–24/25–34/35–44/45+; none/occasional/frequent; yes/no |
| assigned_order; actual_order; date; operator | Planned/actual sequence, session date and facilitator code |
| attempt; repeat_of | Log fields: 1 or 2, link to original failed/interrupted attempt |
| completion | Log-derived execution outcome per attempt: 1 completed; 0 interrupted/failed; NA unobserved |
| antenna_amplitude_deg | Commanded maximum displacement from calibrated neutral per antenna, degrees |
| angles_deg_right_left | Timestamped SDK-measured angles in degrees, right then left; mock values are command echoes |
| measured_neutral_deg_right_left | Mean of five pretrial feedback samples; subtracted from measured excursions |
| maximum_abs_displacement_deg; range_deg | Per-antenna max absolute baseline-corrected displacement and max-minus-min range |
| achieved_poll_hz; max_poll_gap_s | Achieved SDK polling rate and largest gap, not an independently verified sensor update rate |
| movement_start/end_s; speech_start/end_s | Relative event times; movement command dispatch and predicted DAC audio time, not measured acoustic onset |
| technically_valid; study_eligible | Software fidelity with real output; additionally physical participant mode with review gate |

Blank/NA means unobserved or skipped, with reason recorded; zero is an actual completion failure, never a missing rating. Store original JSONL and forms unchanged. Repeats retain original failures; use the first completed attempt for ratings and flag prior exposure. Report completion for **all attempts**, not only included successful ratings. `attempt_outcomes.csv` and `attempt_summary.csv` preserve that distinction. Missing HRIES items are not imputed. Paired B−A requires both nonmissing conditions. Technical/mock/simulator logs cannot be analyzed as participant evidence.
