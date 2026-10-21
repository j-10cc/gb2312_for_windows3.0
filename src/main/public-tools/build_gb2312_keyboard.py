"""Build a CP936 byte-preserving Windows 3.0 keyboard driver test copy.

The stock US KEYBOARD.DRV maps ANSI high bytes to CP437 before KERNEL file
calls and maps directory entries back.  GB2312 8.3 names require both tables
to preserve byte values.  This tool works only on the validated 3.0a US media.
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


import argparse
import hashlib
import struct
from pathlib import Path

ROOT = _LAYOUT_ROOT
SOURCE = ROOT / "src/test/native-gb2312/work/build/expanded/english/KEYBOARD.DRV"
TARGET = ROOT / "src/test/native-gb2312/work/build/GB2312-APP/GBKBD.DRV"
ANSI_MARKER = bytes.fromhex("20 ad 9b 9c 0f 9d dd 15")
OEM_MARKER = bytes.fromhex("c7 fc e9 e2 e4 e0 e5 e7")
STOCK_SHA256 = "2554384b3da7f9925e56d9b0063e240d65c619cb2089819e4eaf3964e3eb769f"


def build(source: Path, target: Path) -> None:
    data = bytearray(source.read_bytes())
    if hashlib.sha256(data).hexdigest() != STOCK_SHA256:
        raise ValueError("Unknown Windows 3.0a US KEYBOARD.DRV image")
    if data.count(ANSI_MARKER) != 1 or data.count(OEM_MARKER) != 1:
        raise ValueError("Unknown Windows 3.0 US keyboard translation table")
    ansi = data.index(ANSI_MARKER)
    oem = data.index(OEM_MARKER)
    if oem != ansi + 128 or data[ansi - 2:ansi] != struct.pack("<H", 437):
        raise ValueError("Unexpected CP437 keyboard table layout")
    data[ansi - 2:ansi] = struct.pack("<H", 936)
    data[ansi:ansi + 96] = bytes(range(0xA0, 0x100))
    data[oem:oem + 128] = bytes(range(0x80, 0x100))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    args = parser.parse_args()
    build(args.source, args.target)
