"""Build a disk-backed compact Big5 screen font for the CGA text prototype.

Input is a GNU Unifont .hex file. The output is an experimental driver data
file, not a Windows .FON resource. Runtime access needs only one 28-byte glyph.
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


MAGIC = b"CH14"
HEADER = struct.Struct("<4sBBBBHHIII")
CELL_WIDTH = 14
CELL_HEIGHT = 14
ASCII_WIDTH = 7
ASCII_COUNT = 128
LEAD_FIRST = 0x81
LEAD_LAST = 0xFE
TRAIL_COUNT = 157
SLOT_COUNT = (LEAD_LAST - LEAD_FIRST + 1) * TRAIL_COUNT
GLYPH_BYTES = CELL_HEIGHT * 2
ASCII_BYTES = ASCII_COUNT * CELL_HEIGHT


def trail_index(trail: int) -> int | None:
    if 0x40 <= trail <= 0x7E:
        return trail - 0x40
    if 0xA1 <= trail <= 0xFE:
        return 63 + trail - 0xA1
    return None


def big5_slot(lead: int, trail: int) -> int | None:
    ti = trail_index(trail)
    if not LEAD_FIRST <= lead <= LEAD_LAST or ti is None:
        return None
    return (lead - LEAD_FIRST) * TRAIL_COUNT + ti


def read_unifont(paths: list[Path]) -> dict[int, tuple[int, tuple[int, ...]]]:
    glyphs = {}
    for path in paths:
        for line in path.read_text(encoding="ascii").splitlines():
            if not line or ":" not in line:
                continue
            code, bitmap = line.split(":", 1)
            if len(bitmap) not in (32, 64):
                continue
            width = 8 if len(bitmap) == 32 else 16
            row_chars = width // 4
            rows = tuple(int(bitmap[i : i + row_chars], 16) for i in range(0, len(bitmap), row_chars))
            if len(rows) == 16:
                glyphs[int(code, 16)] = (width, rows)
    return glyphs


def scale_glyph(width: int, rows: tuple[int, ...], target_width: int,
                target_height: int = CELL_HEIGHT) -> tuple[int, ...]:
    """Area coverage downsample. Each output pixel receives majority coverage."""
    result = []
    for dy in range(target_height):
        row = 0
        y0, y1 = dy * 16, (dy + 1) * 16
        for dx in range(target_width):
            x0, x1 = dx * width, (dx + 1) * width
            ink = 0
            for sy in range(y0 // target_height, (y1 + target_height - 1) // target_height):
                if sy >= 16:
                    break
                overlap_y = min(y1, (sy + 1) * target_height) - max(y0, sy * target_height)
                for sx in range(x0 // target_width, (x1 + target_width - 1) // target_width):
                    if sx >= width:
                        break
                    overlap_x = min(x1, (sx + 1) * target_width) - max(x0, sx * target_width)
                    if rows[sy] & (1 << (width - 1 - sx)):
                        ink += overlap_x * overlap_y
            if ink * 2 >= 16 * width:
                row |= 1 << (target_width - 1 - dx)
        result.append(row)
    return tuple(result)


def pack_dbcs(rows: tuple[int, ...], target_width: int = CELL_WIDTH) -> bytes:
    shift = 2 if target_width == 14 else (16 - target_width) // 2
    return b"".join(struct.pack(">H", row << shift) for row in rows)


def pack_ascii(rows: tuple[int, ...]) -> bytes:
    return bytes(row << 1 for row in rows)


def build(sources: list[Path], destination: Path, cell_width: int = CELL_WIDTH,
          cell_height: int = CELL_HEIGHT, ascii_width: int = ASCII_WIDTH) -> tuple[int, int]:
    if not 1 <= ascii_width <= 8 or not 1 <= cell_width <= 16 or not 1 <= cell_height <= 16:
        raise ValueError("font dimensions outside 1..16 (ASCII width 1..8)")
    glyphs = read_unifont(sources)
    ascii_offset = HEADER.size
    ascii_bytes = ASCII_COUNT * cell_height
    glyph_bytes = cell_height * 2
    dbcs_offset = ascii_offset + ascii_bytes
    valid = 0
    missing = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as out:
        out.write(b"\0" * HEADER.size)
        for code in range(ASCII_COUNT):
            glyph = glyphs.get(code)
            out.write(pack_ascii(scale_glyph(*glyph, ascii_width, cell_height)) if glyph else bytes(cell_height))
        for lead in range(LEAD_FIRST, LEAD_LAST + 1):
            for trail in (*range(0x40, 0x7F), *range(0xA1, 0xFF)):
                try:
                    decoded = bytes((lead, trail)).decode("cp950")
                except UnicodeDecodeError:
                    decoded = ""
                glyph = glyphs.get(ord(decoded)) if len(decoded) == 1 else None
                if glyph is None:
                    out.write(bytes(glyph_bytes))
                    if decoded.isspace():
                        valid += 1  # U+3000 is intentionally an empty cell.
                    elif decoded:
                        missing += 1
                else:
                    out.write(pack_dbcs(scale_glyph(*glyph, cell_width, cell_height), cell_width))
                    valid += 1
        out.seek(0)
        magic = f"CH{cell_height:02d}".encode("ascii")
        out.write(HEADER.pack(magic, 1, cell_width, cell_height, ascii_width,
                              SLOT_COUNT, glyph_bytes, ascii_offset, dbcs_offset, valid))
    assert destination.stat().st_size == dbcs_offset + SLOT_COUNT * glyph_bytes
    return valid, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="CHCGAxx.FNT destination")
    parser.add_argument("sources", type=Path, nargs="+", help="GNU Unifont .hex sources, later files override earlier files")
    parser.add_argument("--cell-width", type=int, default=CELL_WIDTH)
    parser.add_argument("--cell-height", type=int, default=CELL_HEIGHT)
    parser.add_argument("--ascii-width", type=int, default=ASCII_WIDTH)
    args = parser.parse_args()
    valid, missing = build(args.sources, args.output, args.cell_width, args.cell_height, args.ascii_width)
    print(f"{args.output}: {valid} mapped Big5 codes (including full-width space); {missing} missing")


if __name__ == "__main__":
    main()
