"""Build GB2312 font banks for the Windows 3.0 real-mode CGA overlay.

The existing CGA driver indexes a 157-trail DBCS container. GB2312's
A1-FE trails are stored in those slots; every other slot is blank.
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

from build_font import HEADER, SLOT_COUNT, big5_slot, pack_dbcs, read_unifont, scale_glyph
from build_legible_fonts import SOURCES, hint_glyph


ROOT = _LAYOUT_ROOT


def build(destination: Path, height: int, width: int) -> tuple[int, int]:
    base = ROOT / "output" / f"CHCGA{height:02d}.FNT"
    data = bytearray(base.read_bytes())
    magic, version, _, actual_height, ascii_width, slots, record, ascii_at, dbcs_at, _ = HEADER.unpack_from(data)
    if (magic, version, actual_height, slots, record) != (
        f"CH{height:02d}".encode(), 1, height, SLOT_COUNT, height * 2
    ):
        raise ValueError(f"Unexpected font container: {base}")
    data[dbcs_at:] = bytes(len(data) - dbcs_at)
    glyphs = read_unifont(SOURCES)
    valid = missing = 0
    for lead in range(0xA1, 0xF8):
        for trail in range(0xA1, 0xFF):
            try:
                char = bytes((lead, trail)).decode("gb2312")
            except UnicodeDecodeError:
                continue
            if len(char) != 1:
                continue
            valid += 1
            glyph = glyphs.get(ord(char))
            if glyph is None:
                if not char.isspace():
                    missing += 1
                continue
            # At ten or more pixels the source has room for its strokes.
            # Ink-budget hinting can erase an entire radical (for example 理).
            rows = (scale_glyph(*glyph, width, height) if height >= 10
                    else hint_glyph(*glyph, width, height))
            image = pack_dbcs(rows, width)
            slot = big5_slot(lead, trail)
            if slot is None:
                raise AssertionError("GB2312 pair has no font slot")
            at = dbcs_at + slot * record
            data[at:at + record] = image
    HEADER.pack_into(data, 0, magic, version, width, height, ascii_width,
                     slots, record, ascii_at, dbcs_at, valid - missing)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return valid, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    for height, width in ((10, 12), (8, 10)):
        path = args.destination / f"CHCGA{height:02d}.FNT"
        valid, missing = build(path, height, width)
        print(f"{path}: {valid} valid GB2312 positions; {missing} missing non-space glyphs")


if __name__ == "__main__":
    main()
