"""Verify retained upstream files against the fetch-time provenance hashes."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for entry in json.loads((ROOT/'third_party/provenance.json').read_text())['files']:
    path=ROOT/entry['local_path']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise SystemExit(f'Source hash mismatch: {path}')
print('Verified three retained upstream source hashes.')
