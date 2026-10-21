"""Build a compact GB2312 candidate table for the original PHON IME.

The four-byte phonetic keys are preserved. Candidate offsets are rebuilt in
two-byte character units, keeping one placeholder only for empty groups.
"""

from __future__ import annotations

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
import struct
from collections import Counter
from pathlib import Path

from patch_resources import SYMBOLS, simplify

from sys import path as python_path
ROOT = _LAYOUT_ROOT
python_path.insert(0, str(ROOT / "src/main/public-tools"))
from build_big5_simplified_fonts import DICTIONARY, read_mapping  # noqa: E402

BASE = ROOT / "src/test/native-gb2312/work/build/setup-test/C32/WINDOWS"
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/ime"


def main() -> None:
    code = (BASE / "PHONCODE.TBL").read_bytes()
    key = (BASE / "PHON.TBL").read_bytes()
    pointer = (BASE / "PHONPTR.TBL").read_bytes()
    if len(code) != 28140 or len(key) != 5248 or len(pointer) != 2624:
        raise ValueError("unexpected traditional PHON IME tables")
    offsets = struct.unpack(">" + str(len(pointer) // 2) + "H", pointer)
    if not (len(offsets) == len(key) // 4 == 1312
            and offsets[0] == 0 and offsets[-1] < len(code) // 2
            and all(x <= y for x, y in zip(offsets, offsets[1:]))):
        raise ValueError("PHON key/pointer relationship changed")
    mapping = read_mapping(DICTIONARY)
    output = bytearray()
    new_offsets = []
    fallbacks = Counter()
    removed_duplicates = 0
    empty_groups = 0
    placeholder = "？".encode("gb2312")
    for start, end in zip(offsets, (*offsets[1:], len(code) // 2)):
        new_offsets.append(len(output) // 2)
        seen = set()
        candidates = []
        for at in range(start, end):
            source = code[at * 2:at * 2 + 2]
            char = source.decode("cp950")
            converted, changes = simplify(source, mapping)
            if len(converted) != 2:
                raise ValueError("IME candidate no longer occupies two bytes")
            if changes and changes[0].endswith("->？") and char not in SYMBOLS:
                fallbacks[char] += 1
                continue
            if converted in seen:
                removed_duplicates += 1
                continue
            seen.add(converted)
            candidates.append(converted)
        if not candidates:
            candidates.append(placeholder)
            empty_groups += 1
        output.extend(b"".join(candidates))
    if len(output) // 2 > 65535:
        raise ValueError("PHON pointer table exceeded 16-bit range")
    rebuilt_pointer = struct.pack(">" + str(len(new_offsets)) + "H", *new_offsets)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "PHONCODE.TBL").write_bytes(output)
    (OUT / "PHON.TBL").write_bytes(key)
    (OUT / "PHONPTR.TBL").write_bytes(rebuilt_pointer)
    for name in ("IMEINFO.INI", "WIFERM.INI", "WIFEMAN.INI"):
        original = (BASE / name).read_bytes()
        converted, _ = simplify(original, mapping)
        (OUT / name).write_bytes(converted)
    assert len(new_offsets) == len(key) // 4
    assert new_offsets[0] == 0 and all(x < y for x, y in zip(new_offsets, new_offsets[1:]))
    assert all(bytes(output[at:at + 2]).decode("gb2312")
               for at in range(0, len(output), 2))
    report = {
        "source_sha256": hashlib.sha256(code).hexdigest(),
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "original_candidate_slots": len(code) // 2,
        "output_candidate_slots": len(output) // 2,
        "phonetic_keys": len(offsets),
        "unencodable_source_candidates_removed": sum(fallbacks.values()),
        "unencodable_source_characters": dict(fallbacks.most_common(40)),
        "duplicate_candidates_removed": removed_duplicates,
        "empty_groups_with_placeholder": empty_groups,
        "pointer_table_sha256": hashlib.sha256(rebuilt_pointer).hexdigest(),
        "key_table_unchanged": True,
    }
    (OUT / "IME-MANIFEST.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("unencodable_source_characters",)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
