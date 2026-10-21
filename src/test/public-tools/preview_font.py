"""Render a 640x200 monochrome PNG from a CHCGA14.FNT font bank."""

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
import zlib
from pathlib import Path

from build_font import ASCII_COUNT, CELL_HEIGHT, GLYPH_BYTES, HEADER, MAGIC, big5_slot


WIDTH = 640
HEIGHT = 200


def glyph_pixels(font: bytes, char: str) -> tuple[int, list[int]]:
    magic, version, cell_w, cell_h, ascii_w, slots, record_bytes, ascii_at, dbcs_at, _ = HEADER.unpack_from(font)
    if (magic, version, cell_w, cell_h, ascii_w, record_bytes) != (MAGIC, 1, 14, 14, 7, GLYPH_BYTES):
        raise ValueError("unsupported font bank")
    code = ord(char)
    if code < ASCII_COUNT:
        rows = list(font[ascii_at + code * CELL_HEIGHT : ascii_at + (code + 1) * CELL_HEIGHT])
        return ascii_w, [row >> 1 for row in rows]
    try:
        lead, trail = char.encode("cp950")
    except (UnicodeEncodeError, ValueError):
        return cell_w, [0] * cell_h
    slot = big5_slot(lead, trail)
    if slot is None or slot >= slots:
        return cell_w, [0] * cell_h
    at = dbcs_at + slot * record_bytes
    return cell_w, [struct.unpack_from(">H", font, at + y * 2)[0] >> 2 for y in range(cell_h)]


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def save_png(path: Path, pixels: bytearray) -> None:
    raw = b"".join(b"\0" + pixels[y * WIDTH : (y + 1) * WIDTH] for y in range(HEIGHT))
    data = (b"\x89PNG\r\n\x1a\n" +
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 0, 0, 0, 0)) +
            png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    font = args.font.read_bytes()
    pixels = bytearray([255] * (WIDTH * HEIGHT))

    def text(x: int, y: int, value: str) -> None:
        for char in value:
            advance, rows = glyph_pixels(font, char)
            for dy, row in enumerate(rows):
                for dx in range(advance):
                    if row & (1 << (advance - 1 - dx)) and 0 <= x + dx < WIDTH and 0 <= y + dy < HEIGHT:
                        pixels[(y + dy) * WIDTH + x + dx] = 0
            x += advance

    text(12, 5, "檔案(F) 編輯(E) 檢視(V) 說明(H)")
    text(12, 31, "Windows 3.0 繁體中文 CGA 14x14")
    text(12, 55, "字形測試：繁體中文、檔案管理員、設定、說明")
    text(12, 79, "許功蓋  國學  顯示  驅動  輸入法")
    text(12, 103, "0123456789  ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    text(12, 127, "每個中文字佔 14x14 點；英文佔 7x14 點。")
    text(12, 151, "640x200 單色預覽；此圖不是 Windows 啟動畫面。")
    save_png(args.output, pixels)


if __name__ == "__main__":
    main()
