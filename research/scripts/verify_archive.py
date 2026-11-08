"""Verify every file recorded in the root SHA256 manifest without dependencies."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'CONTENTS_SHA256.json').read_text())
failures=[]
for relative,expected in manifest['files'].items():
    path=ROOT/relative
    if not path.is_file():
        failures.append({'file':relative,'error':'missing'})
        continue
    with path.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=expected:
        failures.append({'file':relative,'error':'sha256 mismatch'})
print(json.dumps({'files_checked':len(manifest['files']),
                  'all_match':not failures,'failures':failures},indent=2))
if failures:raise SystemExit(1)
