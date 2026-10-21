"""Apply the hash-bounded native font metrics and line repaint fixes."""
import hashlib
import json
from pathlib import Path

def apply(stage):
    entries=json.loads((Path(__file__).with_name('print-source-patch.json')).read_text())
    for entry in entries:
        path=stage/'CASHMERE'/entry['path'];data=path.read_bytes()
        digest=hashlib.sha256(data).hexdigest().upper()
        if digest==entry['after']:continue
        assert digest==entry['before'],f'unexpected source: {path}'
        for change in entry.get('replacements',[entry]):
            old=change['old'].encode('ascii');new=change['new'].encode('ascii')
            assert data.count(old)==1
            data=data.replace(old,new)
        assert hashlib.sha256(data).hexdigest().upper()==entry['after']
        path.write_bytes(data)
