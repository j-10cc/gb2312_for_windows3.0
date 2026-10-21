"""Explicit source download; normal IME builds remain offline and hash pinned."""

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]

import hashlib
import json
from urllib.request import urlopen
from pinyin_common import SOURCE, UPSTREAM, PINS, provenance


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    for repo, tag, revision, files in UPSTREAM.values():
        for file, path in files.items():
            target = SOURCE / file
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == PINS[file]:
                continue
            with urlopen(f'https://raw.githubusercontent.com/{repo}/{revision}/{path}', timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != PINS[file]:
                raise ValueError('Upstream source checksum mismatch: ' + file)
            temporary = target.with_suffix('.download')
            temporary.write_bytes(data)
            temporary.replace(target)
    (SOURCE / 'SOURCES.json').write_text(json.dumps(provenance(),indent=2)+'\n','utf-8')
    print(SOURCE)


if __name__ == '__main__': main()
