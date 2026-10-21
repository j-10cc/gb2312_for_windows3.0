"""Build compact random-access GB2312 fonts for the mode-independent Win16 UI.

Only one glyph is read into conventional memory at a time. The same files are
usable with CGA or VGA and in all three Windows 3.0 modes.
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
import struct
from pathlib import Path

from build_font import read_unifont
from build_legible_fonts import SOURCES, hint_glyph


HEADER = struct.Struct("<4sHHII")
ROWS = 87
COLS = 94


def packed(glyph: tuple[int, tuple[int, ...]] | None, height: int,
           width: int) -> bytes:
    if glyph is None:
        return bytes(height * (2 if width > 8 else 1))
    source_width, rows = glyph
    if height == 16:
        if source_width > width:
            result = list(hint_glyph(source_width, rows, width, height))
        else:
            result = []
            for row in rows:
                if source_width == 8 and width == 16:
                    row <<= 4
                result.append(row)
    else:
        result = hint_glyph(source_width, rows, width, height)
        if width == 12:
            result = tuple(row << 2 for row in result)
    unit = 2 if width == 16 or width == 12 else 1
    return b"".join(row.to_bytes(unit, "big") for row in result)


def build(path: Path, height: int) -> tuple[int, int]:
    glyphs = read_unifont(SOURCES)
    ascii_at = HEADER.size
    dbcs_at = ascii_at + 128 * height
    record = 2 * height
    valid = missing = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as out:
        out.write(HEADER.pack(b"GBF1", height, record, ascii_at, dbcs_at))
        for code in range(128):
            out.write(packed(glyphs.get(code), height, 8))
        for row in range(ROWS):
            for col in range(COLS):
                pair = bytes((0xA1 + row, 0xA1 + col))
                try:
                    char = pair.decode("gb2312")
                except UnicodeDecodeError:
                    out.write(bytes(record))
                    continue
                valid += 1
                glyph = glyphs.get(ord(char))
                if glyph is None and not char.isspace():
                    missing += 1
                out.write(packed(glyph, height, 16 if height == 16 else 12))
    assert path.stat().st_size == dbcs_at + ROWS * COLS * record
    return valid, missing


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    for height in (10, 16):
        path = a.output / f"GB{height:02d}.FNT"
        valid, missing = build(path, height)
        print(f"{path}: {valid} GB2312 positions, {missing} missing glyphs")


if __name__ == "__main__":
    main()
