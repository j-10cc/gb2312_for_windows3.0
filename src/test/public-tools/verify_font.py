"""Check the CHCGA disk font layout and 8086 seek arithmetic."""

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

from build_font import HEADER, SLOT_COUNT, big5_slot


def verify(path: Path) -> None:
    data = path.read_bytes()
    magic, version, width, height, ascii_width, slots, record_bytes, ascii_at, dbcs_at, valid = HEADER.unpack_from(data)
    assert magic == f"CH{height:02d}".encode("ascii") and version == 1
    assert (width, height, ascii_width) in ((14, 14, 7), (12, 10, 6), (10, 8, 5))
    assert (slots, record_bytes, ascii_at, dbcs_at) == (
        SLOT_COUNT, height * 2, HEADER.size, HEADER.size + 128 * height
    )
    assert len(data) == dbcs_at + slots * record_bytes
    assert 0 < valid <= slots
    assert big5_slot(0x81, 0x40) == 0
    assert big5_slot(0x81, 0x7E) == 62
    assert big5_slot(0x81, 0xA1) == 63
    assert big5_slot(0xFE, 0xFE) == slots - 1
    assert big5_slot(0x81, 0x7F) is None
    assert any(data[ascii_at + ord("A") * height : ascii_at + (ord("A") + 1) * height])

    # Mirror the 8086 driver's 16-bit MUL plus ADD/ADC across every 64 KiB crossing.
    for slot in range(slots):
        product = slot * record_bytes
        low = product & 0xFFFF
        high = product >> 16
        summed = low + dbcs_at
        dos_offset = ((high + (summed >> 16)) << 16) | (summed & 0xFFFF)
        assert dos_offset == dbcs_at + slot * record_bytes

    # These include the DOS sample and File Manager menu glyphs.
    samples = (
        (0xC1, 0x63), (0xC5, 0xE9), (0xA4, 0xA4), (0xA4, 0xE5),
        (0xC5, 0xE3), (0xA5, 0xDC), (0xB4, 0xFA), (0xB8, 0xD5),
        (0xC0, 0xC9), (0xAE, 0xD7), (0xBA, 0xDE), (0xB2, 0x7A), (0xAD, 0xFB),
    )
    for lead, trail in samples:
        slot = big5_slot(lead, trail)
        assert slot is not None
        offset = dbcs_at + slot * record_bytes
        assert any(data[offset : offset + record_bytes]), f"empty glyph at {lead:02X}{trail:02X}"
        assert offset <= 0xFFFFFFFF  # DOS INT 21h / 42h uses CX:DX.
    for char in "輔助檔案管理員":
        pair = char.encode("cp950")
        slot = big5_slot(*pair)
        assert slot is not None
        offset = dbcs_at + slot * record_bytes
        assert any(data[offset : offset + record_bytes]), f"empty glyph: {char}"
    # All Big5 level-one Hanzi must survive compression without blank images
    # or collisions. This is especially important in the 8-pixel icon bank.
    level_one = []
    for lead in range(0xA4, 0xC7):
        for trail in (*range(0x40, 0x7F), *range(0xA1, 0xFF)):
            code = lead << 8 | trail
            if not 0xA440 <= code <= 0xC67E:
                continue
            try:
                char = bytes((lead, trail)).decode("cp950")
            except UnicodeDecodeError:
                continue
            if len(char) != 1:
                continue
            slot = big5_slot(lead, trail)
            offset = dbcs_at + slot * record_bytes
            glyph = data[offset : offset + record_bytes]
            assert any(glyph), f"empty level-one glyph: {code:04X}"
            level_one.append(glyph)
    assert len(level_one) == 5401
    assert len(set(level_one)) == len(level_one), "level-one glyph collision"
    print(f"OK: {path}, {valid} mapped codes, {len(level_one)} distinct level-one Hanzi, {len(data)} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    verify(parser.parse_args().font)
