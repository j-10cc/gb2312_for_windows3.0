"""Expand Windows 3.0 installation SZDD files without changing the originals."""

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
import struct
from pathlib import Path


SIGNATURE = b"SZDD\x88\xf0\x27\x33"


def expand(data: bytes) -> bytes:
    if not data.startswith(SIGNATURE) or data[8] != ord("A"):
        raise ValueError("not an SZDD mode A file")
    expected = struct.unpack_from("<I", data, 10)[0]
    window = bytearray(b" " * 4096)
    cursor = 0xFF0
    source = 14
    result = bytearray()
    while len(result) < expected:
        if source >= len(data):
            raise ValueError("truncated SZDD flags")
        flags = data[source]
        source += 1
        for bit in range(8):
            if len(result) == expected:
                break
            if flags & (1 << bit):
                if source >= len(data):
                    raise ValueError("truncated SZDD literal")
                values = (data[source],)
                source += 1
            else:
                if source + 1 >= len(data):
                    raise ValueError("truncated SZDD reference")
                low, high = data[source : source + 2]
                source += 2
                offset = low | ((high & 0xF0) << 4)
                length = (high & 0x0F) + 3
                values = (window[(offset + step) & 0xFFF] for step in range(length))
            for value in values:
                if len(result) == expected:
                    break
                result.append(value)
                window[cursor] = value
                cursor = (cursor + 1) & 0xFFF
    return bytes(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("sources", type=Path, nargs="+")
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    for path in args.sources:
        data = path.read_bytes()
        target = args.destination / path.name
        target.write_bytes(expand(data) if data.startswith(SIGNATURE) else data)
        print(f"{path.name}: {len(data)} -> {target.stat().st_size}")


if __name__ == "__main__":
    main()
