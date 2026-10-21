"""Patch local CompuFont 16/20-pixel hand-tuned banks by Big5 slot.

The result is derived from user-owned CFSUNG*.B5Q files and stays local.
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
from pathlib import Path
import struct

from build_font import read_unifont
from build_legible_fonts import SOURCES
from build_big5_simplified_fonts import DICTIONARY, read_mapping


FULL_GLYPHS = 13737
# The first 275 full-width images precede Big5 A140. For example, the
# original glyph for A4A4 (中) is at image 750, while its CP950 ordinal is 475.
# This offset is verified against several unmodified glyphs in both packages.
BIG5_PREFIX = 275
TRAILS = (*range(0x40, 0x7F), *range(0xA1, 0xFF))


def pairs() -> list[tuple[int, str]]:
    result = []
    for lead in range(0x81, 0xFF):
        for trail in TRAILS:
            code = lead << 8 | trail
            try:
                char = bytes((lead, trail)).decode("cp950")
            except UnicodeDecodeError:
                continue
            if len(char) == 1:
                result.append((code, char))
    if len(result) != FULL_GLYPHS + 15 or result[FULL_GLYPHS - 1][0] != 0xF9EF:
        raise ValueError("unexpected CP950 ordering for B5Q bank")
    return result[:FULL_GLYPHS]


def pack_glyph(glyph: tuple[int, tuple[int, ...]], size: int) -> bytes:
    width, rows = glyph
    stride = (size + 7) // 8
    result = bytearray()
    for y in range(size):
        source_y = y * 16 // size
        out = 0
        for x in range(size):
            source_x = x * width // size
            if rows[source_y] & (1 << (width - 1 - source_x)):
                out |= 1 << (stride * 8 - 1 - x)
        result.extend((~out & ((1 << (stride * 8)) - 1)).to_bytes(stride, "big"))
    return bytes(result)


def build(source: Path, target: Path, size: int) -> dict[str, int]:
    if source.resolve() == target.resolve():
        raise ValueError("refusing to overwrite the original B5Q bank")
    data = bytearray(source.read_bytes())
    if data[:8] != b"BIG5-FQ\0":
        raise ValueError("not a CompuFont bitmap package")
    half_at, full_at = struct.unpack_from("<II", data, 0x110)
    half_stride, full_stride = struct.unpack_from("<HH", data, 0x11C)
    geometry = {16: (0x120, 0x920, 16, 32),
                20: (0x120, 0x1520, 40, 60)}
    if ((half_at, full_at, half_stride, full_stride) != geometry[size]
            or len(data) != full_at + FULL_GLYPHS * full_stride):
        raise ValueError("unexpected B5Q geometry")
    mapping = read_mapping(DICTIONARY)
    glyphs = read_unifont(SOURCES)
    changed = missing = outside_bank = 0
    for index, (_, original) in enumerate(pairs()):
        choices = mapping.get(original, (original,))
        if choices[0] == original:
            continue
        image_index = index + BIG5_PREFIX
        if image_index >= FULL_GLYPHS:
            outside_bank += 1
            continue
        glyph = next((glyphs[ord(choice)] for choice in choices
                      if ord(choice) in glyphs), None)
        if glyph is None:
            missing += 1
            continue
        at = full_at + image_index * full_stride
        data[at:at + full_stride] = pack_glyph(glyph, size)
        changed += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"changed": changed, "missing": missing,
            "outside_bank": outside_bank, "size": len(data)}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_b5q", type=Path)
    p.add_argument("output_b5q", type=Path)
    p.add_argument("--size", type=int, choices=(16, 20), required=True)
    args = p.parse_args()
    print(build(args.original_b5q, args.output_b5q, args.size))
