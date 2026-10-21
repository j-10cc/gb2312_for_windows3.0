"""Build matched 10- and 8-pixel Big5 screen fonts from OFL Unifont bitmaps.

The low-resolution conversion ranks pixels by source coverage and limits ink
density. This keeps thin strokes while avoiding solid blocks in complex Hanzi.
Both banks retain the v1 CHCGA layout used by the 8086 display driver.
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

from build_font import HEADER, SLOT_COUNT, big5_slot, pack_ascii, pack_dbcs, read_unifont, scale_glyph


ROOT = _LAYOUT_ROOT
SOURCES = [ROOT / "external/unifont/font/plane00/unifont-base.hex",
           ROOT / "external/unifont/font/plane00/wqy.hex"]
TRAILS = (*range(0x40, 0x7F), *range(0xA1, 0xFF))


def hint_glyph(width: int, rows: tuple[int, ...], target_width: int,
               target_height: int) -> tuple[int, ...]:
    """Retain the strongest source pixels under a small-screen ink budget."""
    area = width * 16
    source_ink = sum(row.bit_count() for row in rows)
    if not source_ink:
        return (0,) * target_height
    if target_height <= 8 and source_ink <= 65:
        # Sparse characters lose diagonals and enclosing boxes under area
        # ranking. Project their source strokes into the 8-pixel grid.
        projected = [0] * target_height
        for sy, row in enumerate(rows):
            for sx in range(width):
                if row & (1 << (width - 1 - sx)):
                    ty = min(target_height - 1, sy * target_height // 16)
                    tx = min(target_width - 1, sx * target_width // width)
                    projected[ty] |= 1 << (target_width - 1 - tx)
        return tuple(projected)
    pixels = []
    for y in range(target_height):
        for x in range(target_width):
            ink = 0
            y0, y1 = y * 16, (y + 1) * 16
            x0, x1 = x * width, (x + 1) * width
            for sy in range(y0 // target_height, (y1 + target_height - 1) // target_height):
                if sy >= 16:
                    break
                oy = min(y1, (sy + 1) * target_height) - max(y0, sy * target_height)
                for sx in range(x0 // target_width, (x1 + target_width - 1) // target_width):
                    if sx >= width:
                        break
                    ox = min(x1, (sx + 1) * target_width) - max(x0, sx * target_width)
                    if rows[sy] & (1 << (width - 1 - sx)):
                        ink += ox * oy
            # Prefer a dark center pixel when area coverage ties.
            center_y = min(15, (2 * y + 1) * 16 // (2 * target_height))
            center_x = min(width - 1, (2 * x + 1) * width // (2 * target_width))
            center = bool(rows[center_y] & (1 << (width - 1 - center_x)))
            pixels.append((ink, center, y, x))
    count = max(1, round(source_ink * target_width * target_height / area))
    count = min(count, round(target_width * target_height * 0.43))
    selected = sorted(pixels, reverse=True)[:count]
    result = [0] * target_height
    for ink, _, y, x in selected:
        if ink:
            result[y] |= 1 << (target_width - 1 - x)
    return tuple(result)


def build(path: Path, glyphs: dict[int, tuple[int, tuple[int, ...]]],
          width: int, height: int, ascii_width: int) -> dict[str, int]:
    ascii_at = HEADER.size
    dbcs_at = ascii_at + 128 * height
    records = bytearray()
    mapped = missing = common = common_missing = 0
    common_images: list[bytes] = []
    seen_common: set[bytes] = set()
    for lead in range(0x81, 0xFF):
        for trail in TRAILS:
            pair = bytes((lead, trail))
            try:
                char = pair.decode("cp950")
            except UnicodeDecodeError:
                char = ""
            glyph = glyphs.get(ord(char)) if len(char) == 1 else None
            if glyph:
                image = pack_dbcs(hint_glyph(*glyph, width, height), width)
                mapped += 1
            else:
                image = bytes(height * 2)
                if char.isspace():
                    mapped += 1
                elif char:
                    missing += 1
            if 0xA440 <= (lead << 8 | trail) <= 0xC67E and char:
                if image in seen_common and glyph:
                    alternative = pack_dbcs(scale_glyph(*glyph, width, height), width)
                    if alternative not in seen_common and any(alternative):
                        image = alternative
                    else:
                        # At 8 pixels, two distinct Hanzi can quantize to the
                        # same image. Preserve one distinguishing source stroke.
                        shift = (16 - width) // 2
                        for sy in range(16):
                            for sx in range(glyph[0]):
                                if not (glyph[1][sy] & (1 << (glyph[0] - 1 - sx))):
                                    continue
                                tx = min(width - 1, sx * width // glyph[0])
                                ty = min(height - 1, sy * height // 16)
                                candidate = bytearray(image)
                                row = int.from_bytes(candidate[ty * 2:ty * 2 + 2], "big")
                                row ^= 1 << (15 - shift - tx)
                                candidate[ty * 2:ty * 2 + 2] = row.to_bytes(2, "big")
                                if bytes(candidate) not in seen_common:
                                    image = bytes(candidate)
                                    break
                            else:
                                continue
                            break
                seen_common.add(image)
                common += 1
                common_images.append(image)
                if not any(image) and not char.isspace():
                    common_missing += 1
            records.extend(image)
    ascii_glyphs = bytearray()
    for code in range(128):
        glyph = glyphs.get(code)
        ascii_glyphs.extend(pack_ascii(hint_glyph(*glyph, ascii_width, height))
                            if glyph else bytes(height))
    header = HEADER.pack(f"CH{height:02d}".encode("ascii"), 1, width, height,
                         ascii_width, SLOT_COUNT, height * 2, ascii_at, dbcs_at, mapped)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + ascii_glyphs + records)
    assert len(records) == SLOT_COUNT * height * 2
    return {"mapped": mapped, "missing": missing, "level1": common,
            "level1_missing": common_missing,
            "level1_unique": len(set(common_images))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    glyphs = read_unifont(SOURCES)
    for width, height, ascii_width in ((12, 10, 6), (10, 8, 5)):
        target = args.output_dir / f"CHCGA{height:02d}.FNT"
        print(target, build(target, glyphs, width, height, ascii_width))


if __name__ == "__main__":
    main()
