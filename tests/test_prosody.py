import hashlib
import json
import wave

import numpy as np
import pytest

from reachy_lab2.choreography import ROOT, EmotionLibrary, speech_performance
from reachy_lab2.prosody import align_audio, align_beats, load_alignment


def fixtures():
    questions = json.loads((ROOT/'config/questions.json').read_text())['questions']
    score = json.loads((ROOT/'config/choreography.json').read_text())
    return questions, score


def test_every_frozen_answer_has_complete_hash_bound_phone_timing():
    questions, score = fixtures()
    for q in questions:
        selection = score['questions'][q['id']]
        path = ROOT/selection['alignment']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == selection['alignment_sha256']
        timing = load_alignment(path, ROOT/q['audio'], q['answer'])
        assert timing['reviewed'] is False
        assert all(w['phones'] for w in timing['words'])
        assert sum(len(w['syllables']) for w in timing['words']) > len(timing['words'])
        assert timing['words'][-1]['end_s'] > q['duration_s']-.3
        beats = align_beats(selection['beats'], timing)
        for beat in beats:
            assert beat['start_s'] == timing['words'][beat['word_index']]['start_s']
            assert all(beat['start_s'] <= a['at_s'] <= beat['end_s'] for a in beat['accents'])


def test_timing_uses_audio_words_instead_of_percentages_and_rejects_stale_text(tmp_path):
    questions,score = fixtures()
    q=questions[0]; selection=score['questions']['q1']
    timing=load_alignment(ROOT/selection['alignment'],ROOT/q['audio'],q['answer'])
    wrong_fractions=[{**b,'at':0} for b in selection['beats']]
    assert align_beats(wrong_fractions,timing)[1]['start_s'] == pytest.approx(2.05,abs=.01)
    with pytest.raises(ValueError,match='Stale'):
        load_alignment(ROOT/selection['alignment'],ROOT/q['audio'],q['answer']+' Changed')
    bad=json.loads(json.dumps(timing));bad['words'][0]['end_s']=-1
    path=tmp_path/'alignment.json';path.write_text(json.dumps(bad))
    with pytest.raises(ValueError,match='times'):
        load_alignment(path,ROOT/q['audio'],q['answer'])
    with pytest.raises(ValueError,match='exact aligned match'):
        align_beats([{'phrase':'not in the recording','state':'happy'}],timing)


def test_real_phone_alignment_follows_audio_shift(tmp_path):
    q=fixtures()[0][0]
    with wave.open(str(ROOT/q['audio']),'rb') as source:
        params=source.getparams();pcm=source.readframes(source.getnframes())
    shifted=tmp_path/'shifted.wav'
    with wave.open(str(shifted),'wb') as target:
        target.setparams(params);target.writeframes(bytes(16000*2//2)+pcm)
    timing=align_audio(shifted,q['answer'])
    original=json.loads((ROOT/'assets/conversation/q1/alignment.json').read_text())
    shifts=[a['start_s']-b['start_s'] for a,b in zip(timing['words'][2:],original['words'][2:])]
    assert np.median(shifts) == pytest.approx(.5,abs=.04)
    assert max(abs(s-.5) for s in shifts) < .12


def test_source_emotions_and_syllable_accents_both_affect_performance():
    questions,score=fixtures();q=questions[0]
    timing=load_alignment(ROOT/score['questions']['q1']['alignment'],ROOT/q['audio'],q['answer'])
    beats=align_beats(score['questions']['q1']['beats'],timing)
    library=EmotionLibrary()
    original=speech_performance(library,beats,q['duration_s'],alignment=timing)
    changed=[{**b,'motion':'surprised1'} for b in beats]
    alternate=speech_performance(library,changed,q['duration_s'],alignment=timing)
    assert np.max(np.abs(original[:,:6]-alternate[:,:6])) > .05
    no_accents=speech_performance(library,beats,q['duration_s'],
        {'head_accent_deg':0,'antenna_accent_rad':0},timing)
    assert np.max(np.abs(original[:,6:]-no_accents[:,6:])) > .005
    with pytest.raises(ValueError,match='alignment'):
        speech_performance(library,beats,q['duration_s'])
