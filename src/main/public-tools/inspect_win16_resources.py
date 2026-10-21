"""List string, dialog, and menu resources in an NE (Win16) module."""

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


TYPES = {1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU",
         5: "DIALOG", 6: "STRING", 7: "FONTDIR", 8: "FONT",
         9: "ACCEL", 10: "RCDATA", 11: "GROUP_CURSOR",
         12: "GROUP_ICON", 16: "VERSION"}


def word(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def resources(path: Path):
    data = path.read_bytes()
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if data[ne:ne + 2] != b"NE":
        raise ValueError(f"{path}: not an NE module")
    start = ne + word(data, ne + 0x24)
    at = start + 2
    shift = word(data, start)
    while type_id := word(data, at):
        count = word(data, at + 2)
        at += 8
        for _ in range(count):
            offset, length, flags, name, _, _ = struct.unpack_from(
                "<6H", data, at)
            at += 12
            if not type_id & 0x8000:
                continue
            number = name & 0x7FFF if name & 0x8000 else name
            payload = data[offset << shift:(offset + length) << shift]
            yield type_id & 0x7FFF, number, flags, payload


def strings(payload: bytes, block_id: int):
    at = 0
    for index in range(16):
        if at >= len(payload):
            break
        size = payload[at]
        at += 1
        if size:
            yield (block_id - 1) * 16 + index, payload[at:at + size].decode(
                "cp1252", "replace")
        at += size


def inspect(path: Path, detail: bool) -> None:
    found = list(resources(path))
    counts = {TYPES.get(kind, str(kind)): sum(k == kind for k, *_ in found)
              for kind, *_ in found}
    print(path, counts)
    if detail:
        for kind, number, _, payload in found:
            if kind == 6:
                for string_id, value in strings(payload, number):
                    print(f"  STRING {string_id}: {value}")
            elif kind in (4, 5):
                import re
                text = [part.decode("cp1252", "replace") for part
                        in re.findall(rb"[ -~]{3,}", payload)]
                print(f"  {TYPES[kind]} {number}: {text[:25]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--detail", action="store_true")
    args = parser.parse_args()
    for file in args.files:
        inspect(file, args.detail)
