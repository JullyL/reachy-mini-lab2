"""Parts 6-7: explicit missingness, separate HRIES dimensions, paired summaries.

No participant data is bundled. Never write into the supplied raw-data folder.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

from .trial import ROOT, digest, load_json
from .choreography import STUDY_VERSION

DIMENSIONS = {"sociability": "soc", "animacy": "ani", "agency": "age", "disturbance": "dis"}
ITEMS = [f"{prefix}_{i}" for prefix in DIMENSIONS.values() for i in range(1, 5)]
FIELDS = ["participant_id", "condition", "order", "session_id", "study_version", "survey_version", "observer_coverage", "include",
          "exclusion_reason", *ITEMS, "expression_check", "qualitative_response", "protocol_deviation"]


def rating(value):
    if value in ("", "NA", None):
        return None
    number = int(value)
    if str(number) != str(value) or not 1 <= number <= 7:
        raise ValueError(f"Rating must be an integer 1-7 or blank/NA, got {value!r}")
    return number


def score(row):
    result = {}
    for dimension, prefix in DIMENSIONS.items():
        values = [rating(row.get(f"{prefix}_{i}")) for i in range(1, 5)]
        result[dimension] = None if None in values else statistics.mean(values)
        result[dimension + "_n_items"] = sum(v is not None for v in values)
    result["expression_check"] = rating(row.get("expression_check"))
    return result


def write_csv(path, records, fields):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def analyze(raw, logs, out):
    raw, logs, out = Path(raw).resolve(), Path(logs).resolve(), Path(out).resolve()
    if raw.parent == out or raw.parent in out.parents:
        raise ValueError("Analysis output must be outside the raw data directory")
    with raw.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("Use the provided responses.csv column schema")
        rows = list(reader)
    if not rows:
        raise ValueError("No participant responses: no study results have been generated")
    protocol = load_json(ROOT / "study/protocol.json")
    stimuli = {q["id"]: q["sha256"] for q in load_json(ROOT / "config/questions.json")["questions"]}
    sessions, audit = {}, {str(raw): digest(raw)}
    for file in sorted(logs.glob("*.jsonl")):
        records = [json.loads(s) for s in file.read_text().splitlines() if s.strip()]
        if not records:
            continue
        audit[str(file)] = digest(file)
        end = records[-1]
        # Retain incomplete logs for auditing, but never treat them as valid trials.
        if end["marker"] == "TRIAL_END" and end.get("study_version") == STUDY_VERSION:
            sessions.setdefault(end["session_id"], []).append(end)
    ready, seen = [], set()
    for row in rows:
        pid, condition = row["participant_id"], row["condition"]
        if row["study_version"] != STUDY_VERSION:
            raise ValueError("Do not mix the archived timing study with expressive-performance-v2")
        if pid not in protocol["assignments"] or row["order"] != protocol["assignments"][pid]:
            raise ValueError(f"Unknown ID or assignment mismatch: {pid}")
        if condition not in "AB" or len(condition) != 1 or row["include"] not in ("0", "1"):
            raise ValueError("Invalid condition or inclusion flag")
        if not row["survey_version"]:
            raise ValueError("Record the approved questionnaire version")
        if row["observer_coverage"] not in ("complete", "missing"):
            raise ValueError("Observer coverage must be complete or missing; unknown counts are not zero")
        if row["include"] == "0" and not row["exclusion_reason"]:
            raise ValueError("Exclusions require a reason")
        trial_rows = sessions.get(row["session_id"], [])
        valid = len(trial_rows) == len(protocol["question_order"]) and all(
            r["technically_valid"] and r["participant_id"] == pid and r["condition"] == condition
            and r["condition_order"] == row["order"] and r["input_mode"] == "operator-mediated"
            and r["condition_position"] == row["order"].index(condition) + 1
            and r.get("choreography_reviewed") is True
            and r.get("expressive_motion") == (1 if condition == "B" else 0)
            and r.get("answer_sha256") == stimuli.get(r["question_id"])
            for r in trial_rows)
        valid = valid and sorted((r["trial_sequence"], r["question_id"]) for r in trial_rows) == list(enumerate(protocol["question_order"], 1))
        if row["include"] == "1":
            if not valid:
                raise ValueError(f"Included {pid}/{condition} needs six valid matching trial logs")
            if (pid, condition) in seen:
                raise ValueError("Duplicate included participant/condition; adjudicate repeats explicitly")
            seen.add((pid, condition))
        counts = sum(r["repeat_prompt_count"] for r in trial_rows) if valid and row["observer_coverage"] == "complete" else None
        ready.append({"participant_id": pid, "condition": condition, "order": row["order"], "study_version":row["study_version"],
                      "session_id": row["session_id"], "include": row["include"],
                      "exclusion_reason": row["exclusion_reason"],
                      "survey_version": row["survey_version"], "observer_coverage": row["observer_coverage"],
                      **{item: rating(row[item]) for item in ITEMS}, **score(row),
                      "repeat_prompt_count": counts, "valid_trial_count": sum(bool(r["technically_valid"]) for r in trial_rows),
                      "qualitative_response": row["qualitative_response"],
                      "protocol_deviation": row["protocol_deviation"]})
    measures = [*DIMENSIONS, "expression_check", "repeat_prompt_count"]
    summaries, pairs = [], []
    included = [r for r in ready if r["include"] == "1"]
    for measure in measures:
        for condition in "AB":
            values = [r[measure] for r in included if r["condition"] == condition and r[measure] is not None]
            summaries.append({"measure": measure, "condition": condition, "n": len(values),
                "mean": statistics.mean(values) if values else None,
                "sd": statistics.stdev(values) if len(values) > 1 else None,
                "median": statistics.median(values) if values else None})
        for pid in sorted({r["participant_id"] for r in included}):
            by = {r["condition"]: r for r in included if r["participant_id"] == pid}
            a = by.get("A", {}).get(measure)
            b = by.get("B", {}).get(measure)
            pairs.append({"participant_id": pid, "measure": measure, "A": a, "B": b,
                          "B_minus_A": None if a is None or b is None else b-a})
    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / "analysis_ready.csv", ready, list(ready[0]))
    write_csv(out / "condition_summary.csv", summaries, list(summaries[0]))
    write_csv(out / "paired_differences.csv", pairs, ["participant_id", "measure", "A", "B", "B_minus_A"])
    qualitative = [{k: row[k] for k in ["participant_id", "condition", "include", "qualitative_response"]} |
                   {"category": "", "coding_note": ""} for row in rows]
    write_csv(out / "qualitative_coding.csv", qualitative, list(qualitative[0]))
    audit["protocol_sha256"] = digest(ROOT / "study/protocol.json")
    audit["missingness_policy"] = "No imputation; dimension score requires four valid items; pairs require A and B"
    (out / "audit.json").write_text(json.dumps(audit, indent=2))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharey=True)
    for ax, dimension in zip(axes.flat, DIMENSIONS):
        for pair in pairs:
            if pair["measure"] == dimension and pair["A"] is not None and pair["B"] is not None:
                ax.plot([0, 1], [pair["A"], pair["B"]], "o-", alpha=.75, label=pair["participant_id"])
        ax.set(title=dimension.title(), xticks=[0, 1], xticklabels=["A: brief cue", "B: expressive"], ylim=(.8, 7.2), ylabel="HRIES mean (1-7)")
        ax.grid(axis="y", alpha=.2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=min(len(labels), 6))
    fixture = all(r["survey_version"].startswith("SYNTHETIC") for r in rows)
    title = "SYNTHETIC TEST DATA ONLY" if fixture else "Paired participant ratings"
    fig.suptitle(title + "; higher disturbance means more disturbance")
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(out / "paired_hries.png", dpi=200)
    fig.savefig(out / "paired_hries.pdf")
    plt.close(fig)
    return ready


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.responses, args.logs, args.out)
