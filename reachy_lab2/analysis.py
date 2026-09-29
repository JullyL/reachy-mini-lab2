"""Separate HRIES dimensions, paired descriptive summaries and an attempt audit."""
import argparse
import csv
import json
import statistics
from pathlib import Path

from .greeting import STUDY_VERSION
from .trial import ROOT, digest, load_json

DIMENSIONS = {"sociability": "soc", "animacy": "ani", "agency": "age", "disturbance": "dis"}
ITEMS = [f"{prefix}_{i}" for prefix in DIMENSIONS.values() for i in range(1, 5)]
FIELDS = ["participant_id", "condition", "order", "trial_id", "study_version", "survey_version", "include",
          "exclusion_reason", *ITEMS, "valence", "arousal", "qualitative_response", "movement_size", "protocol_deviation"]


def rating(value):
    if value in ("", "NA", None):
        return None
    number = int(value)
    if str(number) != str(value) or not 1 <= number <= 7:
        raise ValueError(f"Rating must be an integer 1-7 or blank/NA: {value!r}")
    return number


def score(row):
    result = {}
    for dimension, prefix in DIMENSIONS.items():
        values = [rating(row.get(f"{prefix}_{i}")) for i in range(1, 5)]
        result[dimension] = None if None in values else statistics.mean(values)
        result[dimension+"_n_items"] = sum(v is not None for v in values)
    for name in ("valence", "arousal", "movement_size"):
        result[name] = rating(row.get(name))
    return result


def write_csv(path, records, fields):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def analyze(raw, logs, out):
    raw, logs, out = Path(raw).resolve(), Path(logs).resolve(), Path(out).resolve()
    if raw.parent == out or raw.parent in out.parents:
        raise ValueError("Analysis output must be outside raw data")
    with raw.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("Use the greeting responses.csv schema")
        rows = list(reader)
    if not rows:
        raise ValueError("No participant responses; no study results generated")
    protocol = load_json(ROOT/"study/protocol.json")
    trials, audit, attempts = {}, {str(raw): digest(raw)}, []
    for path in sorted(logs.glob("*.jsonl")):
        records = [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
        if not records or records[0].get("study_version") != STUDY_VERSION:
            continue
        audit[str(path)] = digest(path)
        end = records[-1]
        if end["marker"] != "TRIAL_END":
            attempts.append({"trial_id": end["trial_id"], "participant_id": end["participant_id"], "condition": end["condition"], "completion": None, "status": "incomplete log", "reason": "Missing terminal record"})
            continue
        if end["trial_id"] in trials:
            raise ValueError("Duplicate trial UUID in logs")
        trials[end["trial_id"]] = end
        attempts.append({"trial_id": end["trial_id"], "participant_id": end["participant_id"], "condition": end["condition"], "completion": end["completion"], "status": end["completion_status"], "reason": end["error"]})
    ready, seen, frozen = [], set(), None
    for row in rows:
        pid, condition = row["participant_id"], row["condition"]
        if row["study_version"] != STUDY_VERSION or row["survey_version"] != protocol["survey_version"]:
            raise ValueError("Study/survey version mismatch")
        if pid not in protocol["assignments"] or row["order"] != protocol["assignments"][pid]:
            raise ValueError("Unknown participant or assignment mismatch")
        if condition not in ("A", "B") or row["include"] not in ("0", "1"):
            raise ValueError("Invalid condition or inclusion flag")
        if row["include"] == "0" and not row["exclusion_reason"]:
            raise ValueError("Exclusions require a reason")
        trial = trials.get(row["trial_id"])
        valid = trial and trial.get("study_eligible") and trial["participant_id"] == pid and trial["condition"] == condition and trial["condition_order"] == row["order"] and trial["condition_position"] == row["order"].index(condition)+1
        if row["include"] == "1":
            if not valid:
                raise ValueError(f"Included {pid}/{condition} needs a matching eligible physical trial")
            if (pid, condition) in seen:
                raise ValueError("Duplicate included participant/condition")
            seen.add((pid, condition))
            fingerprint = tuple(trial[k] for k in ("configuration_sha256", "audio_sha256", "calibration_sha256", "software_sha256"))
            if frozen is not None and fingerprint != frozen:
                raise ValueError("Do not combine different stimulus/code/calibration versions")
            frozen = fingerprint
            completed = [r for r in trials.values() if r["participant_id"] == pid and r["condition"] == condition and r["completion"] == 1]
            if min(completed, key=lambda r:r["wall_time_utc"])["trial_id"] != row["trial_id"]:
                raise ValueError("Use ratings from the first completed attempt")
        ready.append({**row, **score(row), "completion": trial["completion"] if trial else None,
                      "prior_exposure": bool(trial and trial["repeat_of"])})
    included = [r for r in ready if r["include"] == "1"]
    measures = [*DIMENSIONS, "valence", "arousal", "movement_size", "completion"]
    summaries, pairs = [], []
    for measure in measures:
        for condition in "AB":
            values = [r[measure] for r in included if r["condition"] == condition and r[measure] is not None]
            summaries.append({"measure": measure, "condition": condition, "n": len(values),
                "mean": statistics.mean(values) if values else None,
                "sd": statistics.stdev(values) if len(values)>1 else None,
                "median": statistics.median(values) if values else None})
        for pid in sorted({r["participant_id"] for r in included}):
            by = {r["condition"]: r for r in included if r["participant_id"] == pid}
            a, b = by.get("A", {}).get(measure), by.get("B", {}).get(measure)
            pairs.append({"participant_id": pid, "measure": measure, "A": a, "B": b,
                          "B_minus_A": None if a is None or b is None else b-a})
    out.mkdir(parents=True, exist_ok=False)
    write_csv(out/"analysis_ready.csv", ready, list(ready[0]))
    write_csv(out/"condition_summary.csv", summaries, list(summaries[0]))
    write_csv(out/"paired_differences.csv", pairs, ["participant_id", "measure", "A", "B", "B_minus_A"])
    # All physical participant attempts, including failures, remain in the denominator.
    physical_ids = {r["trial_id"] for r in trials.values() if r["robot_backend"] == "physical" and r["participant_id"] != "TECH"}
    objective = [r for r in attempts if r["trial_id"] in physical_ids or r["status"] == "incomplete log"]
    write_csv(out/"attempt_outcomes.csv", objective, ["trial_id", "participant_id", "condition", "completion", "status", "reason"])
    objective_summary = []
    for condition in "AB":
        vals = [r["completion"] for r in objective if r["condition"] == condition and r["completion"] is not None]
        objective_summary.append({"condition": condition, "observed_attempts": len(vals), "completed": sum(vals), "completion_proportion": statistics.mean(vals) if vals else None})
    write_csv(out/"attempt_summary.csv", objective_summary, list(objective_summary[0]))
    qualitative = [{k:r[k] for k in ("participant_id", "condition", "include", "qualitative_response")} | {"category":"", "coding_note":""} for r in rows]
    write_csv(out/"qualitative_coding.csv", qualitative, list(qualitative[0]))
    audit.update(primary_hries_outcome="sociability", exploratory_outcomes=["valence", "arousal"],
                 missingness_policy="No imputation; four responses per HRIES mean; pairs require A and B")
    (out/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharey=True)
    for ax, dimension in zip(axes.flat, DIMENSIONS):
        for pair in pairs:
            if pair["measure"] == dimension and pair["A"] is not None and pair["B"] is not None:
                ax.plot([0, 1], [pair["A"], pair["B"]], "o-", alpha=.75)
        ax.set(title=dimension.title(), xticks=[0, 1], xticklabels=["A", "B"], ylim=(.8, 7.2), ylabel="HRIES mean (1–7)")
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Paired ratings; sociability primary; higher disturbance means more disturbance")
    fig.tight_layout()
    fig.savefig(out/"paired_hries.png", dpi=200)
    plt.close(fig)
    return ready


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.responses, args.logs, args.out)
