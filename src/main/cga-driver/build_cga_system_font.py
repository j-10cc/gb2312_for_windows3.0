"""Build a 12-pixel CGA system FON inside an existing Windows 3.0 FON container.

The English DDK EGA system bitmap has a 12-pixel cell. The source FON from
the Chinese media has a larger resource allocation, so replacing its FONT and
FONTDIR payloads in place preserves NE offsets while changing GDI metrics.
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


import struct
from pathlib import Path

from patch_resources import resources

HERE = Path(__file__).resolve().parent
ROOT = _LAYOUT_ROOT
CONTAINER = ROOT / "src/test/native-gb2312/work/build/expanded/chinese/EGASYS.FON"
FNT = ROOT / "external/win30ddk/fonts/system/ega/egasys.fnt"
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/fonts/CGAS12.FON"


def gb2312_metrics(font: bytes) -> bytes:
    """Match the overlay's 8-pixel advance for each GB2312 source byte.

    GDI measures captions using this proportional FNT, before the display
    overlay sees them. Keeping the English high-byte widths can make a
    Chinese caption's clip narrower than its actual 16-pixel cells. ASCII
    widths, character bitmap offsets and the bitmap bank remain untouched.
    """
    if (font[:2] != b'\x00\x02' or struct.unpack_from('<H', font, 86)[0] != 0
            or font[95] > 0xA1 or font[96] < 0xFE):
        raise ValueError('expected a proportional FNT covering GB2312 bytes')
    result = bytearray(font)
    for code in range(0xA1, 0xFF):
        struct.pack_into('<H', result, 118 + 4 * (code - font[95]), 8)
    return bytes(result)


def main() -> None:
    data = bytearray(CONTAINER.read_bytes())
    font = gb2312_metrics(FNT.read_bytes())
    entries = {entry.kind: entry for entry in resources(data)
               if entry.kind in (7, 8)}
    if set(entries) != {7, 8}:
        raise ValueError("expected one FONTDIR and FONT resource")
    directory, bitmap = entries[7], entries[8]
    if (directory.length != 128 or bitmap.length != 5472
            or data[bitmap.offset:bitmap.offset + 2] != b"\x00\x02"):
        raise ValueError("unexpected source FON layout")
    if (font[:2] != b"\x00\x02" or struct.unpack_from("<H", font, 88)[0] != 12
            or len(font) > bitmap.length or
            struct.unpack_from("<I", font, 2)[0] > len(font)):
        raise ValueError("unexpected DDK 12-pixel FNT")
    data[bitmap.offset:bitmap.offset + bitmap.length] = (
        font + bytes(bitmap.length - len(font)))
    # FONTDIR stores the FNT header through dfBitsPointer and then the face
    # name. Its final 11 bytes already contain "System" and padding.
    data[directory.offset + 4:directory.offset + 117] = font[:113]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    check = OUT.read_bytes()
    if (len(check) != len(CONTAINER.read_bytes()) or
            check[bitmap.offset:bitmap.offset + len(font)] != font or
            check[directory.offset + 4:directory.offset + 117] != font[:113]):
        raise AssertionError("CGA system font verification failed")
    print(f"{OUT}: 12-pixel system font, {len(check)} bytes")


if __name__ == "__main__":
    main()
