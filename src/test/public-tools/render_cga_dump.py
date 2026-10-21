"""Convert a raw 16 KiB CGA mode 06h B800 memory dump to a 640x200 PNG."""

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

from preview_font import HEIGHT, WIDTH, save_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path)
    parser.add_argument("png", type=Path)
    args = parser.parse_args()
    data = args.dump.read_bytes()
    if len(data) != 16384:
        raise ValueError("expected the complete 16 KiB CGA memory window")
    pixels = bytearray(WIDTH * HEIGHT)
    for y in range(HEIGHT):
        bank = (y & 1) * 8192
        row = bank + (y // 2) * 80
        for x in range(WIDTH):
            byte = data[row + x // 8]
            pixels[y * WIDTH + x] = 0 if byte & (0x80 >> (x & 7)) else 255
    save_png(args.png, pixels)


if __name__ == "__main__":
    main()
