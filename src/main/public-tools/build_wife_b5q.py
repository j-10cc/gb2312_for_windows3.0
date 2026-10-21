"""Resize the user's 16-pixel WIFE Big5 bitmap package to a 14-pixel test package.

The output derives from proprietary installation media and must stay local.
The container layout is inferred from the 16- and 20-pixel files; successful
parsing by CFFONT.FOD has not yet been verified in Windows.
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
import math
import struct
from pathlib import Path


HEADER_SIZE = 0x120
HALF_GLYPHS = 128
FULL_GLYPHS = 13737


def resize_glyph(data: bytes, width: int, height: int, new_width: int, new_height: int) -> bytes:
    source_pitch = (width + 7) // 8
    if len(data) != source_pitch * height:
        raise ValueError("unexpected glyph byte count")
    new_pitch = (new_width + 7) // 8
    result = bytearray()
    for y in range(new_height):
        top = y * height // new_height
        bottom = math.ceil((y + 1) * height / new_height)
        row = [1] * (new_pitch * 8)
        for x in range(new_width):
            left = x * width // new_width
            right = math.ceil((x + 1) * width / new_width)
            if any(not (data[sy * source_pitch + sx // 8] & (0x80 >> (sx & 7)))
                   for sy in range(top, bottom) for sx in range(left, right)):
                row[x] = 0
        for byte_at in range(new_pitch):
            result.append(sum(row[byte_at * 8 + bit] << (7 - bit) for bit in range(8)))
    return bytes(result)


def convert(source: bytes) -> bytes:
    if source[:8] != b"BIG5-FQ\0" or len(source) < HEADER_SIZE:
        raise ValueError("input is not a WIFE BIG5-FQ bitmap package")
    half_start, full_start = struct.unpack_from("<II", source, 0x110)
    half_stride, full_stride = struct.unpack_from("<HH", source, 0x11C)
    if (half_start, full_start, half_stride, full_stride) != (0x120, 0x920, 16, 32):
        raise ValueError("expected the original 16-pixel CFSUNG16.B5Q layout")
    if len(source) != full_start + FULL_GLYPHS * full_stride:
        raise ValueError("unexpected fullwidth glyph count")

    result = bytearray(source[:HEADER_SIZE])
    for offset in (0x9E, 0xA0, 0xA2, 0xB0, 0xB4):
        struct.pack_into("<H", result, offset, 14)
    for offset in (0xAE, 0xF8):
        struct.pack_into("<H", result, offset, 7)
    new_full_start = HEADER_SIZE + HALF_GLYPHS * 14
    struct.pack_into("<II", result, 0x110, HEADER_SIZE, new_full_start)
    struct.pack_into("<HH", result, 0x11C, 14, 28)
    for i in range(HALF_GLYPHS):
        glyph = source[half_start + i * half_stride : half_start + (i + 1) * half_stride]
        result.extend(resize_glyph(glyph, 8, 16, 7, 14))
    for i in range(FULL_GLYPHS):
        glyph = source[full_start + i * full_stride : full_start + (i + 1) * full_stride]
        result.extend(resize_glyph(glyph, 16, 16, 14, 14))
    if len(result) != new_full_start + FULL_GLYPHS * 28:
        raise AssertionError("output size mismatch")
    return bytes(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_b5q", type=Path)
    parser.add_argument("output_b5q", type=Path)
    args = parser.parse_args()
    if args.original_b5q.resolve() == args.output_b5q.resolve():
        raise ValueError("output must differ from source")
    result = convert(args.original_b5q.read_bytes())
    args.output_b5q.parent.mkdir(parents=True, exist_ok=True)
    args.output_b5q.write_bytes(result)
    print(f"Created {args.output_b5q}: {len(result)} bytes, {HALF_GLYPHS} halfwidth and {FULL_GLYPHS} fullwidth glyphs")


if __name__ == "__main__":
    main()
