"""Render ESC/P 24-pin bitmap bands from the CEPSON file-port test."""

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

from PIL import Image


def read_bands(source: Path) -> list[tuple[int, bytes]]:
    data = source.read_bytes()
    bands: list[tuple[int, bytes]] = []
    at = 0
    while True:
        at = data.find(b"\x1b*", at)
        if at < 0:
            break
        if at + 5 > len(data):
            raise ValueError("truncated ESC/P band header")
        mode = data[at + 2]
        columns = data[at + 3] | (data[at + 4] << 8)
        if mode != 39:
            raise ValueError(f"unexpected ESC/P mode {mode}")
        start = at + 5
        end = start + columns * 3
        if end > len(data):
            raise ValueError("truncated ESC/P 24-pin bitmap")
        bands.append((columns, data[start:end]))
        at = end
    if not bands:
        raise ValueError("no ESC/P raster bands")
    return bands


def render(source: Path, destination: Path, bands_per_page: int = 6,
           strip: bool = False) -> list[Path]:
    bands = read_bands(source)
    if strip:
        bands_per_page = len(bands)
    elif len(bands) % bands_per_page:
        raise ValueError(f"unexpected raster band count {len(bands)}")
    paths = []
    for page in range(len(bands) // bands_per_page):
        current = bands[page * bands_per_page:(page + 1) * bands_per_page]
        width = max(item[0] for item in current)
        image = Image.new("1", (width, bands_per_page * 24), 1)
        pixels = image.load()
        for band_number, (columns, bitmap) in enumerate(current):
            for x in range(columns):
                for byte_number in range(3):
                    value = bitmap[x * 3 + byte_number]
                    for bit in range(8):
                        if value & (0x80 >> bit):
                            pixels[x, band_number * 24 + byte_number * 8 + bit] = 0
        output = (destination if strip else
                  destination.with_name(f"{destination.stem}-page{page + 1}.png"))
        image.save(output)
        paths.append(output)
    return paths


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--bands-per-page", type=int, default=6)
    p.add_argument("--strip", action="store_true",
                   help="stack all raster bands to inspect printed glyphs")
    a = p.parse_args()
    print(*render(a.source, a.destination, a.bands_per_page, a.strip), sep="\n")


if __name__ == "__main__":
    main()
