import ast
import json
from types import SimpleNamespace

import numpy as np
import pytest

from reachy_lab2.greeting import compile_greeting, settings, require_physical_review
from reachy_lab2.robot import MockRobot
from reachy_lab2.trial import Controller, ROOT, run_trial, send_control
from reachy_lab2.conversation_audio import audio_to_float32, read_wav
from reachy_lab2.emotion_player import transition_duration
from reachy_lab2.__main__ import session_attempt
from reachy_lab2.analysis import rating, score, analyze
from reachy_lab2.audio import AudioOutput


def test_one_factor_and_complete_timeline():
    a, b = compile_greeting("A"), compile_greeting("B")
    assert settings()["parameter"] == "antenna_amplitude_deg"
    assert a["amplitude_deg"] == 10 and b["amplitude_deg"] == 30
    assert a["time"] == b["time"] == [i/50 for i in range(301)]
    aa = np.array([x["antennas"] for x in a["set_target_data"]])
    bb = np.array([x["antennas"] for x in b["set_target_data"]])
    np.testing.assert_allclose(bb, aa*3, atol=1e-15)
    np.testing.assert_allclose(aa.sum(axis=1), 0)
    np.testing.assert_allclose(np.rad2deg(aa[[0, 50, 100, 200, 250, 300]]),
                               [[0,0],[0,0],[-10,10],[10,-10],[0,0],[0,0]], atol=1e-12)
    assert np.all(aa[:51] == 0) and np.all(aa[250:] == 0)
    for frame in b["set_target_data"]:
        np.testing.assert_array_equal(frame["head"], np.eye(4))
        assert frame["body_yaw"] == 0
    # Same timing necessarily scales velocity and acceleration as well.
    np.testing.assert_allclose(np.diff(bb, n=2, axis=0), 3*np.diff(aa, n=2, axis=0), atol=1e-14)


def test_calibrated_neutral_and_commissioning():
    neutral = np.deg2rad([1,-1])
    g = compile_greeting("B", neutral=neutral, commissioning=True)
    assert g["amplitude_deg"] == 15
    np.testing.assert_allclose(g["set_target_data"][0]["antennas"], neutral)
    with pytest.raises(ValueError):
        require_physical_review()


def test_verified_upstream_conversion_equivalence():
    source = ast.parse((ROOT/"third_party/conversation/streaming.py").read_text())
    fn = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "audio_to_float32")
    fn.returns = None
    for arg in fn.args.args:
        arg.annotation = None
    ns = {"np":np}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "upstream", "exec"), ns)
    for values in [np.array([-32768,0,32767],dtype=np.int16), np.array([-.8,0,.9],dtype=np.float32)]:
        np.testing.assert_array_equal(audio_to_float32(values), ns["audio_to_float32"](values))
    with pytest.raises(TypeError):
        audio_to_float32(np.ones(2,dtype=np.float64))


def test_frozen_audio_and_emotions_transition():
    rate, samples = read_wav(ROOT/settings()["audio"])
    assert rate == 16000 and 1 < len(samples)/rate < 4
    assert transition_duration(np.eye(4), np.zeros(2)) == 0
    assert transition_duration(np.eye(4), np.deg2rad([60,0])) == pytest.approx(.3)


def test_device_clock_audio_onset(monkeypatch):
    monkeypatch.setattr("reachy_lab2.audio.time.perf_counter", lambda: 10)
    output = AudioOutput(1000, np.ones(30, dtype=np.float32))
    output.arm(10.05)
    block = np.empty((100,1), dtype=np.float32)
    output._callback(block,100,SimpleNamespace(outputBufferDacTime=5.02,currentTime=5),False)
    assert np.all(block[:30] == 0) and np.all(block[30:60] == 1)
    event = output.events.get()
    assert event[0] == "SPEECH_START" and event[1] == pytest.approx(10.05)


def test_order_and_one_replacement():
    with pytest.raises(ValueError):
        session_attempt([], "B", "AB", "")
    failed = {"condition":"A","completion":0,"trial_id":"first"}
    assert session_attempt([failed],"A","AB","first") == (1,2)
    with pytest.raises(ValueError):
        session_attempt([failed,failed],"A","AB","first")
    completed = {**failed,"completion":1}
    with pytest.raises(ValueError):
        session_attempt([completed],"A","AB","")
    assert session_attempt([completed],"B","AB","") == (2,1)


def test_scores_missingness_and_separate_outcomes(tmp_path):
    row = {f"soc_{i}":str(i+1) for i in range(1,5)} | {"valence":"6","arousal":"2","movement_size":"1"}
    s = score(row)
    assert s["sociability"] == 3.5 and s["animacy"] is None
    assert s["valence"] == 6 and s["arousal"] == 2
    assert "overall" not in s
    for v in ["0","8","2.5"]:
        with pytest.raises(ValueError): rating(v)
    with pytest.raises(ValueError, match="No participant"):
        analyze(ROOT/"study/data/raw/responses.csv",tmp_path,tmp_path/"out")


@pytest.mark.parametrize("condition,stop", [("A",None),("B",None),("A",.2),("B",1.5),("B",5.3)])
def test_trials_and_stops(tmp_path,condition,stop):
    with Controller() as control:
        path,status=run_trial(MockRobot(),control,condition,tmp_path,silent=True,stop_after=stop)
    rows=[json.loads(s) for s in path.read_text().splitlines()]
    end=rows[-1]
    assert status == ("completed" if stop is None else "interrupted")
    assert end["neutral_recovery_succeeded"] and not end["study_eligible"]
    assert not end["technically_valid"]
    if stop is None:
        assert end["measured_movement"]["verified"] and end["timing_ok"]
        assert end["measured_movement"]["achieved_poll_hz"] >= 20
        assert any(r["marker"] == "POST_HOLD_START" for r in rows)


def test_tcp_stop_and_exclusive_controller():
    with Controller() as control:
        with pytest.raises(RuntimeError,match="Another trial"):
            with Controller(): pass
        assert send_control("stop") == "recorded"
        assert control.stop.wait(1)


def test_stuck_feedback_fails_not_false_success(tmp_path):
    class Stuck(MockRobot):
        def send(self,frame): pass
    with Controller() as control:
        path,status=run_trial(Stuck(),control,"B",tmp_path,silent=True)
    end=json.loads(path.read_text().splitlines()[-1])
    assert status == "failed" and not end["measured_movement"]["verified"]


def test_disconnect_and_failed_recovery_retained(tmp_path):
    class Broken(MockRobot):
        def send(self,frame): raise ConnectionError("test disconnect")
        def neutral(self,stop=None):
            if getattr(self,"initialized",False): raise ConnectionError("test recovery failure")
            self.initialized=True
            return super().neutral(stop)
    with Controller() as control:
        path,status=run_trial(Broken(),control,"A",tmp_path,silent=True)
    end=json.loads(path.read_text().splitlines()[-1])
    assert status == "failed" and not end["neutral_recovery_succeeded"]
    assert "ConnectionError" in end["error"]


def test_analysis_preserves_failed_attempts_and_pairs(tmp_path):
    import csv
    from reachy_lab2.analysis import FIELDS
    logs=tmp_path/'logs'; logs.mkdir()
    records=[]
    for condition,tid,complete,attempt in [('A','a0',0,1),('A','a1',1,2),('B','b1',1,1)]:
        r={'marker':'TRIAL_END','study_version':'antenna-greeting-v1','trial_id':tid,'participant_id':'P01',
           'condition':condition,'condition_order':'AB','condition_position':1 if condition=='A' else 2,
           'robot_backend':'physical','completion':complete,'completion_status':'completed' if complete else 'failed',
           'error':None if complete else 'fixture fault','study_eligible':bool(complete),
           'wall_time_utc':f'2026-01-01T00:00:0{attempt}+00:00',
           'repeat_of':'a0' if tid=='a1' else '',
           'configuration_sha256':'fixture','audio_sha256':'fixture','calibration_sha256':'fixture','software_sha256':'fixture'}
        (logs/(tid+'.jsonl')).write_text(json.dumps(r)+'\n')
    for condition,tid,value in [('A','a1','3'),('B','b1','5')]:
        row={k:'' for k in FIELDS}
        row.update(participant_id='P01',condition=condition,order='AB',trial_id=tid,study_version='antenna-greeting-v1',survey_version='HRIES-greeting-v1',include='1',valence='4',arousal='2',movement_size='1')
        row.update({f'soc_{i}':value for i in range(1,5)})
        records.append(row)
    raw=tmp_path/'raw';raw.mkdir();file=raw/'responses.csv'
    with file.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(records)
    out=tmp_path/'out'
    ready=analyze(file,logs,out)
    assert ready[0]['sociability']==3 and ready[0]['prior_exposure']
    pairs=list(csv.DictReader((out/'paired_differences.csv').open()))
    assert next(r for r in pairs if r['measure']=='sociability')['B_minus_A']=='2'
    attempt_rows=list(csv.DictReader((out/'attempt_outcomes.csv').open()))
    assert len(attempt_rows)==3 and sum(r['completion']=='0' for r in attempt_rows)==1
    assert (out/'paired_hries.png').exists()
