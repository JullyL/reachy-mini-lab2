# Post-condition survey specification

Administer after each complete six-question block. Use the same wording, item order and scale in both blocks. The participant should rate the robot just experienced, without seeing A/B labels. The primary HRIES dimension is animacy; administer all four dimensions regardless.

Use Table S1 on page 2 of the [assignment-linked published supplement](https://public-pages-files-2025.frontiersin.org/articles/1585589/file/Data_Sheet_1.pdf/1585589_data-sheet_1/1) to obtain the official questionnaire wording and response anchors. Original scale: [Spatola et al. (2021)](https://doi.org/10.1007/s12369-020-00667-4). Store the questionnaire version used in every response row.

| CSV columns in order | HRIES terms in that order |
| --- | --- |
| soc_1, soc_2, soc_3, soc_4 | Warm, Likeable, Trustworthy, Friendly |
| ani_1, ani_2, ani_3, ani_4 | Alive, Natural, Real, Human-like |
| age_1, age_2, age_3, age_4 | Self-reliant, Rational, Intentional, Intelligent |
| dis_1, dis_2, dis_3, dis_4 | Creepy, Scary, Uncanny, Weird |

**Resolve before participant collection:** the linked supplement lists the positive labels at points 5 and 6 in an apparently reversed intensity order. Do not silently repair or substitute an agree/disagree scale for HRIES. Obtain the course-approved anchor wording, document the decision and adaptation from general robot ratings to this just-completed interaction, and use it consistently. The numeric scoring code accepts integers 1-7 but does not establish that an unresolved questionnaire is valid.

Additional study-specific manipulation check: "The robot used expressive head and antenna movements while preparing and giving its answers." Use 1 = strongly disagree through 7 = strongly agree. This is separate from HRIES and is not a validated scale. Record this as `expression_check`; a higher score indicates more perceived expressive movement. Use `study_version=expressive-performance-v2`.

Neutral open question: "What did you think the robot's movements meant, and how did they affect your experience?" Record the response accurately without coaching. Do not collect names or identifying stories.

The behavioral measure is observer-counted repeated/rephrased question utterances during the waiting interval; it is collected through app marks, not the survey. Record `observer_coverage` as `complete` or `missing`. Missing coverage leaves that measure unscored rather than converting it to zero.
