"""Prepare inspectable local timing receipts for the unchanged frozen answer WAVs."""
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reachy_lab2.prosody import align_audio, align_beats


if __name__ == '__main__':
    questions = json.loads((ROOT/'config/questions.json').read_text())['questions']
    config_path = ROOT/'config/choreography.json'
    score = json.loads(config_path.read_text())
    prepared = []
    for q in questions:
        wav = ROOT/q['audio']
        receipt = align_audio(wav, q['answer'])
        destination = wav.with_name('alignment.json')
        raw = (json.dumps(receipt, indent=2)+'\n').encode()
        selection = score['questions'][q['id']]
        for beat, aligned in zip(selection['beats'], align_beats(selection['beats'],receipt)):
            beat['at'] = round(aligned['at'],6)
        selection.update(alignment=destination.relative_to(ROOT).as_posix(),
                         alignment_sha256=hashlib.sha256(raw).hexdigest(),reviewed=False)
        prepared.append((destination,raw))
        print(q['id'], len(receipt['words']), 'words;',
              sum(len(w['syllables']) for w in receipt['words']), 'vowel nuclei;', destination, flush=True)
    # Do not publish half-prepared timing when one answer fails alignment.
    for destination, raw in prepared:
        destination.write_bytes(raw)
    config_path.write_text(json.dumps(score,indent=2)+'\n')
