"""Show large exact matches between two Windows NE code segments."""

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
import difflib
import struct
from pathlib import Path


def segment(path: Path, number: int) -> bytes:
    data = path.read_bytes()
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    table = ne + struct.unpack_from("<H", data, ne + 0x22)[0]
    shift = struct.unpack_from("<H", data, ne + 0x32)[0]
    sector, length = struct.unpack_from("<HH", data, table + 8 * (number - 1))
    at = sector << shift
    return data[at : at + (length or 65536)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--segment", type=int, default=1)
    args = parser.parse_args()
    first = segment(args.first, args.segment)
    second = segment(args.second, args.segment)
    chunks_a = [first[i : i + 8] for i in range(0, len(first), 8)]
    chunks_b = [second[i : i + 8] for i in range(0, len(second), 8)]
    matcher = difflib.SequenceMatcher(None, chunks_a, chunks_b)
    print(f"Lengths: {len(first)}, {len(second)}")
    for a, b, count in matcher.get_matching_blocks():
        if count >= 4:
            print(f"{a * 8:04X} -> {b * 8:04X}, {count * 8} bytes")
