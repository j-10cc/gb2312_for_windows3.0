"""Verify the rebuilt CGA baseline against the supplied Windows media."""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import argparse
import hashlib
import struct
from pathlib import Path

from inspect_ne import entries, names, u16


def read_ne(path: Path):
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"{path}: MZ signature missing")
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if data[ne : ne + 2] != b"NE":
        raise ValueError(f"{path}: NE signature missing")
    reference_table = ne + u16(data, ne + 0x28)
    import_table = ne + u16(data, ne + 0x2A)
    imports = []
    for index in range(u16(data, ne + 0x1E)):
        offset = u16(data, reference_table + 2 * index)
        at = import_table + offset
        imports.append(data[at + 1 : at + 1 + data[at]].decode("ascii"))
    table = ne + u16(data, ne + 0x22)
    shift = u16(data, ne + 0x32)
    segments = []
    for index in range(u16(data, ne + 0x1C)):
        sector, length, flags, _ = struct.unpack_from("<HHHH", data, table + 8 * index)
        at = sector << shift
        length = length or 65536
        segments.append((flags, data[at : at + length]))
    exports = dict(names(data, ne + u16(data, ne + 0x26)))
    return imports, segments, exports, entries(data, ne)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rebuilt", type=Path)
    parser.add_argument("english", type=Path)
    parser.add_argument("chinese", type=Path)
    args = parser.parse_args()

    built_imports, built_segments, built_exports, built_entries = read_ne(args.rebuilt)
    english_imports, english_segments, english_exports, english_entries = read_ne(args.english)
    chinese_imports, chinese_segments, chinese_exports, chinese_entries = read_ne(args.chinese)

    assert built_imports == english_imports == ["KEYBOARD", "KERNEL"]
    assert len(built_segments) == len(english_segments) == 8
    for index, (built, original) in enumerate(zip(built_segments, english_segments), 1):
        assert built == original, f"CGA segment {index} differs from supplied media"
    assert built_exports == english_exports
    assert built_entries == english_entries
    assert "WIFEMAN" in chinese_imports
    assert {11, 14, 15}.issubset(chinese_entries)

    print("PASS: rebuilt CGA has the same eight NE segments and export entries as the supplied English CGA.DRV")
    print("PASS: Chinese CHERC.DRV imports WIFEMAN and exports StrBlt, ExtTextOut, GetCharWidth")
    print("English CGA segment 1 SHA-256:", hashlib.sha256(built_segments[0][1]).hexdigest())
    print("Chinese CHERC segment 1 bytes:", len(chinese_segments[0][1]))


if __name__ == "__main__":
    main()
