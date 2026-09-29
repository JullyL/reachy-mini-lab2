import hashlib
import json

import numpy as np
import pytest

from reachy_lab2.choreography import EmotionLibrary, compile_performance, vector
from reachy_lab2.emotion_player import transition_duration
from reachy_lab2.motion import rotation
from reachy_lab2.trial import ROOT, load_json


def test_all_answers_have_distinct_expressive_speech_and_neutral_endpoints():
    config = load_json(ROOT/"config/conditions.json")
    for q in load_json(ROOT/"config/questions.json")["questions"]:
        a = compile_performance(q,{**config,"selected_condition":"A"})
        b = compile_performance(q,{**config,"selected_condition":"B"})
        av = np.array([vector(f) for f in a["set_target_data"]])
        bv = np.array([vector(f) for f in b["set_target_data"]])
        np.testing.assert_allclose(av[[0,-1]],0,atol=1e-8)
        np.testing.assert_allclose(bv[[0,-1]],0,atol=1e-8)
        assert np.max(np.abs(av[250:])) < 1e-8
        assert np.max(np.abs(bv[250:])) > .1
        assert np.max(np.abs(bv[100:240])) > .1
        assert a["sha256"] != b["sha256"]
        assert compile_performance(q,{**config,"selected_condition":"B"})["sha256"] == b["sha256"]
        assert np.max(np.linalg.norm(bv[:,:3],axis=1)) <= .008001
        assert np.max(np.linalg.norm(bv[:,3:6],axis=1)) <= np.deg2rad(22.001)
        assert np.max(np.abs(bv[:,6:])) <= .65001
        for f in b["set_target_data"]:
            assert np.linalg.det(np.array(f["head"])[:3,:3]) == pytest.approx(1)
        for cue in b["cues"][2:]:
            assert cue["phrase"] in q["answer"]


def test_stale_score_and_tampered_source_rejected(tmp_path):
    q = dict(load_json(ROOT/"config/questions.json")["questions"][0])
    q["sha256"] = "different recording"
    config=load_json(ROOT/"config/conditions.json")
    with pytest.raises(ValueError,match="matching"):
        compile_performance(q,{**config,"selected_condition":"B"})
    folder=tmp_path/"assets/motion/emotions"
    folder.mkdir(parents=True)
    (folder/"manifest.json").write_text(json.dumps({"motions":[{"id":"test","sha256":"wrong"}]}))
    (folder/"test.json").write_text("{}")
    with pytest.raises(ValueError,match="hash"):
        EmotionLibrary(tmp_path)


def test_emotions_transition_policy_depends_on_pose_distance():
    assert transition_duration(np.eye(4),[0,0]) == 0
    head=np.eye(4); head[:3,:3]=rotation(np.array([0,0,np.deg2rad(30)]))
    assert transition_duration(head,[0,0]) == pytest.approx(.6)
    head[0,3]=.1
    assert transition_duration(head,[0,0]) == 1.5


def test_emotional_speech_is_smooth_and_uses_aligned_source_sequences():
    cfg=load_json(ROOT/"config/conditions.json")
    scores=load_json(ROOT/"config/choreography.json")
    for q in load_json(ROOT/"config/questions.json")["questions"]:
        result=compile_performance(q,{**cfg,"selected_condition":"B"})
        values=np.array([vector(f) for f in result["set_target_data"][250:]])
        assert np.max(np.linalg.norm(values[:,3:6],axis=1)) > np.deg2rad(5)
        velocity=np.diff(values[:,3:6],axis=0)*50
        assert np.max(np.linalg.norm(velocity,axis=1)) <= np.deg2rad(65.01)
        assert np.max(np.linalg.norm(np.diff(velocity,axis=0),axis=1)*50) <= np.deg2rad(350.01)
        for cue,beat in zip(result["cues"][2:],scores["questions"][q["id"]]["beats"]):
            assert cue['source_motion'] == beat['motion']
            assert cue['accents']
        for cue in result["cues"][3:]:
            index=round((cue["start_s"]-5)*50)
            assert np.linalg.norm(values[index]) > 1e-4
        np.testing.assert_allclose(values[[0,-1]],0,atol=1e-8)


def test_genuine_captures_have_completed_events_and_matching_audio():
    for q in load_json(ROOT/"config/questions.json")["questions"]:
        receipt=load_json(ROOT/q["audio_metadata"])
        events=[json.loads(s) for s in (ROOT/q["audio_metadata"]).with_name("events.jsonl").read_text().splitlines()]
        assert receipt["response"]["status"] == "completed"
        assert any(e["type"]=="response.done" and e["response"]==receipt["response"] for e in events)
        assert receipt["answer"]==q["answer"]
        assert receipt["sha256"]==hashlib.sha256((ROOT/q["audio"]).read_bytes()).hexdigest()
