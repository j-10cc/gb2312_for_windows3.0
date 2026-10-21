"""Reproducible common-word import; build-host only, never shipped as code to DOS.

Use the intersection of Jieba frequency >= 5 and phrase-pinyin-data pinyin.txt.
Do not guess contextual readings from the Cartesian product of character readings.
"""

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]

from collections import Counter
import hashlib
from pathlib import Path

ROOT = _LAYOUT_ROOT
SOURCE = ROOT / 'external/pinyin-common'
PINS = {
    'jieba-dict.txt': '7197c3211ddd98962b036cdf40324d1ea2bfaa12bd028e68faa70111a88e12a8',
    'phrase-pinyin.txt': 'dcc769607c220b312fea3e71cb63421298b4b891b1f7356a95ab58f2c96fff81',
    'jieba-LICENSE': '18ba0984839f85853b29fadaf992f7dba8fd0ca0fbeae34de2b8735222dc7a37',
    'phrase-LICENSE': '89ac55df747e4776088c3e77531ef61b973a1a59dd8e6a4548a58996da9a4f70',
}
UPSTREAM = {
    'jieba': ('fxsjy/jieba', 'v0.42.1', '1e20c89b66f56c9301b0feed211733ffaa1bd72a',
              {'jieba-dict.txt': 'jieba/dict.txt', 'jieba-LICENSE': 'LICENSE'}),
    'phrase': ('mozillazg/phrase-pinyin-data', 'v0.19.0', 'cee0ed6e6e4898580cafd2bd5e3723e20b214aa0',
               {'phrase-pinyin.txt': 'pinyin.txt', 'phrase-LICENSE': 'LICENSE'}),
}


def common_phrases(table, normalize):
    for filename, digest in PINS.items():
        if hashlib.sha256((SOURCE / filename).read_bytes()).hexdigest() != digest:
            raise ValueError('Common phrase source checksum mismatch: ' + filename)
    frequencies = {parts[0]: int(parts[1])
                   for line in (SOURCE / 'jieba-dict.txt').read_text('utf-8').splitlines()
                   if len(parts := line.split()) == 3}
    counts = Counter()
    rows = []
    seen = set()
    for line in (SOURCE / 'phrase-pinyin.txt').read_text('utf-8').splitlines():
        if line.startswith('#') or ':' not in line:
            continue
        counts['source_readings'] += 1
        text, reading = line.split(':', 1)
        if frequencies.get(text, 0) < 5:
            counts['below_frequency_threshold'] += 1
            continue
        syllables = [normalize(s) for s in reading.split('#')[0].split()]
        if not 2 <= len(text) <= 8 or len(syllables) != len(text) or None in syllables:
            counts['unsupported_length_or_spelling'] += 1
            continue
        try:
            encoded = text.encode('gb2312')
        except UnicodeEncodeError:
            counts['outside_gb2312'] += 1
            continue
        if any(c.encode('gb2312') not in table.get(k, ()) for c, k in zip(text, syllables)):
            counts['reading_not_in_character_table'] += 1
            continue
        key = ''.join(syllables)
        if len(key) > 63:
            counts['unsupported_length_or_spelling'] += 1
            continue
        if (key, encoded) in seen:
            counts['duplicate_readings'] += 1
            continue
        seen.add((key, encoded))
        rows.append((key, encoded, frequencies[text]))
    # Same-key manual entries are added first by the caller. Among imported
    # homophones prefer corpus frequency, then GB2312 bytes for deterministic ties.
    rows.sort(key=lambda row: (row[0], -row[2], row[1]))
    counts['accepted_import_readings'] = len(rows)
    return [(key, text) for key, text, frequency in rows], dict(counts)


def provenance():
    manifest = {name: dict(repository='https://github.com/'+repo, tag=tag, revision=revision,
                          files={file: dict(upstream=path,sha256=PINS[file]) for file,path in files.items()})
                for name,(repo,tag,revision,files) in UPSTREAM.items()}
    return dict(minimum_frequency=5, sources=manifest, input_sha256=PINS)
