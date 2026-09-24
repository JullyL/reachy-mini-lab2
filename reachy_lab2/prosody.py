"""Local, inspectable word/phone alignment of frozen speech, without changing audio."""
import hashlib
import importlib.metadata
import json
import re
import wave
from pathlib import Path

import numpy as np

VOWELS = set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split())
FUNCTION_WORDS = set("a an the as at by for from in into of on or so than that their then those to we when while with you your it its is are and be can does doesn't have they this".split())
TIMING_BASIS = ('PocketSphinx local forced word/phone alignment; vowel centers approximate syllable nuclei; '
                'acoustic prominence estimates emphasis, not verified linguistic stress; listening review required')


def tokens(text):
    text = text.lower().replace('\u2019', "'")
    # The only numeric expression in the frozen study transcripts.
    text = re.sub(r'\b340\b', 'three hundred forty', text)
    if re.search(r'\d', text):
        raise ValueError('Spell out numbers before forced alignment')
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text)


def align_audio(path, text):
    """Two-pass local alignment; unknown words fail explicitly rather than fake timing."""
    from pocketsphinx import Decoder

    path = Path(path)
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
            raise ValueError('Alignment requires mono PCM16 16000 Hz WAV')
        pcm = wav.readframes(wav.getnframes())
    samples = np.frombuffer(pcm, dtype='<i2').astype(float)/32768
    words = tokens(text)
    if not words:
        raise ValueError('Cannot align an empty transcript')
    decoder = Decoder(lm=None, samprate=16000, loglevel='ERROR', cmn='batch',
                      beam=1e-100, pbeam=1e-100, bestpath=False)
    # Explicit study vocabulary, retained in the timing receipt.
    overrides = {'micelles': 'M AY S EH L Z', "lightning's": 'L AY T N IH NG Z'}
    applied = {}
    for word in words:
        if decoder.lookup_word(word) is None:
            if word not in overrides:
                raise ValueError('Unknown alignment word: '+word)
            decoder.add_word(word, overrides[word], update=True)
            applied[word] = overrides[word]
    decoder.set_align_text(' '.join(words))
    for phone_pass in (False, True):
        if phone_pass:
            decoder.set_alignment()
        decoder.start_utt()
        decoder.process_raw(pcm, full_utt=True)
        decoder.end_utt()
    aligned = []
    for word in decoder.get_alignment():
        name = re.sub(r'\(\d+\)$', '', word.name)
        if name.startswith('<') or name.startswith('['):
            continue
        phones = []
        syllables = []
        for phone in word:
            begin, end = phone.start/100, (phone.start+phone.duration)/100
            phones.append({'phone': phone.name, 'start_s': begin, 'end_s': end})
            if phone.name.rstrip('012') in VOWELS and end > begin:
                chunk = samples[int(begin*16000):int(end*16000)]
                strength = float(np.sqrt(np.mean(chunk**2))) if len(chunk) else 0.0
                syllables.append({'at_s': round((begin+end)/2, 4), 'vowel': phone.name,
                                  'rms': round(strength, 6), 'duration_s': round(end-begin, 4)})
        aligned.append({'word': name, 'start_s': word.start/100,
                        'end_s': (word.start+word.duration)/100,
                        'phones': phones, 'syllables': syllables})
    if [w['word'] for w in aligned] != words:
        raise ValueError('Alignment did not cover the complete normalized transcript')
    if any(w['end_s'] <= w['start_s'] for w in aligned):
        raise ValueError('Alignment produced a zero-duration word; inspect the transcript')
    return {'schema_version': 1, 'engine': 'pocketsphinx',
            'engine_version': importlib.metadata.version('pocketsphinx'),
            'decoder_settings': {'cmn': 'batch', 'beam': 1e-100, 'pbeam': 1e-100, 'bestpath': False},
            'timing_basis': TIMING_BASIS, 'reviewed': False,
            'audio_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'answer_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'duration_s': len(samples)/16000, 'normalized_text': ' '.join(words),
            'dictionary_overrides': applied, 'words': aligned}


def load_alignment(path, audio_path, text):
    receipt = json.loads(Path(path).read_text())
    if (receipt['audio_sha256'] != hashlib.sha256(Path(audio_path).read_bytes()).hexdigest()
            or receipt['answer_text_sha256'] != hashlib.sha256(text.encode()).hexdigest()):
        raise ValueError('Stale speech alignment: regenerate for this exact audio and transcript')
    if [w['word'] for w in receipt['words']] != tokens(text):
        raise ValueError('Speech alignment transcript mismatch')
    previous = 0.0
    for word in receipt['words']:
        if not previous <= word['start_s'] < word['end_s'] <= receipt['duration_s']+.02:
            raise ValueError('Speech alignment word times are invalid')
        for syllable in word['syllables']:
            if not word['start_s'] <= syllable['at_s'] <= word['end_s']:
                raise ValueError('Syllable outside aligned word')
        previous = word['end_s']
    return receipt


def align_beats(beats, receipt):
    """Locate exact phrase anchors in aligned words; reject missing/ambiguous anchors."""
    words = receipt['words']
    names = [w['word'] for w in words]
    result = []
    for beat in beats:
        anchor = tokens(beat['phrase'])
        matches = [i for i in range(len(names)-len(anchor)+1) if names[i:i+len(anchor)] == anchor]
        if len(matches) != 1:
            raise ValueError('Speech phrase must have one exact aligned match: '+beat['phrase'])
        idx = matches[0]
        if result and idx <= result[-1]['word_index']:
            raise ValueError('Speech phrases must follow transcript order')
        result.append({**beat, 'word_index': idx, 'start_s': words[idx]['start_s']})
    if not result or result[0]['word_index'] != 0:
        raise ValueError('First emotional phrase must begin with the answer')
    for i, beat in enumerate(result):
        end_index = result[i+1]['word_index'] if i+1 < len(result) else len(words)
        segment = words[beat['word_index']:end_index]
        beat['end_s'] = segment[-1]['end_s']
        beat['at'] = beat['start_s']/receipt['duration_s']
        candidates = [(s['rms']*np.sqrt(min(s['duration_s'], .2)), s['at_s'], w['word'])
                      for w in segment if w['word'] not in FUNCTION_WORDS for s in w['syllables']]
        if not candidates:
            candidates = [(s['rms'], s['at_s'], w['word']) for w in segment for s in w['syllables']]
        selected = []
        for strength, at, word in sorted(candidates, reverse=True):
            if all(abs(at-c['at_s']) >= .85 for c in selected):
                selected.append({'at_s': at, 'word': word, 'kind': 'acoustic_prominence'})
            if len(selected) >= max(1, int((beat['end_s']-beat['start_s'])/1.4)):
                break
        # A light phrase-ending accent, unless a nearby prominent word already provides one.
        ending_words = [w for w in segment if w['word'] not in FUNCTION_WORDS] or segment
        ending = ending_words[-1]['syllables']
        if ending and all(abs(ending[-1]['at_s']-c['at_s']) >= .65 for c in selected):
            selected.append({'at_s': ending[-1]['at_s'], 'word': ending_words[-1]['word'], 'kind': 'phrase_ending'})
        beat['accents'] = sorted(selected, key=lambda c:c['at_s'])
    return result
