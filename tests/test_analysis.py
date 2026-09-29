import pytest

from reachy_lab2.analysis import ITEMS, rating, score, analyze, FIELDS

import csv
import json


def test_hries_keeps_dimensions_separate():
    row = {name: "4" for name in ITEMS}
    row.update({f"age_{i}": str(i) for i in range(1, 5)})
    result = score(row)
    assert result["agency"] == 2.5
    assert result["sociability"] == 4
    assert "overall" not in result


def test_missing_item_does_not_impute():
    row = {name: "7" for name in ITEMS}
    row["dis_3"] = "NA"
    result = score(row)
    assert result["disturbance"] is None
    assert result["disturbance_n_items"] == 3
    assert result["agency"] == 7


@pytest.mark.parametrize("value", ["0", "8", "4.5", "nan", "-1"])
def test_bad_rating_is_rejected(value):
    with pytest.raises(ValueError):
        rating(value)


def test_empty_raw_produces_no_results(tmp_path):
    raw = tmp_path / "raw" / "responses.csv"
    raw.parent.mkdir()
    raw.write_text(",".join(FIELDS) + "\n")
    with pytest.raises(ValueError, match="No participant responses"):
        analyze(raw, tmp_path / "logs", tmp_path / "analysis")
    assert not (tmp_path / "analysis").exists()


def test_full_analysis_joins_logs_and_preserves_raw(tmp_path):
    from reachy_lab2.trial import ROOT, load_json
    stimuli = {q["id"]:q["sha256"] for q in load_json(ROOT/"config/questions.json")["questions"]}
    raw = tmp_path / "raw" / "responses.csv"
    raw.parent.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    rows = []
    for condition, value in [("A", "3"), ("B", "5")]:
        row = dict.fromkeys(FIELDS, "")
        row.update(participant_id="P01", condition=condition, order="AB", session_id="SYNTHETIC-TEST-"+condition,
                   survey_version="SYNTHETIC SOFTWARE FIXTURE ONLY", observer_coverage="complete" if condition == "A" else "missing",
                   include="1", expression_check="4", study_version="expressive-performance-v2", **dict.fromkeys(ITEMS, value))
        rows.append(row)
        for i in range(1, 7):
            end = dict(marker="TRIAL_END", session_id=row["session_id"], technically_valid=True,
                       participant_id="P01", condition=condition, condition_order="AB",
                       condition_position="AB".index(condition)+1, input_mode="operator-mediated",
                       trial_sequence=i, question_id=f"q{i}", repeat_prompt_count=1,
                       study_version="expressive-performance-v2", choreography_reviewed=True,
                       expressive_motion=int(condition=="B"), answer_sha256=stimuli[f"q{i}"])
            (logs / f"{condition}{i}.jsonl").write_text(json.dumps(end)+"\n")
    with raw.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    original = raw.read_bytes()
    ready = analyze(raw, logs, tmp_path / "analysis")
    assert raw.read_bytes() == original
    assert ready[0]["agency"] == 3 and ready[1]["agency"] == 5
    assert ready[0]["soc_1"] == 3 and "qualitative_response" in ready[0]
    assert ready[0]["repeat_prompt_count"] == 6 and ready[1]["repeat_prompt_count"] is None
    assert (tmp_path / "analysis" / "paired_hries.png").stat().st_size > 1000
    with (tmp_path / "analysis" / "paired_differences.csv").open() as f:
        pairs = list(csv.DictReader(f))
    assert next(r for r in pairs if r["measure"] == "agency")["B_minus_A"] == "2"
    assert next(r for r in pairs if r["measure"] == "repeat_prompt_count")["B_minus_A"] == ""
    tampered=logs/"B1.jsonl"
    record=json.loads(tampered.read_text()); record["answer_sha256"]="different stimulus"
    tampered.write_text(json.dumps(record)+"\n")
    with pytest.raises(ValueError,match="six valid matching"):
        analyze(raw,logs,tmp_path/"tampered-analysis")
