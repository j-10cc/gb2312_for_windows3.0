"""Turn the Win16 VGA probe's 1-bit device bitmap into an inspectable PNG."""

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
import zlib


def chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def render(info_path: Path, raw_path: Path, png_path: Path) -> None:
    width, height, stride, planes, bits = map(int, info_path.read_text(encoding="ascii").split())
    if planes != 1 or bits != 1 or stride < (width + 7) // 8:
        raise ValueError("expected a 1-bit DDB")
    raw = raw_path.read_bytes()
    if len(raw) != stride * height:
        raise ValueError("unexpected raw image size")
    scanline_bytes = (width + 7) // 8
    scanlines = b"".join(b"\0" + raw[y * stride:y * stride + scanline_bytes]
                         for y in range(height))
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines, level=9))
            + chunk(b"IEND", b""))
    png_path.write_bytes(data)
    print(png_path, width, height)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("info", type=Path)
    p.add_argument("raw", type=Path)
    p.add_argument("png", type=Path)
    args = p.parse_args()
    render(args.info, args.raw, args.png)
