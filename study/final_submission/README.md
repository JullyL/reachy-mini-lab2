# HRI Lab 2 final submission

The final report is `output/documents/HRI Lab 2 Final Report.docx`. It was rewritten from the uploaded `HRI Report Lab 2 (1).docx`; earlier repository reports are historical versions.

Four adults completed A (10°) and B (30°) antenna-amplitude greetings in counterbalanced order. There are eight condition records and four complete pairs. Sociability means are A=3.6875 and B=4.3125, with mean paired B−A=0.625. Arousal means are 3.75 and 4.50; valence means are 4.75 and 5.25. Completion is recorded as 4/4 in each condition. No questionnaire ratings are missing, and no exclusions or deviations were recorded.

## Reproduce the analysis

From the repository root with Python 3.12:

```sh
python -m pip install -r study/analysis-requirements.txt
python scripts/analyze_report_data.py --out analysis/reproduced-pilot
```

`analysis/` here contains the generated dataset, full-precision summaries, participant differences, recorded completion, qualitative coding, both figures in PNG/SVG, and a source/missingness audit. The script checks raw XLSX/CSV agreement before calculating scores. Qualitative wording comes from the raw XLSX; apostrophe typography is normalized only for comparison with the CSV.

`materials/` contains conditions, facilitator/background wording, the survey, data dictionary, and qualitative definitions extracted from the report appendices. These filenames refer to supporting text materials; the report provides the formatted questionnaire.

## Data provenance

Raw inputs are preserved in `study/data/raw/`. Session dates, age band, agreement, operator, and prior experience come from `participants.csv`; gender and questionnaire responses come from the raw XLSX. Recorded deviations come from `deviations.csv`.

The earlier `study/data/Analysis-ready data.xlsx` contains stray `40` text in seven Date cells and fourteen failure/notes cells. It is retained unchanged for provenance and is not the canonical analysis dataset. The new analysis uses raw responses and register metadata, without treating those stray values as observations.

## Missing physical evidence

Participant trial logs and measured physical angle records are missing from this submission; the team reports they are retained on another person's computer. The archived calibration is unverified, conditions remain provisional, and physical review remains unapproved. Exact room/distance/audio-device/volume settings, acoustic timing, neutral-return criteria, head/base checks, and an all-attempt audit cannot be independently verified. No physical verification flags or logs were invented.

The available package reproduces the questionnaire analysis. Full reconstruction and independent verification of the original physical exposure require the missing records. The stricter `reachy_lab2.analysis` module expects its richer schema and matching eligible physical logs; it is separate from the descriptive reproduction command above.

## Part 8 coverage

The report contains Introduction, Method, Results, Discussion, References, and appendices for conditions/implementation, facilitator and participant materials, the questionnaire, data dictionary, qualitative source responses/coding rules, and reproduction/submission instructions. Figures and all reported numerical results derive from the same raw data. The reproduction archive adds a local app/configuration/audio/evidence snapshot and a SHA-256 manifest. Historical software evidence is clearly distinguished from participant evidence.
