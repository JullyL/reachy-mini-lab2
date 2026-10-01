# Greeting Data Dictionary

This data dictionary describes the de-identified participant data collected for the Reachy Mini antenna-amplitude greeting study.

The study used a within-subject design in which each participant experienced both antenna-amplitude conditions. Condition order was counterbalanced across participants.

- **Condition A:** 10° antenna amplitude from neutral per antenna
- **Condition B:** 30° antenna amplitude from neutral per antenna
- **Study version:** `antenna-greeting-v1`
- **Survey version:** `HRIES-greeting-v1`

Four adult participants (P01–P04) completed both conditions, resulting in eight condition-level observations. No participant names, contact information, or other direct identifiers are stored in the dataset.

## Participant and Condition Variables

| Field | Meaning |
| --- | --- |
| participant_id | De-identified participant code (P01–P04) |
| gender | Participant-reported gender |
| physical_robot_experience | Prior experience with physical robots: none / prior experience |
| reachy_experience | Prior experience with Reachy Mini: yes / no |
| greeting_number | Whether the condition was experienced first or second: 1 / 2 |
| condition | Experimental condition: A = 10° antenna amplitude; B = 30° antenna amplitude |
| order | Counterbalanced condition order: AB / BA |

## HRIES Measures

All HRIES items use a 1–7 response scale. The four HRIES dimensions are calculated separately. No overall HRIES score is calculated.

| Field | Meaning |
| --- | --- |
| warm | HRIES Sociability item: Warm |
| likeable | HRIES Sociability item: Likeable |
| trustworthy | HRIES Sociability item: Trustworthy |
| friendly | HRIES Sociability item: Friendly |
| alive | HRIES Animacy item: Alive |
| natural | HRIES Animacy item: Natural |
| real | HRIES Animacy item: Real |
| human_like | HRIES Animacy item: Human-like |
| self_reliant | HRIES Agency item: Self-reliant |
| rational | HRIES Agency item: Rational |
| intentional | HRIES Agency item: Intentional |
| intelligent | HRIES Agency item: Intelligent |
| creepy | HRIES Disturbance item: Creepy |
| scary | HRIES Disturbance item: Scary |
| uncanny | HRIES Disturbance item: Uncanny |
| weird | HRIES Disturbance item: Weird |

## Calculated HRIES Variables

Each dimension score is calculated as the mean of its four component items. All four items must be present; otherwise, the dimension score is treated as missing.

| Field | Calculation |
| --- | --- |
| sociability_avg | Mean of Warm, Likeable, Trustworthy, and Friendly |
| animacy_avg | Mean of Alive, Natural, Real, and Human-like |
| agency_avg | Mean of Self-reliant, Rational, Intentional, and Intelligent |
| disturbance_avg | Mean of Creepy, Scary, Uncanny, and Weird |

No overall HRIES score is calculated.

## Additional Subjective and Qualitative Measures

| Field | Meaning |
| --- | --- |
| valence | Perceived emotional valence, 1–7; 1 = very negative, 4 = neutral, 7 = very positive |
| arousal | Perceived emotional activation, 1–7; 1 = very low activation, 4 = moderate activation, 7 = very high activation |
| qualitative_response | Participant's open-ended description of Reachy Mini during the greeting |
| movement_size | Perceptual manipulation check, 1–7; higher values indicate larger perceived antenna movement |

## Objective and Data-Quality Variables

| Field | Meaning |
| --- | --- |
| completion | Greeting execution outcome: 1 = completed; 0 = interrupted/failed; NA = unobserved |
| failure_interruption_reason | Reason for an interrupted or failed trial; blank when no failure or interruption occurred |
| notes_deviations | Relevant protocol deviations or session notes; blank when none were recorded |

## Missing Data and Data-Quality Rules

Blank or NA values indicate an unobserved or skipped response and are not treated as zero.

Missing HRIES items are not imputed. A HRIES dimension score is calculated only when all four component items are available.

All four participants completed both conditions, producing eight condition-level observations. All eight greetings were completed successfully. No HRIES responses were missing, and no trials were excluded. No technical failures, interruptions, or protocol deviations were recorded.

All participant responses are retained in the de-identified raw dataset. The analysis-ready dataset preserves these responses and adds standardized participant variables and the four calculated HRIES dimension scores.

Within-participant comparisons use Condition B minus Condition A (B − A) when both condition values are available.
